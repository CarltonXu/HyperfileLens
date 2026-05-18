from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0014_restore_proxy_metrics'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proxytask',
            name='task_type',
            field=models.CharField(
                choices=[
                    ('backup', 'Backup'),
                    ('restore', 'Restore'),
                    ('mount', 'Mount'),
                    ('unmount', 'Unmount'),
                    ('snapshot_list', 'Snapshot List'),
                    ('snapshot_delete', 'Snapshot Delete'),
                    ('kopia_maintenance', 'Kopia Maintenance'),
                    ('policy_show', 'Policy Show'),
                    ('verify', 'Verify'),
                    ('test_storage', 'Test Storage'),
                    ('init_repository', 'Init Repository'),
                ],
                help_text='Type of task',
                max_length=20,
            ),
        ),
    ]
