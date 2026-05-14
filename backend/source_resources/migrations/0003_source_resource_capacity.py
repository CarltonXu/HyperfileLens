from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("source_resources", "0002_add_tenant_to_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourceresource",
            name="used_size",
            field=models.BigIntegerField(
                default=0,
                help_text="Used size of the source in bytes",
            ),
        ),
        migrations.AddField(
            model_name="sourceresource",
            name="free_size",
            field=models.BigIntegerField(
                default=0,
                help_text="Free size of the source in bytes",
            ),
        ),
    ]
