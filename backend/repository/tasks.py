"""
HyperFileLens Backend - Repository Celery Tasks
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sync_repository_stats():
    """
    Synchronize repository statistics with actual storage.
    
    This periodic task runs hourly to update used_space
    and other statistics for all repositories.
    """
    from repository.models import Repository
    
    repositories = Repository.objects.filter(status='active')
    
    for repo in repositories:
        try:
            repo.sync_space_usage()
            logger.info(f"Synced stats for repository: {repo.name}")
        except Exception as e:
            logger.error(f"Failed to sync stats for repository {repo.name}: {e}")
    
    return {'synced': repositories.count()}


@shared_task
def cleanup_repository_cache():
    """
    Clean up temporary files and cache in repositories.
    
    This task removes old temporary files and clears
    any cached data that is no longer needed.
    """
    # Implementation depends on storage backend
    pass
