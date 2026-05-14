from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backup_tasks", "0003_backup_task_execution_controls"),
    ]

    operations = [
        migrations.AddField(
            model_name="backuptask",
            name="is_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Whether this backup task is enabled for manual or scheduled execution",
            ),
        ),
    ]
