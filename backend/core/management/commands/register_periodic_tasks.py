"""Register Celery beat tasks in django-celery-beat."""

import json

from celery.schedules import crontab, schedule
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from core.celery import app


class Command(BaseCommand):
    help = "Register configured Celery beat tasks in django-celery-beat."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for name, entry in app.conf.beat_schedule.items():
            task_name = entry["task"]
            schedule_value = entry["schedule"]
            defaults = {
                "task": task_name,
                "kwargs": json.dumps(entry.get("kwargs", {})),
                "args": json.dumps(entry.get("args", [])),
                "enabled": entry.get("enabled", True),
            }

            if isinstance(schedule_value, (int, float)):
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=int(schedule_value),
                    period=IntervalSchedule.SECONDS,
                )
                defaults["interval"] = interval
                defaults["crontab"] = None
            elif isinstance(schedule_value, schedule):
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=int(schedule_value.run_every.total_seconds()),
                    period=IntervalSchedule.SECONDS,
                )
                defaults["interval"] = interval
                defaults["crontab"] = None
            elif isinstance(schedule_value, crontab):
                crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=str(schedule_value._orig_minute),
                    hour=str(schedule_value._orig_hour),
                    day_of_week=str(schedule_value._orig_day_of_week),
                    day_of_month=str(schedule_value._orig_day_of_month),
                    month_of_year=str(schedule_value._orig_month_of_year),
                    timezone=app.conf.timezone,
                )
                defaults["crontab"] = crontab_schedule
                defaults["interval"] = None
            else:
                self.stderr.write(f"Skipping unsupported schedule for {name}: {schedule_value!r}")
                continue

            _, was_created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Registered periodic tasks: created={created}, updated={updated}"))
