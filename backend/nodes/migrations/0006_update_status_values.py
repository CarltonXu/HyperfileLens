# Generated data migration to update proxy status from active/inactive to online/offline

from django.db import migrations


def update_status_values(apps, schema_editor):
    """Update status values from active/inactive to online/offline."""
    ProxyNode = apps.get_model('nodes', 'ProxyNode')
    
    # Update 'active' -> 'online'
    updated_online = ProxyNode.objects.filter(status='active').update(status='online')
    
    # Update 'inactive' -> 'offline'
    updated_offline = ProxyNode.objects.filter(status='inactive').update(status='offline')
    
    print(f"Updated {updated_online} proxies from 'active' to 'online'")
    print(f"Updated {updated_offline} proxies from 'inactive' to 'offline'")


def reverse_status_values(apps, schema_editor):
    """Reverse migration: online/offline -> active/inactive."""
    ProxyNode = apps.get_model('nodes', 'ProxyNode')
    
    # Reverse 'online' -> 'active'
    updated_active = ProxyNode.objects.filter(status='online').update(status='active')
    
    # Reverse 'offline' -> 'inactive'
    updated_inactive = ProxyNode.objects.filter(status='offline').update(status='inactive')
    
    print(f"Reverted {updated_active} proxies from 'online' to 'active'")
    print(f"Reverted {updated_inactive} proxies from 'offline' to 'inactive'")


class Migration(migrations.Migration):
    dependencies = [
        ('nodes', '0005_alter_proxytask_task_type'),
    ]

    operations = [
        migrations.RunPython(update_status_values, reverse_status_values),
    ]
