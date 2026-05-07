"""
Celery Tasks for Nodes Application

This module defines background tasks for node management,
including health checks and status monitoring.
"""

from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_all_nodes_health(self):
    """
    Periodic task to check health of all registered nodes.

    Updates node status based on last heartbeat time.
    Nodes that haven't sent a heartbeat in 3x their interval
    are marked as inactive.
    """
    from .models import Node

    try:
        now = timezone.now()
        nodes = Node.objects.filter(
            status__in=[Node.NodeStatus.ONLINE, Node.NodeStatus.PENDING]
        )

        inactive_count = 0
        for node in nodes:
            if not node.last_heartbeat:
                if (now - node.created_at).total_seconds() > 300:  # 5 minutes
                    node.status = Node.NodeStatus.INACTIVE
                    node.save(update_fields=['status', 'updated_at'])
                    inactive_count += 1
            else:
                elapsed = (now - node.last_heartbeat).total_seconds()
                threshold = node.heartbeat_interval * 3
                if elapsed > threshold:
                    node.status = Node.NodeStatus.INACTIVE
                    node.save(update_fields=['status', 'updated_at'])
                    inactive_count += 1

        logger.info(f'Node health check completed. Inactive nodes: {inactive_count}')
        return {'inactive_nodes': inactive_count}

    except Exception as exc:
        logger.error(f'Error during node health check: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def check_single_node_health(self, node_id):
    """
    Check health of a specific node.

    Args:
        node_id: UUID of the node to check
    """
    from .models import Node
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_async

    try:
        node = Node.objects.get(node_id=node_id)
        is_online = node.is_online()

        # Broadcast status update via WebSocket
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_async(channel_layer.group_send)(
                'system_status',
                {
                    'type': 'status_update',
                    'data': {
                        'type': 'node_status',
                        'node_id': str(node_id),
                        'is_online': is_online,
                        'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

        return {'node_id': str(node_id), 'is_online': is_online}

    except Node.DoesNotExist:
        logger.warning(f'Node not found: {node_id}')
        return {'error': 'Node not found'}

    except Exception as exc:
        logger.error(f'Error checking node {node_id}: {exc}')
        raise self.retry(exc=exc, countdown=30)


@shared_task
def cleanup_old_heartbeats(days=30):
    """
    Clean up old heartbeat records.

    Args:
        days: Number of days to retain heartbeat records
    """
    from .models import NodeHeartbeat

    try:
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted_count = NodeHeartbeat.objects.filter(
            timestamp__lt=cutoff
        ).delete()[0]

        logger.info(f'Cleaned up {deleted_count} old heartbeat records')
        return {'deleted_records': deleted_count}

    except Exception as exc:
        logger.error(f'Error cleaning up heartbeats: {exc}')
        return {'error': str(exc)}


@shared_task
def cleanup_old_connections(days=7):
    """
    Clean up old connection records.

    Args:
        days: Number of days to retain connection records
    """
    from .models import NodeConnection

    try:
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted_count = NodeConnection.objects.filter(
            connected_at__lt=cutoff
        ).delete()[0]

        logger.info(f'Cleaned up {deleted_count} old connection records')
        return {'deleted_records': deleted_count}

    except Exception as exc:
        logger.error(f'Error cleaning up connections: {exc}')
        return {'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def send_command_to_node(self, node_id, command, params=None):
    """
    Send a command to a node via WebSocket.

    Args:
        node_id: UUID of the target node
        command: Command to send
        params: Optional command parameters
    """
    from .models import Node
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_async
    import json

    try:
        node = Node.objects.get(node_id=node_id)

        if not node.is_online():
            return {'error': 'Node is offline'}

        channel_layer = get_channel_layer()
        if channel_layer:
            await async_to_async(channel_layer.group_send)(
                f'node_{node_id}',
                {
                    'type': 'command_message',
                    'data': {
                        'type': 'command',
                        'command': command,
                        'params': params or {},
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

            logger.info(f'Command sent to node {node_id}: {command}')
            return {'success': True, 'node_id': str(node_id), 'command': command}

        return {'error': 'Channel layer not available'}

    except Node.DoesNotExist:
        return {'error': 'Node not found'}

    except Exception as exc:
        logger.error(f'Error sending command to node {node_id}: {exc}')
        raise self.retry(exc=exc, countdown=30)


@shared_task
def notify_node_status_change(node_id, old_status, new_status):
    """
    Send notification when node status changes.

    Args:
        node_id: UUID of the node
        old_status: Previous status
        new_status: New status
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_async
    from audit_log.models import AuditLog
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        node = Node.objects.get(node_id=node_id)

        # Log the status change
        AuditLog.objects.create(
            action='node_status_change',
            user=node.owner,
            resource_type='node',
            resource_id=str(node_id),
            details={
                'node_name': node.name,
                'old_status': old_status,
                'new_status': new_status
            }
        )

        # Broadcast via WebSocket
        channel_layer = get_channel_layer()
        if channel_layer:
            await async_to_async(channel_layer.group_send)(
                'system_status',
                {
                    'type': 'status_update',
                    'data': {
                        'type': 'node_status_change',
                        'node_id': str(node_id),
                        'node_name': node.name,
                        'old_status': old_status,
                        'new_status': new_status,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

        return {'success': True}

    except Exception as exc:
        logger.error(f'Error notifying status change: {exc}')
        return {'error': str(exc)}


# Import Node model at the end to avoid circular imports
from .models import Node
