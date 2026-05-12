"""Celery tasks for the global alert center."""

from celery import shared_task

from .models import SystemMetric
from .services.evaluator import evaluate_alert_policies as run_evaluation
from .views import collect_system_sample


@shared_task
def evaluate_alert_policies():
    run_evaluation()
    return {"status": "ok"}


@shared_task
def collect_system_metrics():
    sample = collect_system_sample()
    SystemMetric.objects.create(**sample)
    return sample


@shared_task
def cleanup_old_metrics(days_to_keep=7):
    from django.utils import timezone

    cutoff = timezone.now() - timezone.timedelta(days=days_to_keep)
    count, _ = SystemMetric.objects.filter(timestamp__lt=cutoff).delete()
    return count
