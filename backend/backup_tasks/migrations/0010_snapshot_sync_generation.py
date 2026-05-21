from django.db import migrations, models


def populate_kopia_snapshot_identity(apps, schema_editor):
    BackupSnapshot = apps.get_model('backup_tasks', 'BackupSnapshot')
    seen = set()
    for snapshot in BackupSnapshot.objects.all().order_by('task_id', 'created_at', 'id'):
        metadata = snapshot.metadata or {}
        root_object_id = str(metadata.get('root_object_id') or snapshot.manifest_path or '').strip()
        snapshot_id = str(metadata.get('snapshot_id') or snapshot.storage_path or '').strip()
        updates = {}
        if root_object_id:
            updates['kopia_root_object_id'] = root_object_id
        if snapshot_id and not metadata.get('no_changes'):
            key = (snapshot.task_id, snapshot_id)
            if key not in seen:
                updates['kopia_snapshot_id'] = snapshot_id
                seen.add(key)
        if updates:
            BackupSnapshot.objects.filter(id=snapshot.id).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('backup_tasks', '0009_backup_partial_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuptask',
            name='latest_snapshot_sync_task_id',
            field=models.UUIDField(
                blank=True,
                help_text="Latest proxy task allowed to reconcile this task's Kopia snapshots",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='backuptask',
            name='latest_snapshot_sync_started_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the latest snapshot reconciliation was dispatched',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='kopia_snapshot_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Kopia snapshot manifest ID. This is the canonical snapshot identity.',
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name='backupsnapshot',
            name='kopia_root_object_id',
            field=models.CharField(
                blank=True,
                help_text='Kopia root object ID used for browsing/restoring snapshot contents.',
                max_length=128,
            ),
        ),
        migrations.RunPython(populate_kopia_snapshot_identity, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='backupsnapshot',
            constraint=models.UniqueConstraint(
                condition=~models.Q(kopia_snapshot_id=''),
                fields=('task', 'kopia_snapshot_id'),
                name='uniq_backup_snapshot_task_kopia_id',
            ),
        ),
    ]
