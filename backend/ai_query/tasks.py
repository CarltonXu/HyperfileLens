"""
HyperFileLens Backend - AI Query Celery Tasks

This module defines asynchronous tasks for AI-powered query processing.
"""

import logging
from celery import shared_task
from django.conf import settings

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
    from backup_tasks.models import BackupSnapshot, BackupFile
    
    try:
        query = AIQuery.objects.get(id=query_id)
    except AIQuery.DoesNotExist:
        logger.error(f"AI Query {query_id} not found")
        return {'status': 'error', 'message': 'Query not found'}
    
    logger.info(f"Starting AI query: {query.query_text[:100]}")
    query.mark_processing()
    
    try:
        # Step 1: Get relevant backup data
        files = _get_relevant_files(query)
        
        # Step 2: Process files with AI
        result = _process_with_ai(query, files)
        
        # Step 3: Return results
        query.mark_completed(
            result=result,
            model_used='gpt-4',  # In production, get from settings
            tokens_used=result.get('tokens_used', 0)
        )
        
        logger.info(f"AI query {query_id} completed successfully")
        return {
            'status': 'success',
            'query_id': str(query_id),
            'results_count': len(result.get('results', []))
        }
        
    except Exception as e:
        error_message = str(e)
        logger.exception(f"AI query {query_id} failed: {error_message}")
        query.mark_failed(error_message)
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'status': 'error', 'message': error_message}


def _get_relevant_files(query):
    """
    Get files relevant to the query from backups.
    
    Args:
        query: AIQuery instance
    
    Returns:
        List of relevant files
    """
    from backup_tasks.models import BackupSnapshot, BackupFile
    
    files = []
    
    # Get snapshots to search
    snapshots = BackupSnapshot.objects.all()
    
    if query.target_paths:
        snapshots = snapshots.filter(
            task__source_node__paths__overlap=query.target_paths
        )
    
    # Get files from snapshots
    file_query = BackupFile.objects.filter(snapshot__in=snapshots)
    
    # Filter by file types if specified
    if query.file_types:
        file_query = file_query.filter(
            mime_type__in=query.file_types
        )
    
    # Limit to prevent memory issues
    files = list(file_query[:1000])
    
    return files


def _process_with_ai(query, files):
    """
    Process files with AI model.
    
    This is a placeholder that simulates AI processing.
    In production, this would:
    1. Extract text from files (OCR, document parsing)
    2. Send to AI model
    3. Process and format results
    
    Args:
        query: AIQuery instance
        files: List of files to process
    
    Returns:
        AI processing results
    """
    # Placeholder implementation
    results = []
    
    for file in files[:10]:  # Limit results
        results.append({
            'path': file.relative_path,
            'name': file.file_name,
            'size': file.size,
            'relevance': 0.95,
            'preview': f'Sample preview for {file.file_name}'
        })
    
    return {
        'results': results,
        'summary': f'Found {len(results)} relevant files for your query.',
        'suggestions': [
            'Try a more specific search term',
            'Filter by file type',
            'Search in a specific backup snapshot'
        ],
        'tokens_used': len(query.query_text) // 4
    }
