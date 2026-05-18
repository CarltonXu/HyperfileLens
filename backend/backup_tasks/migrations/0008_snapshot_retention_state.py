from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backup_tasks', '0007_backuptask_last_run_status_backuptaskrun'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupsnapshot',
            name='snapshot_status',
            field=models.CharField(
                choices=[
                    ('available', 'Available'),
                    ('pending_prune', 'Pending Prune'),
                    ('pruned', 'Pruned'),
                    ('missing', 'Missing'),
                    ('delete_failed', 'Delete Failed'),
                ],
                default='available',
                help_text='Platform-observed availability state reconciled from Kopia',
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='retention_reasons',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Retention reasons observed from Kopia or calculated by platform',
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='last_synced_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Last time this snapshot was reconciled with Kopia',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='missing_count',
            field=models.IntegerField(
                default=0,
                help_text='Consecutive reconciliation cycles where Kopia did not return this snapshot',
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='pruned_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When Kopia deletion was confirmed by reconciliation',
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name='backupsnapshot',
            index=models.Index(fields=['snapshot_status'], name='backup_snap_snapsho_861ddd_idx'),
        ),
        migrations.AddIndex(
            model_name='backupsnapshot',
            index=models.Index(fields=['last_synced_at'], name='backup_snap_last_sy_a2a77b_idx'),
        ),
    ]
