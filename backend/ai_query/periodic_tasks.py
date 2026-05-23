"""
HyperFileLens Backend - AI Query Periodic Tasks

This module defines periodic tasks for AI query management.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_queries():
    """
    Clean up old AI query records.
    
    This periodic task runs daily to remove AI query
    records that are older than the retention period.
    """
    from ai_query.models import AIQuery
    from django.utils import timezone
    from datetime import timedelta
    
    # Keep queries for 90 days
    cutoff = timezone.now() - timedelta(days=90)
    
    # Delete old queries
    deleted_count, _ = AIQuery.objects.filter(
        created_at__lt=cutoff
    ).delete()
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old AI query records")
    
    return {'deleted': deleted_count}


@shared_task
def process_pending_queries():
    """
    Process any pending AI queries that may have failed.
    
    This is a safety net for queries that didn't get processed.
    """
    from ai_query.models import AIQuery
    from ai_query.services import dispatch_ai_query
    
    # Find pending queries that have been pending for more than 5 minutes
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(minutes=5)
    
    pending_queries = AIQuery.objects.filter(
        status='pending',
        created_at__lt=cutoff
    )
    
    count = 0
    for query in pending_queries:
        try:
            dispatch_ai_query(query)
            count += 1
        except Exception as exc:
            query.mark_failed(str(exc))
    
    if count > 0:
        logger.warning(f"Re-queued {count} stale pending queries")
    
    return {'requeued': count}
