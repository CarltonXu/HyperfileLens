"""Job alert event handling."""

from alerts.models import AlertPolicy
from alerts.services.evaluator import fire_alert, resolve_alert


def on_job_finished(job):
    status = getattr(job, "status", "")
    if status in ["failed", "timeout", "partial_success"]:
        handle_job_event(job)
    elif status == "success":
        recover_job_alerts(job)


def handle_job_event(job):
    event_type = "job_failed" if getattr(job, "status", "") == "failed" else f"job_{getattr(job, 'status', '')}"
    job_type = getattr(job, "task_type", None) or getattr(job, "type", None)
    for policy in AlertPolicy.objects.filter(enabled=True, type="job"):
        rule = policy.trigger_rule or {}
        if rule.get("job_type") == job_type and rule.get("event_type") == event_type:
            fire_alert(
                policy,
                resource=job,
                title=f"Job Alert: {event_type}",
                message=f"Job {getattr(job, 'id', '')} triggered {event_type}.",
                alert_key=f"{job_type}:{event_type}",
                metadata={
                    "event_type": event_type,
                    "job_type": job_type,
                    "job_status": status,
                    "error_message": getattr(job, "error_message", "") or getattr(job, "status_message", ""),
                },
            )


def recover_job_alerts(job):
    job_id = getattr(job, "id", None)
    if not job_id:
        return
    from alerts.models import AlertRecord

    for alert in AlertRecord.objects.filter(resource_id=job_id, status__in=["pending", "firing", "acknowledged"]):
        resolve_alert(alert)
