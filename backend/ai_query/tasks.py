"""
HyperFileLens Backend - AI Query Celery Tasks

This module defines asynchronous tasks for AI-powered query processing.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_ai_query(self, query_id: str):
    """
    Execute an AI query asynchronously.
    
    This task:
    1. Retrieves the query from database
    2. Extracts relevant files from backups
    3. Processes files through AI model
    4. Returns results
    
    Args:
        query_id: UUID of the AIQuery to execute
    """
    from .models import AIQuery
    from .services import dispatch_ai_query
    
    try:
        query = AIQuery.objects.get(id=query_id)
    except AIQuery.DoesNotExist:
        logger.error(f"AI Query {query_id} not found")
        return {'status': 'error', 'message': 'Query not found'}
    
    try:
        dispatch_ai_query(query)
        logger.info(f"AI query {query_id} dispatched to Gateway")
        return {'status': 'dispatched', 'query_id': str(query_id)}
    except Exception as e:
        error_message = str(e)
        logger.exception(f"AI query {query_id} failed: {error_message}")
        query.mark_failed(error_message)
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'status': 'error', 'message': error_message}


@shared_task
def cleanup_old_queries():
    from datetime import timedelta

    from django.utils import timezone

    from .models import AIQuery

    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = AIQuery.objects.filter(created_at__lt=cutoff).delete()
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old AI query records")
    return {'deleted': deleted_count}
