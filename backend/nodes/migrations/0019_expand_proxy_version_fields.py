from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0018_relax_snapshot_list_repository_lock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proxynode',
            name='kopia_version',
            field=models.CharField(
                blank=True,
                help_text='Kopia version installed on proxy',
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name='proxynode',
            name='os_version',
            field=models.CharField(
                blank=True,
                help_text='OS version details',
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name='proxynode',
            name='version',
            field=models.CharField(
                blank=True,
                help_text='Proxy software version',
                max_length=255,
            ),
        ),
    ]
