# Generated manually for Kopia-native backup policy configuration.

from django.db import migrations, models
import policies.models


class Migration(migrations.Migration):

    dependencies = [
        ('policies', '0002_add_tenant_to_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuppolicy',
            name='policy_scope',
            field=models.CharField(
                choices=[
                    ('global', 'Global Policy'),
                    ('host', 'Host Policy'),
                    ('user', 'User Policy'),
                    ('path', 'Path Policy'),
                ],
                default='path',
                help_text='Kopia policy target scope',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='policy_target',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Kopia policy target, e.g. {host,user,path}',
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='snapshot_schedule',
            field=models.JSONField(
                blank=True,
                default=policies.models.default_kopia_schedule_policy,
                help_text='Kopia snapshot scheduling policy',
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='retention_policy',
            field=models.JSONField(
                blank=True,
                default=policies.models.default_kopia_retention_policy,
                help_text='Kopia retention policy',
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='file_policy',
            field=models.JSONField(
                blank=True,
                default=policies.models.default_kopia_file_policy,
                help_text='Kopia file and ignore policy',
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='compression_policy',
            field=models.JSONField(
                blank=True,
                default=policies.models.default_kopia_compression_policy,
                help_text='Kopia compression and performance policy',
            ),
        ),
        migrations.AddField(
            model_name='backuppolicy',
            name='advanced_policy',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Advanced Kopia policy options',
            ),
        ),
    ]
