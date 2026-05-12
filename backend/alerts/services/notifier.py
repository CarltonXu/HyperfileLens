"""Notification delivery for alert records."""

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.mail import send_mail

from alerts.choices import NotificationChannelType, NotificationStatus
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
        send_mail(
            subject="HyperFileLens alert channel test",
            message="This is a test notification from HyperFileLens.",
            from_email=config.get("from_email"),
            recipient_list=recipients,
            fail_silently=False,
        )
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
            if channel.type == NotificationChannelType.EMAIL:
                _send_email(channel, alert, resolved)
            elif channel.type == NotificationChannelType.WEBHOOK:
                _send_webhook(channel, _payload(alert, resolved))
            elif channel.type == NotificationChannelType.DINGTALK:
                _send_dingtalk(channel, f"{'Resolved' if resolved else 'Alert'}: {alert.title}\n{alert.message or ''}")
            elif channel.type == NotificationChannelType.WECOM:
                _send_wecom(channel, f"{'Resolved' if resolved else 'Alert'}: {alert.title}\n{alert.message or ''}")
            else:
                logger.info("Notification channel type %s is reserved.", channel.type)

            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                status=NotificationStatus.SUCCESS,
            )
        except Exception as exc:
            logger.exception("Alert notification failed: %s", exc)
            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                status=NotificationStatus.FAILED,
                error_message=str(exc),
            )


def _send_email(channel, alert, resolved):
    config = channel.config or {}
    recipients = config.get("to_emails") or []
    if not recipients:
        raise ValueError("Email channel requires to_emails.")

    prefix = "Resolved" if resolved else "Alert"
    send_mail(
        subject=f"[HyperFileLens] {prefix}: {alert.title}",
        message=alert.message or alert.title,
        from_email=config.get("from_email"),
        recipient_list=recipients,
        fail_silently=False,
    )


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
        "current_value": str(alert.current_value) if alert.current_value is not None else None,
        "threshold_value": str(alert.threshold_value) if alert.threshold_value is not None else None,
        "unit": alert.unit,
    }
