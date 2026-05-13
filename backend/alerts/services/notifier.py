"""Notification delivery for alert records."""

import base64
import hashlib
import hmac
import html
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils import timezone

from alerts.choices import NotificationChannelType, NotificationStatus, NotificationType
from alerts.models import AlertPolicy, NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)


def send_notification(alert):
    """Send firing notifications for an alert."""
    _send(alert, resolved=False)


def send_resolved_notification(alert):
    """Send resolved notifications for an alert."""
    _send(alert, resolved=True)


def test_channel(channel):
    """Send a lightweight test message through a channel."""
    if channel.type == NotificationChannelType.EMAIL:
        config = channel.config or {}
        recipients = config.get("to_emails") or []
        if not recipients:
            raise ValueError("Email channel requires to_emails.")

        # Get SMTP configuration from channel config or fall back to database
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port")
        smtp_username = config.get("smtp_username")
        smtp_password = config.get("smtp_password")
        use_tls = config.get("use_tls", True)
        use_ssl = config.get("use_ssl", False)
        from_email = config.get("from_email")
        email_subject = config.get("email_subject")

        # Auto-detect SSL for port 465 (common for SMTP SSL)
        if str(smtp_port) == "465":
            use_ssl = True
            use_tls = False

        # Use custom email subject if provided, otherwise use default
        subject = email_subject or "HyperFileLens alert channel test"

        # If channel config has SMTP settings, use them directly
        if smtp_host and smtp_port:
            from django.core.mail import get_connection
            from system_settings.email_backend import NoVerifyEmailBackend

            connection = get_connection(
                backend='system_settings.email_backend.NoVerifyEmailBackend',
                host=smtp_host,
                port=smtp_port,
                username=smtp_username,
                password=smtp_password,
                use_tls=use_tls,
                use_ssl=use_ssl,
            )

            email = EmailMessage(
                subject=subject,
                body="This is a test notification from HyperFileLens.",
                from_email=from_email,
                to=recipients,
                connection=connection,
            )
            email.send()
            return {"status": "success"}
        else:
            # Fall back to database SMTP configuration
            from system_settings.models import SMTPConfig

            smtp_config = SMTPConfig.objects.filter(is_active=True).first()
            if not smtp_config:
                raise ValueError("No SMTP configuration found in channel or System Settings.")

            connection = smtp_config.get_connection()

            email = EmailMessage(
                subject=subject,
                body="This is a test notification from HyperFileLens.",
                from_email=from_email or smtp_config.from_email,
                to=recipients,
                connection=connection,
            )
            email.send()
            return {"status": "success"}

    if channel.type == NotificationChannelType.WEBHOOK:
        _send_webhook(channel, {"type": "test", "message": "HyperFileLens alert channel test"})
        return {"status": "success"}

    if channel.type == NotificationChannelType.DINGTALK:
        _send_dingtalk(channel, "HyperFileLens alert channel test")
        return {"status": "success"}

    if channel.type == NotificationChannelType.WECOM:
        _send_wecom(channel, "HyperFileLens alert channel test")
        return {"status": "success"}

    return {"status": "skipped", "message": "Channel type is reserved for future delivery."}


def _send(alert, resolved=False):
    try:
        policy = AlertPolicy.objects.get(id=alert.policy_id)
    except AlertPolicy.DoesNotExist:
        return

    channel_ids = policy.notification_channel_ids or []
    if not channel_ids:
        return

    channels = NotificationChannel.objects.filter(id__in=channel_ids, enabled=True)
    for channel in channels:
        try:
            lang = _channel_language(channel)
            if channel.type == NotificationChannelType.EMAIL:
                _send_email(channel, alert, resolved)
            elif channel.type == NotificationChannelType.WEBHOOK:
                _send_webhook(channel, _payload(alert, resolved))
            elif channel.type == NotificationChannelType.DINGTALK:
                _send_dingtalk(channel, _build_text_message(alert, resolved, lang))
            elif channel.type == NotificationChannelType.WECOM:
                _send_wecom(channel, _build_text_message(alert, resolved, lang))
            else:
                logger.info("Notification channel type %s is reserved.", channel.type)

            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                notification_type=NotificationType.RESOLVED if resolved else NotificationType.FIRING,
                status=NotificationStatus.SUCCESS,
            )
        except Exception as exc:
            logger.exception("Alert notification failed: %s", exc)
            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                notification_type=NotificationType.RESOLVED if resolved else NotificationType.FIRING,
                status=NotificationStatus.FAILED,
                error_message=str(exc),
            )


def _send_email(channel, alert, resolved):
    config = channel.config or {}
    lang = _channel_language(channel)
    recipients = config.get("to_emails") or []
    if not recipients:
        raise ValueError("Email channel requires to_emails.")

    # Get SMTP configuration from channel config or fall back to database
    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port")
    smtp_username = config.get("smtp_username")
    smtp_password = config.get("smtp_password")
    use_tls = config.get("use_tls", True)
    use_ssl = config.get("use_ssl", False)
    from_email = config.get("from_email")
    email_subject = config.get("email_subject")

    # Auto-detect SSL for port 465 (common for SMTP SSL)
    if str(smtp_port) == "465":
        use_ssl = True
        use_tls = False

    subject = _build_email_subject(email_subject, alert, resolved, lang)

    # If channel config has SMTP settings, use them directly
    if smtp_host and smtp_port:
        from django.core.mail import get_connection
        from system_settings.email_backend import NoVerifyEmailBackend

        connection = get_connection(
            backend='system_settings.email_backend.NoVerifyEmailBackend',
            host=smtp_host,
            port=smtp_port,
            username=smtp_username,
            password=smtp_password,
            use_tls=use_tls,
            use_ssl=use_ssl,
        )
    else:
        # Fall back to database SMTP configuration
        from system_settings.models import SMTPConfig

        smtp_config = SMTPConfig.objects.filter(is_active=True).first()
        if not smtp_config:
            logger.warning("No active SMTP configuration found")
            return

        connection = smtp_config.get_connection()

    html_body = _build_email_html(alert, resolved, lang)
    text_body = _build_text_message(alert, resolved, lang)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=recipients,
        connection=connection,
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def _build_email_subject(template, alert, resolved, lang=None):
    lang = _normalize_language(lang)
    prefix = "Resolved" if resolved else "Alert"
    state = _t(lang, "resolved_state" if resolved else "firing_state")
    label = _alert_label(alert, lang)
    resource = alert.resource_name or "-"
    current = _format_value(_alert_current_value(alert), _alert_unit(alert))
    threshold = _format_value(_alert_threshold_value(alert), _alert_unit(alert))
    default_subject = f"[HyperFileLens][{alert.severity.upper()}][{state}] {label} - {resource}"
    if current != "-":
        default_subject = f"{default_subject} {_t(lang, 'current')} {current}"
    if threshold != "-":
        default_subject = f"{default_subject} {_t(lang, 'threshold')} {threshold}"

    if not template:
        return default_subject

    values = {
        "status": prefix,
        "state": state,
        "title": alert.title,
        "severity": alert.severity,
        "resource": resource,
        "metric": label,
        "alert": label,
        "current": current,
        "threshold": threshold,
    }
    if "{" in template and "}" in template:
        subject = template
        for key, value in values.items():
            subject = subject.replace(f"{{{key}}}", str(value))
        return subject
    return f"{template} - {label} - {resource} - {state}"


def _build_email_html(alert, resolved, lang=None):
    lang = _normalize_language(lang)
    policy = _policy_for_alert(alert)
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    resource = _resource_details(alert)
    status_text = _t(lang, "resolved_status" if resolved else "firing_status")
    accent = "#16a34a" if resolved else _severity_color(alert.severity)
    bg = "#f8fafc"
    card = "#ffffff"
    border = "#e2e8f0"
    muted = "#64748b"
    text = "#0f172a"
    current = _format_value(_alert_current_value(alert), _alert_unit(alert))
    threshold = _format_value(_alert_threshold_value(alert), _alert_unit(alert))
    label = _alert_label(alert, lang, policy=policy)
    operator = metadata.get("operator") or trigger_rule.get("operator") or "-"
    duration = _format_duration(trigger_rule.get("duration_seconds"), lang)
    evaluation_interval = _format_duration(trigger_rule.get("evaluation_interval_seconds"), lang)

    summary_rows = [
        (_t(lang, "alert_status"), status_text),
        (_t(lang, "severity"), alert.severity.upper()),
        (_t(lang, "alert_type"), alert.type),
        (_t(lang, "current_value"), current),
        (_t(lang, "trigger_condition"), _trigger_condition(alert, label, operator, threshold, lang)),
        (_t(lang, "duration"), duration),
        (_t(lang, "evaluation_interval"), evaluation_interval),
        (_t(lang, "first_triggered"), _format_datetime(alert.first_triggered_at)),
        (_t(lang, "last_triggered"), _format_datetime(alert.last_triggered_at)),
        (_t(lang, "resolved_at"), _format_datetime(alert.resolved_at) if resolved else "-"),
    ]
    resource_rows = [
        (_t(lang, "resource_name"), alert.resource_name or "-"),
        (_t(lang, "resource_id"), str(alert.resource_id) if alert.resource_id else "-"),
        (_t(lang, "resource_type"), alert.resource_type or "-"),
        (_t(lang, "resource_ip"), resource.get("ip") or "-"),
        (_t(lang, "hostname"), resource.get("hostname") or "-"),
        (_t(lang, "role"), resource.get("role") or "-"),
        (_t(lang, "os"), resource.get("os") or "-"),
        (_t(lang, "cpu_cores"), resource.get("cpu_cores") or "-"),
        (_t(lang, "memory_usage"), _format_percent(resource.get("memory_usage"))),
        (_t(lang, "disk_usage"), _format_percent(resource.get("disk_usage"))),
        (_t(lang, "last_heartbeat"), _format_datetime(resource.get("last_heartbeat"))),
    ]
    policy_rows = [
        (_t(lang, "policy_name"), policy.name if policy else "-"),
        (_t(lang, "policy_id"), str(policy.id) if policy else "-"),
        (_t(lang, "policy_status"), _t(lang, "enabled") if policy and policy.enabled else _t(lang, "disabled")),
        (_t(lang, "scope"), policy.scope if policy else "-"),
        (_t(lang, "channel_count"), len(policy.notification_channel_ids or []) if policy else "-"),
    ]
    type_section_title, type_rows = _type_specific_section(alert, policy, resource, lang)

    return f"""<!doctype html>
<html>
  <body style="margin:0;background:{bg};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:{text};">
    <div style="max-width:760px;margin:0 auto;padding:28px 18px;">
      <div style="background:{card};border:1px solid {border};border-radius:10px;overflow:hidden;">
        <div style="padding:22px 24px;border-left:6px solid {accent};background:#ffffff;">
          <div style="font-size:13px;color:{muted};font-weight:700;letter-spacing:.04em;text-transform:uppercase;">HyperFileLens Alert Center</div>
          <h1 style="margin:8px 0 6px;font-size:22px;line-height:1.35;color:{text};">{_escape(label)} - {_escape(status_text)}</h1>
          <div style="font-size:14px;color:{muted};">{_escape(_localized_alert_title(alert, label, status_text, lang))}</div>
        </div>
        <div style="padding:22px 24px;border-top:1px solid {border};">
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;">
            {_pill(_t(lang, 'severity'), alert.severity.upper(), accent)}
            {_pill(_t(lang, 'current_value'), current, '#2563eb')}
            {_pill(_t(lang, 'threshold'), f'{operator} {threshold}', '#7c3aed')}
            {_pill(_t(lang, 'resource'), alert.resource_name or '-', '#475569')}
          </div>
          <p style="margin:0 0 18px;font-size:14px;line-height:1.7;color:{text};">{_escape(_localized_alert_message(alert, label, operator, threshold, lang))}</p>
          {_section(_t(lang, 'alert_overview'), summary_rows)}
          {_section(type_section_title, type_rows)}
          {_section(_t(lang, 'resource_info'), resource_rows)}
          {_section(_t(lang, 'policy_info'), policy_rows)}
          <div style="margin-top:20px;padding:14px 16px;background:#f1f5f9;border-radius:8px;color:{muted};font-size:12px;line-height:1.6;">
            Alert ID: {_escape(str(alert.id))}<br/>
            Fingerprint: {_escape(alert.fingerprint)}<br/>
            Metadata: {_escape(json.dumps(_email_metadata(alert), ensure_ascii=False, default=str))}
          </div>
        </div>
      </div>
    </div>
  </body>
</html>"""


def _build_text_message(alert, resolved, lang=None):
    lang = _normalize_language(lang)
    policy = _policy_for_alert(alert)
    trigger_rule = policy.trigger_rule if policy else {}
    resource = _resource_details(alert)
    label = _alert_label(alert, lang, policy=policy)
    operator = (alert.metadata or {}).get("operator") or trigger_rule.get("operator") or "-"
    status_text = _t(lang, "resolved_status" if resolved else "firing_status")
    return "\n".join(
        [
            f"[HyperFileLens] {label} - {status_text}",
            f"{_t(lang, 'alert_title')}: {_localized_alert_title(alert, label, status_text, lang)}",
            f"{_t(lang, 'severity')}: {alert.severity.upper()}",
            f"{_t(lang, 'resource_name')}: {alert.resource_name or '-'}",
            f"{_t(lang, 'resource_id')}: {alert.resource_id or '-'}",
            f"{_t(lang, 'resource_ip')}: {resource.get('ip') or '-'}",
            f"{_t(lang, 'cpu_cores')}: {resource.get('cpu_cores') or '-'}",
            f"{_t(lang, 'current_value')}: {_format_value(_alert_current_value(alert), _alert_unit(alert))}",
            f"{_t(lang, 'trigger_condition')}: {_trigger_condition(alert, label, operator, _format_value(_alert_threshold_value(alert), _alert_unit(alert)), lang)}",
            f"{_t(lang, 'policy_name')}: {policy.name if policy else '-'}",
            f"{_t(lang, 'last_triggered')}: {_format_datetime(alert.last_triggered_at)}",
            f"{_t(lang, 'message')}: {_localized_alert_message(alert, label, operator, _format_value(_alert_threshold_value(alert), _alert_unit(alert)), lang)}",
        ]
    )


def _localized_alert_title(alert, metric_label, status_text, lang):
    resource = alert.resource_name or "-"
    if _normalize_language(lang) == "zh":
        return f"{metric_label} - {resource} - {status_text}"
    return f"{metric_label} - {resource} - {status_text}"


def _localized_alert_message(alert, metric_label, operator, threshold, lang):
    current = _format_value(_alert_current_value(alert), _alert_unit(alert))
    resource = alert.resource_name or "-"
    metadata = alert.metadata or {}
    if alert.type == "availability" and metadata.get("check_type") == "heartbeat":
        if _normalize_language(lang) == "zh":
            return f"{resource} 心跳超时，当前离线时长为 {current}，超过阈值 {threshold}。"
        return f"{resource} heartbeat timed out. Current heartbeat age is {current}, exceeding threshold {threshold}."
    if alert.type == "job":
        event = metadata.get("event_type") or metadata.get("alert_type") or "job event"
        if _normalize_language(lang) == "zh":
            return f"{resource} 触发任务告警：{event}。{alert.message or ''}".strip()
        return f"{resource} triggered job alert: {event}. {alert.message or ''}".strip()
    if alert.type == "system":
        if _normalize_language(lang) == "zh":
            return f"系统告警 {metric_label} 当前为 {current}，触发条件：{metric_label} {operator} {threshold}。"
        return f"System alert {metric_label} is currently {current}, matching trigger condition: {metric_label} {operator} {threshold}."
    if alert.type == "event":
        if _normalize_language(lang) == "zh":
            return f"平台事件触发告警：{metadata.get('type') or alert.title}。"
        return f"Platform event triggered alert: {metadata.get('type') or alert.title}."
    if _normalize_language(lang) == "zh":
        return f"{resource} 的 {metric_label} 当前为 {current}，已满足触发条件：{metric_label} {operator} {threshold}。"
    return f"{metric_label} on {resource} is currently {current}, matching trigger condition: {metric_label} {operator} {threshold}."


def _type_specific_section(alert, policy, resource, lang):
    if alert.type == "metric":
        return _t(lang, "metric_details"), _metric_rows(alert, policy, lang)
    if alert.type == "availability":
        return _t(lang, "availability_details"), _availability_rows(alert, policy, resource, lang)
    if alert.type == "job":
        job = _job_details(alert)
        return _t(lang, "job_details"), _job_rows(alert, policy, job, lang)
    if alert.type == "system":
        return _t(lang, "system_details"), _system_rows(alert, policy, lang)
    if alert.type == "event":
        return _t(lang, "event_details"), _event_rows(alert, policy, lang)
    return _t(lang, "alert_details"), [(_t(lang, "message"), alert.message or "-")]


def _metric_rows(alert, policy, lang):
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    metric_key = metadata.get("metric_key") or trigger_rule.get("metric_key")
    label = _metric_label(metric_key, lang)
    operator = metadata.get("operator") or trigger_rule.get("operator") or "-"
    return [
        (_t(lang, "metric"), label),
        (_t(lang, "metric_key"), metric_key or "-"),
        (_t(lang, "current_value"), _format_value(_alert_current_value(alert), _alert_unit(alert))),
        (_t(lang, "threshold"), f"{operator} {_format_value(_alert_threshold_value(alert), _alert_unit(alert))}"),
        (_t(lang, "duration"), _format_duration(trigger_rule.get("duration_seconds"), lang)),
        (_t(lang, "evaluation_interval"), _format_duration(trigger_rule.get("evaluation_interval_seconds"), lang)),
    ]


def _availability_rows(alert, policy, resource, lang):
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    check_type = metadata.get("check_type") or trigger_rule.get("check_type")
    timeout = metadata.get("timeout_seconds") or trigger_rule.get("timeout_seconds")
    return [
        (_t(lang, "check_type"), _availability_label(check_type, lang)),
        (_t(lang, "check_key"), check_type or "-"),
        (_t(lang, "heartbeat_age"), _format_value(_alert_current_value(alert), _alert_unit(alert))),
        (_t(lang, "timeout_threshold"), _format_value(_alert_threshold_value(alert) or timeout, _alert_unit(alert)) if (_alert_threshold_value(alert) or timeout) is not None else "-"),
        (_t(lang, "last_heartbeat"), _format_datetime(resource.get("last_heartbeat"))),
        (_t(lang, "resource_status"), resource.get("status") or "-"),
        (_t(lang, "heartbeat_interval"), _format_value(resource.get("heartbeat_interval"), "s")),
    ]


def _job_rows(alert, policy, job, lang):
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    event_type = metadata.get("event_type") or metadata.get("alert_type") or trigger_rule.get("event_type")
    job_type = metadata.get("job_type") or trigger_rule.get("job_type") or job.get("job_type")
    return [
        (_t(lang, "job_event"), _job_label(event_type, lang)),
        (_t(lang, "job_event_key"), event_type or "-"),
        (_t(lang, "job_id"), job.get("id") or str(alert.resource_id or "-")),
        (_t(lang, "job_name"), job.get("name") or alert.resource_name or "-"),
        (_t(lang, "job_type"), job_type or "-"),
        (_t(lang, "job_status"), job.get("status") or "-"),
        (_t(lang, "progress"), _format_value(job.get("progress"), "%") if job.get("progress") is not None else "-"),
        (_t(lang, "started_at"), _format_datetime(job.get("started_at"))),
        (_t(lang, "completed_at"), _format_datetime(job.get("completed_at"))),
        (_t(lang, "duration"), _format_duration(job.get("duration"), lang)),
        (_t(lang, "source_resource"), job.get("source_resource") or "-"),
        (_t(lang, "repository"), job.get("repository") or "-"),
        (_t(lang, "proxy"), job.get("proxy") or "-"),
        (_t(lang, "error_message"), job.get("error_message") or alert.message or "-"),
    ]


def _system_rows(alert, policy, lang):
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    check_type = metadata.get("check_type") or trigger_rule.get("check_type")
    disk = metadata.get("disk") or {}
    rows = [
        (_t(lang, "check_type"), _system_label(check_type, lang)),
        (_t(lang, "check_key"), check_type or "-"),
        (_t(lang, "current_value"), _format_value(_alert_current_value(alert), _alert_unit(alert))),
        (_t(lang, "threshold"), _format_value(_alert_threshold_value(alert), _alert_unit(alert))),
    ]
    if disk:
        rows.extend(
            [
                (_t(lang, "disk_device"), disk.get("device") or "-"),
                (_t(lang, "mount_point"), disk.get("mountpoint") or "-"),
                (_t(lang, "disk_total"), _format_bytes(disk.get("total"))),
                (_t(lang, "disk_used"), _format_bytes(disk.get("used"))),
                (_t(lang, "disk_free"), _format_bytes(disk.get("free"))),
            ]
        )
    return rows


def _event_rows(alert, policy, lang):
    metadata = alert.metadata or {}
    return [
        (_t(lang, "event_category"), metadata.get("category") or "-"),
        (_t(lang, "event_type"), metadata.get("type") or "-"),
        (_t(lang, "actor"), metadata.get("actor") or "-"),
        (_t(lang, "target"), metadata.get("target") or "-"),
        (_t(lang, "event_metadata"), json.dumps(metadata.get("metadata") or metadata, ensure_ascii=False, default=str)),
    ]


def _trigger_condition(alert, label, operator, threshold, lang):
    if alert.type == "availability" and (alert.metadata or {}).get("check_type") == "heartbeat":
        return f"{label} {operator} {threshold}"
    return f"{label} {operator} {threshold}"


def _alert_label(alert, lang=None, policy=None):
    lang = _normalize_language(lang)
    metadata = alert.metadata or {}
    trigger_rule = policy.trigger_rule if policy else {}
    if alert.type == "metric":
        return _metric_label(metadata.get("metric_key") or trigger_rule.get("metric_key"), lang)
    if alert.type == "availability":
        return _availability_label(metadata.get("check_type") or trigger_rule.get("check_type"), lang)
    if alert.type == "system":
        return _system_label(metadata.get("check_type") or trigger_rule.get("check_type"), lang)
    if alert.type == "job":
        return _job_label(metadata.get("event_type") or trigger_rule.get("event_type"), lang)
    if alert.type == "event":
        return _event_label(metadata.get("type") or trigger_rule.get("event_type"), lang)
    return _t(lang, "alert_notification")


def _policy_for_alert(alert):
    if not alert.policy_id:
        return None
    try:
        return AlertPolicy.objects.get(id=alert.policy_id)
    except AlertPolicy.DoesNotExist:
        return None


def _resource_details(alert):
    if not alert.resource_id or not alert.resource_type:
        return {}

    try:
        if alert.resource_type == "system":
            import platform

            return {
                "ip": "-",
                "hostname": platform.node(),
                "role": "control-plane",
                "os": platform.platform(),
                "status": "active",
            }
        if alert.resource_type in {"sync_proxy", "agent_proxy"}:
            from nodes.models import ProxyNode

            proxy = ProxyNode.objects.filter(id=alert.resource_id).first()
            if not proxy:
                return {}
            return {
                "ip": proxy.internal_ip or _first_interface_ip(proxy.network_interfaces),
                "hostname": proxy.hostname,
                "role": proxy.role,
                "os": " ".join(part for part in [proxy.operating_system, proxy.os_version] if part),
                "cpu_cores": proxy.cpu_cores,
                "memory_usage": proxy.memory_usage,
                "disk_usage": proxy.disk_usage,
                "last_heartbeat": proxy.last_heartbeat,
                "heartbeat_interval": proxy.heartbeat_interval,
                "status": proxy.status,
            }
        if alert.resource_type == "gateway":
            from gateways.models import Gateway

            gateway = Gateway.objects.filter(id=alert.resource_id).first()
            if not gateway:
                return {}
            return {
                "ip": getattr(gateway, "internal_ip", None) or getattr(gateway, "hostname", None),
                "hostname": getattr(gateway, "hostname", None),
                "role": "gateway",
                "os": " ".join(part for part in [getattr(gateway, "operating_system", None), getattr(gateway, "os_version", None)] if part),
                "cpu_cores": getattr(gateway, "cpu_cores", None),
                "memory_usage": getattr(gateway, "memory_usage", None),
                "disk_usage": getattr(gateway, "disk_usage", None),
                "last_heartbeat": getattr(gateway, "last_heartbeat", None),
                "heartbeat_interval": getattr(gateway, "heartbeat_interval", None),
                "status": getattr(gateway, "status", None),
            }
        if alert.resource_type == "job":
            job = _job_details(alert)
            return {
                "role": job.get("job_type"),
                "hostname": job.get("proxy"),
                "status": job.get("status"),
            }
    except Exception as exc:
        logger.debug("Failed to load alert resource details: %s", exc)
    return {}


def _job_details(alert):
    job_id = alert.resource_id
    details = {}
    if not job_id:
        return details

    try:
        from backup_tasks.models import BackupTask

        task = BackupTask.objects.select_related("source_resource", "target_repository").filter(id=job_id).first()
        if task:
            proxy = getattr(getattr(task, "source_resource", None), "bound_node", None)
            return {
                "id": str(task.id),
                "name": task.name,
                "job_type": f"backup:{task.task_type}",
                "status": task.status,
                "progress": task.progress,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "duration": task.duration,
                "source_resource": getattr(task.source_resource, "name", None),
                "repository": getattr(task.target_repository, "name", None),
                "proxy": getattr(proxy, "name", None),
                "error_message": task.error_message or task.status_message,
            }
    except Exception as exc:
        logger.debug("Failed to load backup task details: %s", exc)

    try:
        from recovery_tasks.models import RecoveryTask

        task = RecoveryTask.objects.select_related("target_node", "snapshot").filter(id=job_id).first()
        if task:
            return {
                "id": str(task.id),
                "name": task.name,
                "job_type": f"recovery:{task.recovery_type}",
                "status": task.status,
                "progress": task.progress,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "duration": task.duration,
                "source_resource": getattr(task.snapshot, "source_path", None) or getattr(task.snapshot, "snapshot_id", None),
                "repository": "-",
                "proxy": getattr(task.target_node, "name", None),
                "error_message": task.error_message,
            }
    except Exception as exc:
        logger.debug("Failed to load recovery task details: %s", exc)

    try:
        from nodes.models import ProxyTask

        task = ProxyTask.objects.select_related("proxy").filter(id=job_id).first()
        if task:
            return {
                "id": str(task.id),
                "name": str(task.task_type),
                "job_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "started_at": getattr(task, "started_at", None),
                "completed_at": getattr(task, "completed_at", None),
                "duration": _duration_seconds(getattr(task, "started_at", None), getattr(task, "completed_at", None)),
                "source_resource": "-",
                "repository": "-",
                "proxy": getattr(task.proxy, "name", None),
                "error_message": getattr(task, "error_message", None) or getattr(task, "progress_message", None),
            }
    except Exception as exc:
        logger.debug("Failed to load proxy task details: %s", exc)

    return details


def _first_interface_ip(interfaces):
    for item in interfaces or []:
        if isinstance(item, dict):
            for key in ("ip", "ip_address", "address", "addr"):
                value = item.get(key)
                if value:
                    return value
    return None


def _section(title, rows):
    cells = "".join(
        f"""
        <tr>
          <td style="width:170px;padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;">{_escape(label)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#0f172a;font-size:13px;font-weight:600;">{_escape(value)}</td>
        </tr>"""
        for label, value in rows
    )
    return f"""
      <h2 style="margin:22px 0 10px;font-size:15px;color:#0f172a;">{_escape(title)}</h2>
      <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
        {cells}
      </table>
    """


def _pill(label, value, color):
    return f"""
      <div style="border:1px solid #e2e8f0;border-radius:8px;padding:9px 12px;background:#ffffff;">
        <div style="font-size:11px;color:#64748b;margin-bottom:3px;">{_escape(label)}</div>
        <div style="font-size:13px;color:{color};font-weight:700;">{_escape(value)}</div>
      </div>
    """


def _metric_label(metric_key, lang=None):
    lang = _normalize_language(lang)
    labels = {
        "zh": {
            "cpu_usage": "CPU 利用率告警",
            "memory_usage": "内存利用率告警",
            "disk_usage": "磁盘利用率告警",
            "network_rx": "网络入流量告警",
            "network_tx": "网络出流量告警",
            "capacity_usage": "容量利用率告警",
            "used_size": "已用容量告警",
            "free_size": "可用容量告警",
            "data_size": "数据量告警",
            "file_count": "文件数量告警",
            "swap_usage": "Swap 利用率告警",
            "disk_read_bytes": "磁盘读取量告警",
            "disk_write_bytes": "磁盘写入量告警",
            "load_1m": "1 分钟负载告警",
            "load_5m": "5 分钟负载告警",
            "load_15m": "15 分钟负载告警",
        },
        "en": {
            "cpu_usage": "CPU Utilization Alert",
            "memory_usage": "Memory Utilization Alert",
            "disk_usage": "Disk Utilization Alert",
            "network_rx": "Network Inbound Traffic Alert",
            "network_tx": "Network Outbound Traffic Alert",
            "capacity_usage": "Capacity Utilization Alert",
            "used_size": "Used Capacity Alert",
            "free_size": "Free Capacity Alert",
            "data_size": "Data Size Alert",
            "file_count": "File Count Alert",
            "swap_usage": "Swap Utilization Alert",
            "disk_read_bytes": "Disk Read Bytes Alert",
            "disk_write_bytes": "Disk Write Bytes Alert",
            "load_1m": "1-Minute Load Alert",
            "load_5m": "5-Minute Load Alert",
            "load_15m": "15-Minute Load Alert",
        },
    }
    return labels[lang].get(metric_key, metric_key or _t(lang, "alert_notification"))


def _availability_label(check_type, lang=None):
    lang = _normalize_language(lang)
    labels = {
        "zh": {
            "heartbeat": "心跳超时告警",
            "connection": "连接可用性告警",
            "api_health": "API 健康检查告警",
        },
        "en": {
            "heartbeat": "Heartbeat Timeout Alert",
            "connection": "Connection Availability Alert",
            "api_health": "API Health Alert",
        },
    }
    return labels[lang].get(check_type, _t(lang, "availability_alert"))


def _system_label(check_type, lang=None):
    lang = _normalize_language(lang)
    labels = {
        "zh": {
            "disk_space_low": "系统磁盘空间告警",
            "database_unreachable": "数据库不可达告警",
            "celery_worker_down": "Celery Worker 异常告警",
            "scheduler_down": "调度器异常告警",
            "api_service_down": "API 服务异常告警",
            "service_health": "系统服务健康告警",
        },
        "en": {
            "disk_space_low": "System Disk Space Alert",
            "database_unreachable": "Database Unreachable Alert",
            "celery_worker_down": "Celery Worker Down Alert",
            "scheduler_down": "Scheduler Down Alert",
            "api_service_down": "API Service Down Alert",
            "service_health": "System Service Health Alert",
        },
    }
    return labels[lang].get(check_type, _t(lang, "system_alert"))


def _job_label(event_type, lang=None):
    lang = _normalize_language(lang)
    labels = {
        "zh": {
            "job_failed": "任务失败告警",
            "job_timeout": "任务超时告警",
            "retry_exceeded": "任务重试超限告警",
            "partial_success": "任务部分成功告警",
        },
        "en": {
            "job_failed": "Job Failed Alert",
            "job_timeout": "Job Timeout Alert",
            "retry_exceeded": "Retry Exceeded Alert",
            "partial_success": "Partial Success Alert",
        },
    }
    return labels[lang].get(event_type, _t(lang, "job_alert"))


def _event_label(event_type, lang=None):
    lang = _normalize_language(lang)
    labels = {
        "zh": "平台事件告警",
        "en": "Platform Event Alert",
    }
    if event_type:
        return f"{labels[lang]}: {event_type}"
    return labels[lang]


def _severity_color(severity):
    return {
        "critical": "#dc2626",
        "warning": "#d97706",
        "info": "#2563eb",
    }.get(severity, "#475569")


def _format_value(value, unit=None):
    if value is None:
        return "-"
    try:
        number = float(value)
        rendered = f"{number:.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        rendered = str(value)
    return f"{rendered}{unit or ''}"


def _alert_current_value(alert):
    if alert.current_value is not None:
        return alert.current_value
    metadata = alert.metadata or {}
    if metadata.get("current_value") is not None:
        return metadata.get("current_value")
    parsed = _legacy_availability_seconds(alert)
    if parsed:
        return parsed[0]
    return None


def _alert_threshold_value(alert):
    if alert.threshold_value is not None:
        return alert.threshold_value
    metadata = alert.metadata or {}
    if metadata.get("timeout_seconds") is not None:
        return metadata.get("timeout_seconds")
    parsed = _legacy_availability_seconds(alert)
    if parsed:
        return parsed[1]
    return None


def _alert_unit(alert):
    if alert.unit:
        return alert.unit
    metadata = alert.metadata or {}
    if alert.type == "availability" and (metadata.get("check_type") == "heartbeat" or metadata.get("timeout_seconds") is not None):
        return "s"
    return None


def _legacy_availability_seconds(alert):
    if alert.type != "availability":
        return None
    match = re.search(r"(?P<current>\d+(?:\.\d+)?)s\s*>\s*(?P<threshold>\d+(?:\.\d+)?)s", alert.message or "")
    if not match:
        return None
    return match.group("current"), match.group("threshold")


def _email_metadata(alert):
    metadata = dict(alert.metadata or {})
    metadata.pop("raw_message", None)
    if alert.type == "availability":
        metadata.setdefault("current_value", _format_value(_alert_current_value(alert), _alert_unit(alert)))
        metadata.setdefault("threshold_value", _format_value(_alert_threshold_value(alert), _alert_unit(alert)))
    return metadata


def _format_percent(value):
    return _format_value(value, "%") if value is not None else "-"


def _format_bytes(value):
    if value in (None, ""):
        return "-"
    try:
        size = float(value)
    except (TypeError, ValueError):
        return str(value)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}".replace(".00", "")


def _format_duration(seconds, lang=None):
    lang = _normalize_language(lang)
    if seconds in (None, "", 0):
        return "-"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return str(seconds)
    if lang == "zh":
        if seconds < 60:
            return f"{seconds} 秒"
        if seconds < 3600:
            return f"{seconds // 60} 分钟"
        return f"{seconds // 3600} 小时 {seconds % 3600 // 60} 分钟"
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    return f"{seconds // 3600} hours {seconds % 3600 // 60} minutes"


def _duration_seconds(started_at, completed_at):
    if not started_at:
        return None
    end_at = completed_at or timezone.now()
    return int((end_at - started_at).total_seconds())


def _format_datetime(value):
    if not value:
        return "-"
    if isinstance(value, str):
        return value
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S %Z")


def _escape(value):
    if value is None:
        return "-"
    return html.escape(str(value))


def _channel_language(channel):
    config = channel.config or {}
    return _normalize_language(
        config.get("notification_language")
        or config.get("language")
        or config.get("locale")
    )


def _normalize_language(lang=None):
    if not lang:
        return "zh"
    value = str(lang).lower()
    if value.startswith("zh"):
        return "zh"
    return "en"


def _t(lang, key):
    lang = _normalize_language(lang)
    messages = {
        "zh": {
            "firing_state": "触发",
            "resolved_state": "恢复",
            "firing_status": "正在触发",
            "resolved_status": "已恢复",
            "current": "当前",
            "threshold": "阈值",
            "alert_status": "告警状态",
            "severity": "告警级别",
            "alert_type": "告警类型",
            "current_value": "当前值",
            "trigger_condition": "触发条件",
            "duration": "持续时间",
            "evaluation_interval": "检测周期",
            "first_triggered": "首次触发",
            "last_triggered": "最近触发",
            "resolved_at": "恢复时间",
            "resource_name": "资源名称",
            "resource_id": "资源 ID",
            "resource_type": "资源类型",
            "resource_ip": "资源 IP",
            "hostname": "主机名",
            "role": "角色",
            "os": "操作系统",
            "cpu_cores": "CPU 核数",
            "memory_usage": "内存使用率",
            "disk_usage": "磁盘使用率",
            "last_heartbeat": "最后心跳",
            "policy_name": "策略名称",
            "policy_id": "策略 ID",
            "policy_status": "策略状态",
            "scope": "监控范围",
            "channel_count": "通知渠道数",
            "enabled": "启用",
            "disabled": "禁用",
            "resource": "资源",
            "alert_overview": "告警概览",
            "resource_info": "资源信息",
            "policy_info": "策略信息",
            "alert_title": "告警标题",
            "message": "告警描述",
            "alert_notification": "告警通知",
            "availability_alert": "可用性告警",
            "system_alert": "系统告警",
            "job_alert": "任务告警",
            "alert_details": "告警详情",
            "metric_details": "指标详情",
            "availability_details": "可用性详情",
            "job_details": "任务详情",
            "system_details": "系统详情",
            "event_details": "事件详情",
            "metric": "指标",
            "metric_key": "指标 Key",
            "check_type": "检查类型",
            "check_key": "检查 Key",
            "heartbeat_age": "心跳超时时长",
            "timeout_threshold": "超时阈值",
            "resource_status": "资源状态",
            "heartbeat_interval": "心跳间隔",
            "job_event": "任务事件",
            "job_event_key": "任务事件 Key",
            "job_id": "任务 ID",
            "job_name": "任务名称",
            "job_type": "任务类型",
            "job_status": "任务状态",
            "progress": "进度",
            "started_at": "开始时间",
            "completed_at": "完成时间",
            "source_resource": "源端资源",
            "repository": "仓库",
            "proxy": "代理",
            "error_message": "错误信息",
            "disk_device": "磁盘设备",
            "mount_point": "挂载点",
            "disk_total": "磁盘总量",
            "disk_used": "磁盘已用",
            "disk_free": "磁盘可用",
            "event_category": "事件分类",
            "event_type": "事件类型",
            "actor": "操作者",
            "event_metadata": "事件元数据",
        },
        "en": {
            "firing_state": "Firing",
            "resolved_state": "Resolved",
            "firing_status": "Firing",
            "resolved_status": "Resolved",
            "current": "Current",
            "threshold": "Threshold",
            "alert_status": "Alert Status",
            "severity": "Severity",
            "alert_type": "Alert Type",
            "current_value": "Current Value",
            "trigger_condition": "Trigger Condition",
            "duration": "Duration",
            "evaluation_interval": "Evaluation Interval",
            "first_triggered": "First Triggered",
            "last_triggered": "Last Triggered",
            "resolved_at": "Resolved At",
            "resource_name": "Resource Name",
            "resource_id": "Resource ID",
            "resource_type": "Resource Type",
            "resource_ip": "Resource IP",
            "hostname": "Hostname",
            "role": "Role",
            "os": "Operating System",
            "cpu_cores": "CPU Cores",
            "memory_usage": "Memory Usage",
            "disk_usage": "Disk Usage",
            "last_heartbeat": "Last Heartbeat",
            "policy_name": "Policy Name",
            "policy_id": "Policy ID",
            "policy_status": "Policy Status",
            "scope": "Scope",
            "channel_count": "Notification Channels",
            "enabled": "Enabled",
            "disabled": "Disabled",
            "resource": "Resource",
            "alert_overview": "Alert Overview",
            "resource_info": "Resource Information",
            "policy_info": "Policy Information",
            "alert_title": "Alert Title",
            "message": "Message",
            "alert_notification": "Alert Notification",
            "availability_alert": "Availability Alert",
            "system_alert": "System Alert",
            "job_alert": "Job Alert",
            "alert_details": "Alert Details",
            "metric_details": "Metric Details",
            "availability_details": "Availability Details",
            "job_details": "Job Details",
            "system_details": "System Details",
            "event_details": "Event Details",
            "metric": "Metric",
            "metric_key": "Metric Key",
            "check_type": "Check Type",
            "check_key": "Check Key",
            "heartbeat_age": "Heartbeat Age",
            "timeout_threshold": "Timeout Threshold",
            "resource_status": "Resource Status",
            "heartbeat_interval": "Heartbeat Interval",
            "job_event": "Job Event",
            "job_event_key": "Job Event Key",
            "job_id": "Job ID",
            "job_name": "Job Name",
            "job_type": "Job Type",
            "job_status": "Job Status",
            "progress": "Progress",
            "started_at": "Started At",
            "completed_at": "Completed At",
            "source_resource": "Source Resource",
            "repository": "Repository",
            "proxy": "Proxy",
            "error_message": "Error Message",
            "disk_device": "Disk Device",
            "mount_point": "Mount Point",
            "disk_total": "Disk Total",
            "disk_used": "Disk Used",
            "disk_free": "Disk Free",
            "event_category": "Event Category",
            "event_type": "Event Type",
            "actor": "Actor",
            "event_metadata": "Event Metadata",
        },
    }
    return messages[lang].get(key, key)


def _send_webhook(channel, payload):
    config = channel.config or {}
    url = config.get("url")
    if not url:
        raise ValueError("Webhook channel requires url.")

    method = config.get("method") or "POST"
    headers = {"Content-Type": "application/json", **(config.get("headers") or {})}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Webhook returned HTTP {exc.code}") from exc


def _send_dingtalk(channel, message):
    """Send notification to DingTalk."""
    import time
    import hmac
    import base64
    import hashlib

    config = channel.config or {}
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("DingTalk channel requires webhook_url.")

    secret = config.get("secret")
    if secret:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "text",
        "text": {"content": f"[HyperFileLens] {message}"},
    }

    headers = {"Content-Type": "application/json"}
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"DingTalk returned HTTP {exc.code}") from exc


def _send_wecom(channel, message):
    """Send notification to WeCom."""
    config = channel.config or {}
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("WeCom channel requires webhook_url.")

    payload = {
        "msgtype": "text",
        "text": {"content": f"[HyperFileLens] {message}"},
    }

    headers = {"Content-Type": "application/json"}
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"WeCom returned HTTP {exc.code}") from exc


def _payload(alert, resolved):
    policy = _policy_for_alert(alert)
    trigger_rule = policy.trigger_rule if policy else {}
    resource = _resource_details(alert)
    return {
        "id": str(alert.id),
        "type": alert.type,
        "severity": alert.severity,
        "status": "resolved" if resolved else alert.status,
        "title": alert.title,
        "message": alert.message,
        "resource_type": alert.resource_type,
        "resource_id": str(alert.resource_id) if alert.resource_id else None,
        "resource_name": alert.resource_name,
        "resource_ip": resource.get("ip"),
        "resource_hostname": resource.get("hostname"),
        "resource_role": resource.get("role"),
        "resource_os": resource.get("os"),
        "resource_cpu_cores": resource.get("cpu_cores"),
        "current_value": str(_alert_current_value(alert)) if _alert_current_value(alert) is not None else None,
        "threshold_value": str(_alert_threshold_value(alert)) if _alert_threshold_value(alert) is not None else None,
        "unit": _alert_unit(alert),
        "metric_key": (alert.metadata or {}).get("metric_key") or trigger_rule.get("metric_key"),
        "operator": (alert.metadata or {}).get("operator") or trigger_rule.get("operator"),
        "duration_seconds": trigger_rule.get("duration_seconds"),
        "evaluation_interval_seconds": trigger_rule.get("evaluation_interval_seconds"),
        "policy_id": str(policy.id) if policy else None,
        "policy_name": policy.name if policy else None,
        "first_triggered_at": alert.first_triggered_at.isoformat() if alert.first_triggered_at else None,
        "last_triggered_at": alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "fingerprint": alert.fingerprint,
        "metadata": alert.metadata or {},
    }
