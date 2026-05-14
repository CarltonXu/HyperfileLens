from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0006_repository_quota_fields_update"),
    ]

    operations = [
        migrations.AddField(
            model_name="repository",
            name="kopia_password",
            field=models.TextField(
                blank=True,
                help_text="Encrypted Kopia repository password for non-interactive operations",
            ),
        ),
    ]
