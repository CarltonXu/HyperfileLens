from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licenses', '0003_add_changed_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='license',
            name='license_token',
            field=models.TextField(blank=True, default='', help_text='Original signed license token. This is the source of truth for licensed limits.'),
        ),
        migrations.AddField(
            model_name='license',
            name='verified_payload',
            field=models.JSONField(blank=True, default=dict, help_text='Last successfully verified license payload cache'),
        ),
        migrations.AddField(
            model_name='license',
            name='payload_hash',
            field=models.CharField(blank=True, default='', help_text='SHA256 hash of the last verified license payload', max_length=64),
        ),
        migrations.AddField(
            model_name='license',
            name='last_verified_at',
            field=models.DateTimeField(blank=True, help_text='When the license token was last verified', null=True),
        ),
        migrations.AddField(
            model_name='license',
            name='verification_status',
            field=models.CharField(default='unverified', help_text='Latest token verification status', max_length=32),
        ),
        migrations.AddField(
            model_name='license',
            name='verification_message',
            field=models.TextField(blank=True, default='', help_text='Latest token verification message'),
        ),
        migrations.AddField(
            model_name='license',
            name='highest_seen_version',
            field=models.PositiveIntegerField(default=0, help_text='Highest signed license version seen by this installation'),
        ),
    ]
