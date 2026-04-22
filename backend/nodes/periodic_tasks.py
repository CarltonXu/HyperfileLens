"""
HyperFileLens Backend - Nodes Periodic Tasks

This module defines periodic tasks for node management.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_node_heartbeat():
    """
    Check heartbeat status of all registered nodes.
    
    This periodic task runs every 5 minutes to identify
    nodes that have missed their heartbeat and mark them
    as offline.
    """
    from nodes.models import Node
    from django.utils import timezone
    from datetime import timedelta
    
    # Consider a node offline if no heartbeat for 15 minutes
    timeout = timezone.now() - timedelta(minutes=15)
    
    # Find nodes that should be marked offline
    offline_nodes = Node.objects.filter(
        status='online',
        last_heartbeat__lt=timeout
    )
    
    # Mark them offline
    count = offline_nodes.update(status='offline')
    
    if count > 0:
        logger.warning(f"Marked {count} nodes as offline due to heartbeat timeout")
    
    return {'checked': Node.objects.count(), 'marked_offline': count}


@shared_task
def cleanup_offline_nodes():
    """
    Clean up nodes that have been offline for too long.
    
    This task removes or archives nodes that have been
    offline for more than 30 days.
    """
    from nodes.models import Node
    from django.utils import timezone
    from datetime import timedelta
    
    # Consider a node for cleanup if offline for 30 days
    timeout = timezone.now() - timedelta(days=30)
    
    # Find nodes for cleanup
    nodes_to_cleanup = Node.objects.filter(
        status='offline',
        last_heartbeat__lt=timeout
    )
    
    count = nodes_to_cleanup.count()
    
    # Archive rather than delete (optional)
    # nodes_to_cleanup.update(status='archived')
    
    if count > 0:
        logger.info(f"Found {count} nodes for cleanup")
    
    return {'found': count}
