"""
HyperFileLens Backend - Periodic Tasks Registry

This module registers all periodic (cron-like) tasks for the Celery Beat scheduler.
Each app that needs periodic tasks should define a register_periodic_tasks() function here.
"""

import logging

logger = logging.getLogger(__name__)


def register_periodic_tasks(registry):
    """
    Register all periodic tasks from various apps.
    
    Args:
        registry: The periodic registry instance from core.periodic_registry
    """
    logger.info("Registering periodic tasks...")
    
    # Import tasks from apps
    try:
        from backup_tasks.tasks import cleanup_old_snapshots
        from nodes.tasks import check_node_heartbeat
        from repository.tasks import sync_repository_stats
        from ai_query.tasks import cleanup_old_queries
    except ImportError as e:
        logger.warning(f"Some periodic task modules could not be imported: {e}")
    
    # Register backup task cleanup
    # Runs daily at midnight
    registry.register_cron_task(
        name='cleanup-old-snapshots',
        task='backup_tasks.tasks.cleanup_old_snapshots',
        schedule={'type': 'crontab', 'minute': 0, 'hour': 0},
    )
    
    # Register node heartbeat check
    # Runs every 5 minutes
    registry.register_cron_task(
        name='check-node-heartbeat',
        task='nodes.tasks.check_node_heartbeat',
        schedule={'type': 'crontab', 'minute': '*/5'},
    )
    
    # Register repository stats sync
    # Runs every hour
    registry.register_cron_task(
        name='sync-repository-stats',
        task='repository.tasks.sync_repository_stats',
        schedule={'type': 'crontab', 'minute': 0},
    )
    
    # Register AI query cleanup
    # Runs daily at 3 AM
    registry.register_cron_task(
        name='cleanup-old-ai-queries',
        task='ai_query.tasks.cleanup_old_queries',
        schedule={'type': 'crontab', 'minute': 0, 'hour': 3},
    )
    
    # Register scheduled backup tasks based on policies
    # This is handled dynamically in backup_tasks.tasks.schedule_backup_tasks
    
    logger.info("Periodic tasks registered successfully")
