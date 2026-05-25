"""Platform-managed Kopia snapshot reconciliation and retention."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from backup_tasks.models import BackupSnapshot, BackupTask
from backup_tasks.services.execution import (
    build_source_resource_config,
    build_repository_config,
    resolve_kopia_source_path,
    select_execution_node,
)
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService
from nodes.repository_locks import RepositoryLockError, create_repository_proxy_task


@dataclass
class RetentionPlan:
    retain_ids: set[str]
    prune_ids: set[str]
    reasons: dict[str, list[str]]


def dispatch_snapshot_reconciliation(task: BackupTask) -> tuple[ProxyTask | None, str]:
    """Ask the execution proxy to list Kopia snapshots for a task source."""
    proxy, error = select_execution_node(task)
    if error:
        return None, error
    source_path = resolve_kopia_source_path(task)
    if not source_path:
        return None, "Backup task has no source path to reconcile"
    password = task.target_repository.get_kopia_password()
    if not password:
        return None, "Repository password is not saved"

    try:
        proxy_task = create_repository_proxy_task(
            repository_id=task.target_repository_id,
            proxy=proxy,
            task_type=ProxyTask.TaskType.SNAPSHOT_LIST,
            parameters={
                "backup_task_id": str(task.id),
                "repository_id": str(task.target_repository_id),
                "source_resource_id": str(task.source_resource_id),
                "source_path": source_path,
                "source_resource": build_source_resource_config(task.source_resource),
                "repository": build_repository_config(task.target_repository),
                "password": password,
                "task_id": "",
            },
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=300,
        )
    except RepositoryLockError as exc:
        return None, str(exc)
    proxy_task.parameters["task_id"] = str(proxy_task.id)
    proxy_task.save(update_fields=["parameters"])
    task.latest_snapshot_sync_task_id = proxy_task.id
    task.latest_snapshot_sync_started_at = timezone.now()
    task.save(update_fields=[
        "latest_snapshot_sync_task_id",
        "latest_snapshot_sync_started_at",
        "updated_at",
    ])
    proxy_task.dispatch()

    message = {
        "type": "list_snapshots",
        "id": str(proxy_task.id),
        "timestamp": timezone.now().isoformat(),
        "payload": proxy_task.parameters,
    }
    if not ProxyService.send_to_proxy(str(proxy.id), message):
        proxy_task.fail("Failed to send snapshot reconciliation command to proxy")
        return proxy_task, "Failed to send snapshot reconciliation command to proxy"
    return proxy_task, ""


def dispatch_snapshot_delete(task: BackupTask, snapshot_ids: list[str]) -> tuple[ProxyTask | None, str]:
    """Ask the execution proxy to delete Kopia snapshot manifests."""
    if not snapshot_ids:
        return None, "No snapshots selected for pruning"
    proxy, error = select_execution_node(task)
    if error:
        return None, error
    password = task.target_repository.get_kopia_password()
    if not password:
        return None, "Repository password is not saved"

    try:
        proxy_task = create_repository_proxy_task(
            repository_id=task.target_repository_id,
            proxy=proxy,
            task_type=ProxyTask.TaskType.SNAPSHOT_DELETE,
            parameters={
                "backup_task_id": str(task.id),
                "repository_id": str(task.target_repository_id),
                "source_resource_id": str(task.source_resource_id),
                "snapshot_ids": snapshot_ids,
                "repository": build_repository_config(task.target_repository),
                "password": password,
                "task_id": "",
            },
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=900,
        )
    except RepositoryLockError as exc:
        return None, str(exc)
    proxy_task.parameters["task_id"] = str(proxy_task.id)
    proxy_task.save(update_fields=["parameters"])
    proxy_task.dispatch()

    message = {
        "type": "delete_snapshots",
        "id": str(proxy_task.id),
        "timestamp": timezone.now().isoformat(),
        "payload": proxy_task.parameters,
    }
    if not ProxyService.send_to_proxy(str(proxy.id), message):
        proxy_task.fail("Failed to send snapshot delete command to proxy")
        return proxy_task, "Failed to send snapshot delete command to proxy"

    for snapshot in BackupSnapshot.objects.filter(
        task=task,
        kopia_snapshot_id__in=snapshot_ids,
    ):
        metadata = snapshot.metadata or {}
        metadata["prune_proxy_task_id"] = str(proxy_task.id)
        snapshot.metadata = metadata
        snapshot.snapshot_status = BackupSnapshot.STATUS_PENDING_PRUNE
        snapshot.last_synced_at = timezone.now()
        snapshot.save(update_fields=["metadata", "snapshot_status", "last_synced_at"])
    return proxy_task, ""


def dispatch_kopia_maintenance(task: BackupTask, full: bool = True) -> tuple[ProxyTask | None, str]:
    """Ask the execution proxy to run Kopia maintenance for the repository."""
    proxy, error = select_execution_node(task)
    if error:
        return None, error
    password = task.target_repository.get_kopia_password()
    if not password:
        return None, "Repository password is not saved"

    try:
        proxy_task = create_repository_proxy_task(
            repository_id=task.target_repository_id,
            proxy=proxy,
            task_type=ProxyTask.TaskType.KOPIA_MAINTENANCE,
            parameters={
                "backup_task_id": str(task.id),
                "repository_id": str(task.target_repository_id),
                "repository": build_repository_config(task.target_repository),
                "password": password,
                "full": full,
                "task_id": "",
            },
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=1800,
        )
    except RepositoryLockError as exc:
        return None, str(exc)
    proxy_task.parameters["task_id"] = str(proxy_task.id)
    proxy_task.save(update_fields=["parameters"])
    proxy_task.dispatch()

    message = {
        "type": "run_maintenance",
        "id": str(proxy_task.id),
        "timestamp": timezone.now().isoformat(),
        "payload": proxy_task.parameters,
    }
    if not ProxyService.send_to_proxy(str(proxy.id), message):
        proxy_task.fail("Failed to send maintenance command to proxy")
        return proxy_task, "Failed to send maintenance command to proxy"
    return proxy_task, ""


def reconcile_snapshot_result(proxy_task: ProxyTask, result: dict[str, Any]) -> dict[str, int]:
    """Upsert snapshots from a proxy list_snapshots result and mark missing records."""
    task_id = (proxy_task.parameters or {}).get("backup_task_id")
    if not task_id:
        return {"seen": 0, "missing": 0}
    task = BackupTask.objects.select_related("target_repository").filter(id=task_id).first()
    if not task:
        return {"seen": 0, "missing": 0}
    if task.latest_snapshot_sync_task_id and task.latest_snapshot_sync_task_id != proxy_task.id:
        return {
            "seen": 0,
            "missing": 0,
            "ignored_stale_sync": 1,
            "latest_snapshot_sync_task_id": str(task.latest_snapshot_sync_task_id),
        }

    raw_snapshots = result.get("snapshots", [])
    if isinstance(raw_snapshots, str):
        try:
            raw_snapshots = json.loads(raw_snapshots)
        except json.JSONDecodeError:
            raw_snapshots = []
    now = timezone.now()
    current_snapshot_ids: set[str] = set()
    seen_snapshots = 0
    skipped_source_mismatch = 0
    expected_source_path = _normalize_source_path(
        result.get("source_path") or (proxy_task.parameters or {}).get("source_path")
    )

    with transaction.atomic():
        for item in raw_snapshots or []:
            if not isinstance(item, dict):
                continue
            snapshot_id = str(item.get("id") or "").strip()
            if not snapshot_id:
                continue
            source = item.get("source") or {}
            source_path = _normalize_source_path(source.get("path") if source else "")
            root_entry = item.get("rootEntry") or {}
            root_object_id = str(root_entry.get("obj") or "").strip()
            if expected_source_path and source_path and source_path != expected_source_path:
                skipped_source_mismatch += 1
                continue
            current_snapshot_ids.add(snapshot_id)
            seen_snapshots += 1
            stats = item.get("stats") or {}
            snapshot_time = _parse_snapshot_time(item)
            metadata = {
                "source": source,
                "root_object_id": root_object_id,
                "snapshot_id": snapshot_id,
                "kopia_snapshot": item,
                "snapshot_time": snapshot_time.isoformat() if snapshot_time else "",
                "kopia_start_time": item.get("startTime") or "",
                "kopia_end_time": item.get("endTime") or "",
                "last_seen_at": now.isoformat(),
            }
            snapshot, _created = BackupSnapshot.objects.get_or_create(
                task=task,
                kopia_snapshot_id=snapshot_id,
                defaults={
                    "kopia_root_object_id": root_object_id,
                    "storage_path": snapshot_id,
                    "repository": task.target_repository,
                    "name": f"snapshot-{snapshot_id[:12]}",
                    "version": snapshot_id,
                    "manifest_path": root_object_id,
                    "total_size": int(stats.get("totalSize") or 0),
                    "file_count": int(stats.get("fileCount") or 0),
                    "metadata": {},
                },
            )
            existing_metadata = snapshot.metadata or {}
            existing_metadata.update(metadata)
            snapshot.repository = task.target_repository
            snapshot.kopia_snapshot_id = snapshot_id
            snapshot.kopia_root_object_id = root_object_id
            snapshot.version = snapshot_id
            snapshot.storage_path = snapshot_id
            snapshot.manifest_path = root_object_id or snapshot.manifest_path
            if snapshot_time:
                snapshot.created_at = snapshot_time
            snapshot.total_size = int(stats.get("totalSize") or snapshot.total_size or 0)
            snapshot.file_count = int(stats.get("fileCount") or snapshot.file_count or 0)
            snapshot.metadata = existing_metadata
            snapshot.retention_reasons = item.get("retentionReason") or snapshot.retention_reasons or []
            snapshot.snapshot_status = BackupSnapshot.STATUS_AVAILABLE
            snapshot.last_synced_at = now
            snapshot.missing_count = 0
            snapshot.pruned_at = None
            snapshot.save(update_fields=[
                "repository", "version", "storage_path", "manifest_path", "created_at",
                "kopia_snapshot_id", "kopia_root_object_id", "total_size", "file_count",
                "metadata", "retention_reasons", "snapshot_status", "last_synced_at",
                "missing_count", "pruned_at",
            ])

        existing = (
            BackupSnapshot.objects
            .filter(task=task)
            .exclude(metadata__no_changes=True)
            .exclude(kopia_snapshot_id="")
        )
        missing_count = 0
        if not current_snapshot_ids:
            return {
                "seen": seen_snapshots,
                "missing": missing_count,
                "available_seen": len(current_snapshot_ids),
                "skipped_source_mismatch": skipped_source_mismatch,
            }
        for snapshot in existing:
            if snapshot.kopia_snapshot_id in current_snapshot_ids:
                if (
                    snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE
                    or snapshot.missing_count
                    or snapshot.pruned_at
                ):
                    snapshot.snapshot_status = BackupSnapshot.STATUS_AVAILABLE
                    snapshot.missing_count = 0
                    snapshot.pruned_at = None
                    snapshot.last_synced_at = now
                    snapshot.save(update_fields=[
                        "snapshot_status", "missing_count", "pruned_at", "last_synced_at",
                    ])
                continue
            snapshot.missing_count += 1
            snapshot.last_synced_at = now
            if snapshot.snapshot_status == BackupSnapshot.STATUS_PENDING_PRUNE or snapshot.missing_count >= 3:
                snapshot.snapshot_status = BackupSnapshot.STATUS_PRUNED
                snapshot.pruned_at = snapshot.pruned_at or now
            elif snapshot.missing_count >= 2:
                snapshot.snapshot_status = BackupSnapshot.STATUS_MISSING
            else:
                update_fields = ["missing_count", "last_synced_at"]
                snapshot.save(update_fields=update_fields)
                missing_count += 1
                continue
            snapshot.save(update_fields=["missing_count", "last_synced_at", "snapshot_status", "pruned_at"])
            missing_count += 1

    return {
        "seen": seen_snapshots,
        "missing": missing_count,
        "available_seen": len(current_snapshot_ids),
        "skipped_source_mismatch": skipped_source_mismatch,
    }


def _normalize_source_path(path: Any) -> str:
    value = str(path or "").strip()
    if not value:
        return ""
    while len(value) > 1 and value.endswith(("/", "\\")):
        value = value[:-1]
    return value


def _parse_snapshot_time(item: dict[str, Any]):
    value = item.get("startTime") or item.get("endTime") or ""
    parsed = parse_datetime(str(value)) if value else None
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed


def evaluate_retention(task: BackupTask) -> RetentionPlan:
    """Calculate platform retention against currently available real snapshots."""
    snapshots = list(
        BackupSnapshot.objects.filter(
            task=task,
            snapshot_status=BackupSnapshot.STATUS_AVAILABLE,
        )
        .exclude(metadata__no_changes=True)
        .exclude(kopia_snapshot_id="")
        .order_by("-created_at")
    )
    retention = _effective_retention(task)
    retain_ids: set[str] = set()
    reasons: dict[str, list[str]] = {}

    def retain(snapshot: BackupSnapshot, reason: str) -> None:
        retain_ids.add(snapshot.kopia_snapshot_id)
        reasons.setdefault(snapshot.kopia_snapshot_id, []).append(reason)

    for snapshot in snapshots[: int(retention.get("keep_latest") or 0)]:
        retain(snapshot, "latest")

    _retain_by_bucket(snapshots, retention.get("keep_hourly"), "%Y-%m-%dT%H", "hourly", retain)
    _retain_by_bucket(snapshots, retention.get("keep_daily"), "%Y-%m-%d", "daily", retain)
    _retain_by_bucket(snapshots, retention.get("keep_weekly"), "%G-W%V", "weekly", retain)
    _retain_by_bucket(snapshots, retention.get("keep_monthly"), "%Y-%m", "monthly", retain)
    _retain_by_bucket(snapshots, retention.get("keep_annual"), "%Y", "annual", retain)

    all_ids = {snapshot.kopia_snapshot_id for snapshot in snapshots if snapshot.kopia_snapshot_id}
    return RetentionPlan(retain_ids=retain_ids, prune_ids=all_ids - retain_ids, reasons=reasons)


def apply_retention_marks(task: BackupTask, plan: RetentionPlan) -> None:
    """Persist retention reasons for retained snapshots without deleting anything."""
    for snapshot in BackupSnapshot.objects.filter(task=task, kopia_snapshot_id__in=plan.retain_ids):
        snapshot.retention_reasons = plan.reasons.get(snapshot.kopia_snapshot_id, [])
        if snapshot.snapshot_status == BackupSnapshot.STATUS_PENDING_PRUNE:
            snapshot.snapshot_status = BackupSnapshot.STATUS_AVAILABLE
        snapshot.save(update_fields=["retention_reasons", "snapshot_status"])


def run_retention_for_task(task: BackupTask, *, delete: bool = True) -> dict[str, Any]:
    """Evaluate retention and optionally dispatch Kopia snapshot deletion."""
    plan = evaluate_retention(task)
    apply_retention_marks(task, plan)
    result: dict[str, Any] = {
        "retained": len(plan.retain_ids),
        "pending_prune": len(plan.prune_ids),
        "delete_task_id": "",
        "error": "",
    }
    if delete and plan.prune_ids:
        proxy_task, error = dispatch_snapshot_delete(task, sorted(plan.prune_ids))
        result["delete_task_id"] = str(proxy_task.id) if proxy_task else ""
        result["error"] = error
    return result


def _effective_retention(task: BackupTask) -> dict[str, int]:
    policy = task.effective_policy or {}
    retention = policy.get("retention_policy") or {}
    if not retention and task.schedule_id:
        retention = task.schedule.retention_policy or {}
    return {
        "keep_latest": int(retention.get("keep_latest") or task.max_snapshots or 0),
        "keep_hourly": int(retention.get("keep_hourly") or 0),
        "keep_daily": int(retention.get("keep_daily") or task.retention_days or 0),
        "keep_weekly": int(retention.get("keep_weekly") or 0),
        "keep_monthly": int(retention.get("keep_monthly") or 0),
        "keep_annual": int(retention.get("keep_annual") or 0),
    }


def _retain_by_bucket(snapshots, keep_count, fmt, prefix, retain) -> None:
    keep_count = int(keep_count or 0)
    if keep_count <= 0:
        return
    seen = set()
    kept = 0
    for snapshot in snapshots:
        key = timezone.localtime(snapshot.created_at).strftime(fmt)
        if key in seen:
            continue
        seen.add(key)
        retain(snapshot, f"{prefix}-{kept + 1}")
        kept += 1
        if kept >= keep_count:
            break
