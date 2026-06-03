from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system_settings", "0002_delete_systemsetting"),
    ]

    operations = [
        migrations.AlterField(
            model_name="smtpconfig",
            name="from_name",
            field=models.CharField(
                blank=True,
                default="HyperFileLens",
                help_text="Default email subject",
                max_length=100,
            ),
        ),
    ]
