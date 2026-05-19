# Generated manually for downloadable recovery exports.

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('backup_tasks', '0008_snapshot_retention_state'),
        ('nodes', '0015_proxy_retention_task_types'),
        ('recovery_tasks', '0005_alter_recoveryrun_status_alter_recoverytask_status'),
        ('repository', '0007_repository_kopia_password'),
        ('tenants', '0006_alter_tenantinvitation_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecoveryExport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Export job name', max_length=255)),
                ('description', models.TextField(blank=True)),
                ('selected_paths', models.JSONField(blank=True, default=list)),
                ('package_format', models.CharField(choices=[('zip', 'ZIP')], default='zip', max_length=16)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('dispatched', 'Dispatched'), ('running', 'Running'), ('packaging', 'Packaging'), ('ready', 'Ready'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', max_length=20)),
                ('progress', models.IntegerField(default=0)),
                ('status_message', models.TextField(blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('current_file', models.CharField(blank=True, max_length=1024)),
                ('total_files', models.IntegerField(default=0)),
                ('processed_files', models.IntegerField(default=0)),
                ('total_size', models.BigIntegerField(default=0)),
                ('processed_size', models.BigIntegerField(default=0)),
                ('package_size', models.BigIntegerField(default=0)),
                ('checksum', models.CharField(blank=True, max_length=128)),
                ('file_path', models.CharField(blank=True, max_length=4096)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('executor_node', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recovery_exports', to='nodes.node')),
                ('proxy_task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recovery_exports', to='nodes.proxytask')),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_exports', to='repository.repository')),
                ('snapshot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_exports', to='backup_tasks.backupsnapshot')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recovery_exports', to='tenants.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_exports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'recovery_exports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='recoveryexport',
            index=models.Index(fields=['status', '-created_at'], name='recovery_ex_status_3f8e82_idx'),
        ),
        migrations.AddIndex(
            model_name='recoveryexport',
            index=models.Index(fields=['snapshot', '-created_at'], name='recovery_ex_snapsho_7f013b_idx'),
        ),
        migrations.AddIndex(
            model_name='recoveryexport',
            index=models.Index(fields=['tenant', '-created_at'], name='recovery_ex_tenant__ddaf59_idx'),
        ),
    ]
