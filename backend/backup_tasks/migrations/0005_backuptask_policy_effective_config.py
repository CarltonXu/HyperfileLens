from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backup_tasks', '0004_backuptask_is_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuptask',
            name='effective_policy',
            field=models.JSONField(blank=True, default=dict, help_text='Resolved Kopia policy used for the latest execution'),
        ),
        migrations.AddField(
            model_name='backuptask',
            name='policy_overrides',
            field=models.JSONField(blank=True, default=dict, help_text='Task-level overrides merged on top of the associated backup policy'),
        ),
    ]
