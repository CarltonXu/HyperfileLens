from django.db import migrations, models


def backfill_notification_type(apps, schema_editor):
    AlertRecord = apps.get_model("alerts", "AlertRecord")
    NotificationLog = apps.get_model("alerts", "NotificationLog")

    resolved_at_by_alert = {
        alert.id: alert.resolved_at
        for alert in AlertRecord.objects.exclude(resolved_at__isnull=True).only("id", "resolved_at")
    }

    for log in NotificationLog.objects.all().iterator():
        resolved_at = resolved_at_by_alert.get(log.alert_record_id)
        if resolved_at and log.sent_at and log.sent_at >= resolved_at:
            log.notification_type = "resolved"
        else:
            log.notification_type = "firing"
        log.save(update_fields=["notification_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("alerts", "0005_rebuild_global_alert_center"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationlog",
            name="notification_type",
            field=models.CharField(
                choices=[("firing", "Firing"), ("resolved", "Resolved")],
                default="firing",
                max_length=50,
            ),
        ),
        migrations.RunPython(backfill_notification_type, migrations.RunPython.noop),
    ]
