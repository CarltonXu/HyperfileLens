from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recovery_tasks', '0007_recoveryexport_progress_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='recoveryexport',
            name='download_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='last_downloaded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='share_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='share_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='share_password_hash',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='share_token',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
    ]
