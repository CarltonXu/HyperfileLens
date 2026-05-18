from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("backup_tasks", "0005_backuptask_policy_effective_config"),
        ("nodes", "0014_restore_proxy_metrics"),
    ]

    operations = [
        migrations.AddField(
            model_name="backuptask",
            name="execution_mode",
            field=models.CharField(
                choices=[
                    ("pinned", "Pinned Proxy"),
                    ("preferred", "Preferred Proxy with Fallback"),
                    ("auto", "Auto Select Proxy"),
                ],
                default="pinned",
                help_text="How the execution proxy is selected for this task",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="backuptask",
            name="preferred_execution_node",
            field=models.ForeignKey(
                blank=True,
                help_text="Preferred execution proxy used when execution mode allows fallback",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="preferred_backup_tasks",
                to="nodes.proxynode",
            ),
        ),
    ]
