import uuid
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0002_alertchannel'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemMetric',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('cpu', models.JSONField(blank=True, default=dict)),
                ('memory', models.JSONField(blank=True, default=dict)),
                ('swap', models.JSONField(blank=True, default=dict)),
                ('disks', models.JSONField(blank=True, default=list)),
                ('disk_io', models.JSONField(blank=True, default=list)),
                ('networks', models.JSONField(blank=True, default=list)),
                ('load_average', models.JSONField(blank=True, default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'verbose_name': 'System Metric',
                'verbose_name_plural': 'System Metrics',
                'db_table': 'alerts_system_metric',
                'ordering': ['-timestamp'],
            },
        ),
    ]
