# Generated manually for global alert notification channels.

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertChannel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('channel_type', models.CharField(choices=[('email', 'Email'), ('webhook', 'Webhook')], max_length=20)),
                ('enabled', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('last_test_at', models.DateTimeField(blank=True, null=True)),
                ('last_test_result', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Alert Channel',
                'verbose_name_plural': 'Alert Channels',
                'db_table': 'alerts_channel',
                'ordering': ['-is_default', 'name'],
            },
        ),
    ]
