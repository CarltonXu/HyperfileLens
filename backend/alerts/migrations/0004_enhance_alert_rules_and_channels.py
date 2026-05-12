import uuid
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0003_systemmetric'),
    ]

    operations = [
        # Update AlertRule model
        migrations.AddField(
            model_name='alertrule',
            name='category',
            field=models.CharField(
                choices=[
                    ('system', 'System'),
                    ('tasks', 'Tasks'),
                    ('resources', 'Resources'),
                    ('repository', 'Repository'),
                    ('nodes', 'Nodes'),
                    ('authentication', 'Authentication'),
                    ('audit', 'Audit'),
                ],
                default='system',
                max_length=50,
                help_text='Rule category',
                db_index=True
            ),
        ),
        migrations.AddField(
            model_name='alertrule',
            name='template_name',
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text='Preset template name if this rule was created from a template'
            ),
        ),
        migrations.AddField(
            model_name='alertrule',
            name='conditions',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Structured alert conditions: {logic: "AND", groups: [...]}'
            ),
        ),
        migrations.AddField(
            model_name='alertrule',
            name='trigger_count',
            field=models.IntegerField(
                default=0,
                help_text='Total number of times this rule has triggered'
            ),
        ),
        migrations.AddField(
            model_name='alertrule',
            name='trigger_history',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Recent trigger history: [{triggered_at, resolved_at}, ...]'
            ),
        ),
        # Update condition field to be blank
        migrations.AlterField(
            model_name='alertrule',
            name='condition',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Legacy alert conditions (JSON format) - use conditions for new rules'
            ),
        ),
        # Update threshold fields to be nullable
        migrations.AlterField(
            model_name='alertrule',
            name='threshold_value',
            field=models.FloatField(
                blank=True,
                help_text='Threshold value (legacy, use conditions for new rules)',
                null=True
            ),
        ),
        # Update AlertChannel model
        migrations.AlterField(
            model_name='alertchannel',
            name='channel_type',
            field=models.CharField(
                choices=[
                    ('email', 'Email'),
                    ('webhook', 'Webhook'),
                    ('slack', 'Slack'),
                    ('dingtalk', 'DingTalk'),
                    ('sms', 'SMS'),
                    ('pagerduty', 'PagerDuty'),
                    ('lark', 'Lark/Feishu'),
                ],
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='alertchannel',
            name='retry_policy',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Retry policy configuration: {enabled, max_retries, retry_interval, retry_strategy, max_retry_time}'
            ),
        ),
        migrations.AddField(
            model_name='alertchannel',
            name='rate_limiting',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Rate limiting configuration: {enabled, type, max_messages, overflow_policy}'
            ),
        ),
        migrations.AddField(
            model_name='alertchannel',
            name='content_template',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Content template for notifications: {subject, body}'
            ),
        ),
        migrations.AddField(
            model_name='alertchannel',
            name='health_metrics',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Channel health metrics: {total_sent, total_success, total_failed, success_rate, avg_response_time, last_sent_at}'
            ),
        ),
        # Create AlertChannelHistory model
        migrations.CreateModel(
            name='AlertChannelHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('success', 'Success'),
                        ('failed', 'Failed'),
                        ('retrying', 'Retrying'),
                        ('dropped', 'Dropped'),
                        ('aggregated', 'Aggregated'),
                    ],
                    default='pending',
                    max_length=20,
                    db_index=True,
                    help_text='Delivery status'
                )),
                ('attempt', models.IntegerField(default=1, help_text='Retry attempt number')),
                ('request_payload', models.JSONField(blank=True, default=dict, help_text='Request payload sent to the channel')),
                ('response_status', models.IntegerField(blank=True, null=True, help_text='HTTP response status code')),
                ('response_body', models.TextField(blank=True, help_text='HTTP response body')),
                ('error_message', models.TextField(blank=True, help_text='Error message if delivery failed')),
                ('duration_ms', models.IntegerField(blank=True, null=True, help_text='Request duration in milliseconds')),
                ('sent_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True, help_text='When the notification was sent')),
                ('alert', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.CASCADE,
                    related_name='channel_history',
                    to='alerts.alert',
                    help_text='The alert that triggered this notification'
                )),
                ('channel', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='history',
                    to='alerts.alertchannel',
                    help_text='The notification channel'
                )),
            ],
            options={
                'verbose_name': 'Alert Channel History',
                'verbose_name_plural': 'Alert Channel History',
                'db_table': 'alerts_channel_history',
                'ordering': ['-sent_at'],
                'indexes': [
                    models.Index(fields=['channel', 'sent_at'], name='alerts_c_channel__sent_at_idx'),
                    models.Index(fields=['status', 'sent_at'], name='alerts_c_status__sent_at_idx'),
                ],
            },
        ),
    ]