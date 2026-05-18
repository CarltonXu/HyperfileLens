"""
HyperFileLens Backend - Backup Tasks Celery Tasks

This module defines asynchronous tasks for backup operations
using Celery with Redis as the message broker.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_backup_task(self, task_id: str):
    """
    Execute a backup task asynchronously.
    
    This task:
    1. Updates task status to 'running'
    2. Scans source files
    3. Transfers files to repository
    4. Creates snapshot
    5. Updates task status to 'completed' or 'failed'
    
    Args:
        task_id: UUID of the BackupTask to execute
    """
    from .models import BackupTask, BackupSnapshot
    
    try:
        task = BackupTask.objects.get(id=task_id)
    except BackupTask.DoesNotExist:
        logger.error(f"Backup task {task_id} not found")
        return {'status': 'error', 'message': 'Task not found'}
    
    # Check if task is already running
    if task.status == 'running':
        return {'status': 'error', 'message': 'Task already running'}
    
    logger.info(f"Starting backup task: {task.name} (ID: {task_id})")
    task.mark_running()
    
    try:
        # Step 1: Scan source files
        logger.info(f"Scanning source files for task {task_id}")
        files_to_backup = _scan_source_files(task)
        
        # Step 2: Transfer files to repository
        logger.info(f"Transferring files to repository for task {task_id}")
        _transfer_files(task, files_to_backup)
        
        # Step 3: Create snapshot
        logger.info(f"Creating snapshot for task {task_id}")
        snapshot = _create_snapshot(task)
        
        # Step 4: Mark task as completed
        task.mark_completed()
        
        logger.info(f"Backup task {task_id} completed successfully")
        return {
            'status': 'success',
            'task_id': str(task_id),
            'snapshot_id': str(snapshot.id) if snapshot else None,
            'files_backed_up': task.backed_up_files,
            'total_size': task.backed_up_size
        }
        
    except Exception as e:
        error_message = str(e)
        logger.exception(f"Backup task {task_id} failed: {error_message}")
        task.mark_failed(error_message)
        
        # Retry if appropriate
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'status': 'error', 'message': error_message}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_restore_task(self, snapshot_id: str, target_path: str, file_patterns: list = None):
    """
    Execute a restore task asynchronously.
    
    Args:
        snapshot_id: UUID of the BackupSnapshot to restore
        target_path: Path to restore files to
        file_patterns: Optional list of file patterns to restore
    """
    from .models import BackupSnapshot
    
    try:
        snapshot = BackupSnapshot.objects.get(id=snapshot_id)
    except BackupSnapshot.DoesNotExist:
        logger.error(f"Snapshot {snapshot_id} not found")
        return {'status': 'error', 'message': 'Snapshot not found'}
    
    logger.info(f"Starting restore from snapshot: {snapshot.name}")
    
    try:
        # Restore files from repository
        _restore_files(snapshot, target_path, file_patterns)
        
        logger.info(f"Restore from snapshot {snapshot_id} completed")
        return {
            'status': 'success',
            'snapshot_id': str(snapshot_id),
            'target_path': target_path
        }
        
    except Exception as e:
        error_message = str(e)
        logger.exception(f"Restore task {snapshot_id} failed: {error_message}")
        return {'status': 'error', 'message': error_message}


@shared_task
def reconcile_backup_snapshots():
    """Dispatch snapshot reconciliation for enabled backup tasks."""
    from .models import BackupTask
    from .services.retention import dispatch_snapshot_reconciliation

    dispatched = 0
    skipped = 0
    for task in BackupTask.objects.filter(is_enabled=True).select_related(
        'source_resource', 'target_repository', 'source_resource__bound_node',
        'target_repository__bound_node', 'preferred_execution_node', 'schedule',
    )[:100]:
        proxy_task, error = dispatch_snapshot_reconciliation(task)
        if proxy_task and not error:
            dispatched += 1
        else:
            skipped += 1
            logger.warning("Skipped snapshot reconciliation for task %s: %s", task.id, error)
    return {'dispatched': dispatched, 'skipped': skipped}


@shared_task
def evaluate_backup_retention():
    """Evaluate platform retention and dispatch Kopia pruning for due tasks."""
    from .models import BackupTask
    from .services.retention import run_retention_for_task

    evaluated = 0
    pending_prune = 0
    errors = 0
    for task in BackupTask.objects.filter(is_enabled=True).select_related(
        'source_resource', 'target_repository', 'source_resource__bound_node',
        'target_repository__bound_node', 'preferred_execution_node', 'schedule',
    )[:100]:
        try:
            result = run_retention_for_task(task, delete=True)
            evaluated += 1
            pending_prune += result.get('pending_prune', 0)
            if result.get('error'):
                errors += 1
                logger.warning("Retention prune dispatch failed for task %s: %s", task.id, result['error'])
        except Exception as exc:
            errors += 1
            logger.exception("Retention evaluation failed for task %s: %s", task.id, exc)
    return {'evaluated': evaluated, 'pending_prune': pending_prune, 'errors': errors}


@shared_task
def sync_backup_progress(task_id: str):
    """
    Sync backup progress from source node to central database.
    
    This is called periodically during a backup to update progress.
    """
    from .models import BackupTask
    
    try:
        task = BackupTask.objects.get(id=task_id)
        # In a real implementation, this would query the source node
        # for current progress and update the database
        logger.debug(f"Syncing progress for task {task_id}")
    except BackupTask.DoesNotExist:
        logger.error(f"Task {task_id} not found during progress sync")


# Helper functions

def _scan_source_files(task):
    """
    Scan source files for backup.
    
    Returns a list of file information dictionaries.
    """
    import os
    import hashlib
    
    files = []
    exclude_patterns = set(task.exclude_patterns or [])
    
    for path in task.paths:
        if not os.path.exists(path):
            logger.warning(f"Path does not exist: {path}")
            continue
        
        if os.path.isfile(path):
            files.append(_get_file_info(path, task.source_node.host_path))
        elif os.path.isdir(path):
            for root, dirs, filenames in os.walk(path):
                # Filter excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_patterns]
                
                for filename in filenames:
                    if filename in exclude_patterns:
                        continue
                    
                    file_path = os.path.join(root, filename)
                    files.append(_get_file_info(file_path, task.source_node.host_path))
    
    # Update task statistics
    task.total_files = len(files)
    task.total_size = sum(f['size'] for f in files)
    task.save(update_fields=['total_files', 'total_size', 'updated_at'])
    
    return files


def _get_file_info(file_path: str, base_path: str):
    """Get file information for backup."""
    import hashlib
    import os
    
    stat = os.stat(file_path)
    
    # Calculate checksum
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    
    return {
        'path': file_path,
        'relative_path': os.path.relpath(file_path, base_path),
        'name': os.path.basename(file_path),
        'size': stat.st_size,
        'checksum': md5.hexdigest(),
        'modified': stat.st_mtime
    }


def _transfer_files(task, files):
    """
    Transfer files to the backup repository.
    
    In a real implementation, this would:
    1. Connect to the target repository
    2. Stream files to avoid memory issues
    3. Update progress as files are transferred
    """
    total_files = len(files)
    
    for i, file_info in enumerate(files):
        # Simulate file transfer
        # In production, this would be actual file transfer logic
        
        # Update progress
        task.backed_up_files = i + 1
        task.backed_up_size += file_info['size']
        task.progress = int(((i + 1) / total_files) * 100)
        task.save(update_fields=['backed_up_files', 'backed_up_size', 'progress', 'updated_at'])


def _create_snapshot(task):
    """Create a new snapshot for the backup task."""
    from .models import BackupSnapshot
    import uuid
    
    # Calculate expiration date
    expires_at = None
    if task.retention_days > 0:
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(days=task.retention_days)
    
    # Create snapshot
    snapshot = BackupSnapshot.objects.create(
        task=task,
        name=f"{task.name}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        description=f"Automatic backup snapshot",
        version='1.0',
        repository=task.target_repository,
        storage_path=f"snapshots/{task.id}/{uuid.uuid4()}",
        total_size=task.backed_up_size,
        file_count=task.backed_up_files,
        expires_at=expires_at
    )
    
    return snapshot


def _restore_files(snapshot, target_path, file_patterns=None):
    """
    Restore files from a snapshot to a target path.
    
    Args:
        snapshot: BackupSnapshot instance
        target_path: Destination path for restore
        file_patterns: Optional filter for specific files
    """
    import os
    
    # Ensure target directory exists
    os.makedirs(target_path, exist_ok=True)
    
    # In production, this would:
    # 1. Read manifest from repository
    # 2. Extract/decompress files
    # 3. Write to target path
    
    logger.info(f"Restoring {snapshot.file_count} files to {target_path}")
