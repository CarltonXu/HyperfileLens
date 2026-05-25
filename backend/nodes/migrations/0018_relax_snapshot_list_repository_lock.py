from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0017_repository_proxy_task_lock'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='proxytask',
            name='unique_active_repository_source_task',
        ),
        migrations.AddConstraint(
            model_name='proxytask',
            constraint=models.UniqueConstraint(
                condition=(
                    models.Q(('repository_id__isnull', False))
                    & models.Q(('source_resource_id__isnull', False))
                    & models.Q(('status__in', ['pending', 'dispatched', 'accepted', 'running']))
                    & models.Q(('task_type__in', ['backup']))
                ),
                fields=('repository_id', 'source_resource_id'),
                name='unique_active_repository_source_task',
            ),
        ),
    ]
