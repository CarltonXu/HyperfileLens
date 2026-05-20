# Generated manually for partial backup results.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backup_tasks', '0008_snapshot_retention_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='backuptask',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('partial', 'Partial Success'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('paused', 'Paused')], default='pending', help_text='Current task status', max_length=20),
        ),
        migrations.AlterField(
            model_name='backuptask',
            name='last_run_status',
            field=models.CharField(blank=True, help_text='Status of the latest execution run', max_length=20),
        ),
        migrations.AlterField(
            model_name='backuptaskrun',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('dispatched', 'Dispatched'), ('running', 'Running'), ('completed', 'Completed'), ('partial', 'Partial Success'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('timeout', 'Timeout')], default='pending', max_length=20),
        ),
    ]
