from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recovery_tasks', '0006_recoveryexport'),
    ]

    operations = [
        migrations.AddField(
            model_name='recoveryexport',
            name='eta',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='recoveryexport',
            name='speed_mbps',
            field=models.FloatField(default=0.0),
        ),
    ]
