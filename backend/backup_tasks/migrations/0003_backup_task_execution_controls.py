from django.db import migrations, models
import django.db.models.deletion


def add_missing_columns(apps, schema_editor):
    BackupTask = apps.get_model("backup_tasks", "BackupTask")
    table_name = BackupTask._meta.db_table
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }

    fields = [
        (
            "bandwidth_limit_kbps",
            models.IntegerField(
                null=True,
                blank=True,
                help_text="Optional bandwidth limit in KB/s",
            ),
        ),
        (
            "enable_checkpoint",
            models.BooleanField(
                default=True,
                help_text="Enable resumable backup checkpoints",
            ),
        ),
        (
            "checkpoint_interval_minutes",
            models.IntegerField(
                default=15,
                help_text="Checkpoint interval in minutes",
            ),
        ),
        (
            "compression_level",
            models.IntegerField(
                default=6,
                help_text="Compression level, usually 0-9 depending on algorithm",
            ),
        ),
        (
            "max_concurrent_files",
            models.IntegerField(
                default=4,
                help_text="Maximum files processed concurrently",
            ),
        ),
        (
            "verify_checksum",
            models.BooleanField(
                default=True,
                help_text="Verify file checksum after backup",
            ),
        ),
        (
            "max_retries",
            models.IntegerField(
                default=3,
                help_text="Maximum retry attempts for this backup task",
            ),
        ),
        (
            "retry_count",
            models.IntegerField(
                default=0,
                help_text="Current retry count",
            ),
        ),
        (
            "estimated_completion_at",
            models.DateTimeField(
                null=True,
                blank=True,
                help_text="Estimated completion time",
            ),
        ),
        (
            "parent_task",
            models.ForeignKey(
                BackupTask,
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name="child_tasks",
                help_text="Parent task for retry or derived backup executions",
            ),
        ),
    ]

    for name, field in fields:
        column_name = f"{name}_id" if name == "parent_task" else name
        if column_name in existing_columns:
            continue
        field.set_attributes_from_name(name)
        schema_editor.add_field(BackupTask, field)


class Migration(migrations.Migration):

    dependencies = [
        ("backup_tasks", "0002_add_tenant_to_models"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_missing_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="backuptask",
                    name="bandwidth_limit_kbps",
                    field=models.IntegerField(
                        blank=True,
                        help_text="Optional bandwidth limit in KB/s",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="enable_checkpoint",
                    field=models.BooleanField(
                        default=True,
                        help_text="Enable resumable backup checkpoints",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="checkpoint_interval_minutes",
                    field=models.IntegerField(
                        default=15,
                        help_text="Checkpoint interval in minutes",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="compression_level",
                    field=models.IntegerField(
                        default=6,
                        help_text="Compression level, usually 0-9 depending on algorithm",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="max_concurrent_files",
                    field=models.IntegerField(
                        default=4,
                        help_text="Maximum files processed concurrently",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="verify_checksum",
                    field=models.BooleanField(
                        default=True,
                        help_text="Verify file checksum after backup",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="max_retries",
                    field=models.IntegerField(
                        default=3,
                        help_text="Maximum retry attempts for this backup task",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="retry_count",
                    field=models.IntegerField(
                        default=0,
                        help_text="Current retry count",
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="estimated_completion_at",
                    field=models.DateTimeField(
                        blank=True,
                        help_text="Estimated completion time",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="backuptask",
                    name="parent_task",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Parent task for retry or derived backup executions",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_tasks",
                        to="backup_tasks.backuptask",
                    ),
                ),
            ],
        ),
    ]
