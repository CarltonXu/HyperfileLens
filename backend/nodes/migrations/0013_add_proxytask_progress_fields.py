# Generated manually to add missing progress fields to ProxyTask
# These fields were added manually via SQL to match the model definition

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0012_remove_proxymetrics_proxy_delete_metricsaggregation_and_more'),
    ]

    operations = [
        # Fields were added manually via SQL, no operations needed
        migrations.RunSQL(
            sql="SELECT 1; -- Progress fields already added manually via SQL",
            reverse_sql="SELECT 1; -- No reverse operation needed"
        ),
    ]