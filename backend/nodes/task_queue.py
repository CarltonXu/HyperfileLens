"""
Task queue implementation for HyperFileLens.

This module provides a priority-based task queue system for managing
backup, restore, and other operations with proper scheduling.
"""

import heapq
import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from channels.layers import get_channel_layer

from .models import ProxyNode, ProxyTask

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    URGENT = 0      # 最紧急
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级


class TaskStatus(Enum):
    """Task status in queue."""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
    TIMEOUT = "timeout"       # 超时


class QueuedTask:
    """Task in the queue with priority."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        priority: TaskPriority,
        payload: Dict[str, Any],
        callback: Callable = None,
        timeout: int = 3600,
        retries: int = 3,
        retry_delay: int = 60,
        depends_on: List[str] = None
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.priority = priority
        self.payload = payload
        self.callback = callback
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        self.depends_on = depends_on or []
        
        self.status = TaskStatus.PENDING
        self.created_at = timezone.now()
        self.started_at = None
        self.completed_at = None
        self.error = None
        
        # For priority queue
        self._heap_priority = (self.priority.value, self.created_at.timestamp())

    def __lt__(self, other):
        """Compare tasks for priority queue."""
        return self._heap_priority < other._heap_priority

    def can_execute(self, completed_tasks: set) -> bool:
        """Check if task can be executed (dependencies met)."""
        return all(dep in completed_tasks for dep in self.depends_on)

    def mark_started(self):
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = timezone.now()

    def mark_completed(self):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = timezone.now()

    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = timezone.now()
        self.error = error

    def mark_cancelled(self):
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = timezone.now()

    def mark_timeout(self):
        """Mark task as timeout."""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = timezone.now()
        self.error = f"Task timeout after {self.timeout} seconds"

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.retry_count < self.retries

    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1

    def get_duration(self) -> float:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0


class TaskQueue:
    """
    Priority-based task queue.

    Manages tasks with different priorities and dependencies,
    ensuring proper execution order.
    """

    def __init__(self, max_concurrent_tasks: int = 5, check_interval: int = 1):
        """
        Initialize task queue.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            check_interval: Interval to check for new tasks (seconds)
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.check_interval = check_interval

        # Priority queue (min-heap)
        self._queue = []
        self._queue_lock = threading.Lock()

        # Running tasks
        self._running_tasks: Dict[str, QueuedTask] = {}
        self._running_lock = threading.Lock()

        # Completed tasks (for dependency checking)
        self._completed_tasks: set = set()
        self._completed_lock = threading.Lock()

        # Task lookup by ID
        self._tasks: Dict[str, QueuedTask] = {}
        self._tasks_lock = threading.Lock()

        # Control
        self._running = False
        self._worker_thread = None

        # Callbacks
        self._task_callbacks = {
            'started': [],
            'completed': [],
            'failed': [],
            'cancelled': [],
            'timeout': [],
        }

    def add_task(
        self,
        task_id: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        payload: Dict[str, Any] = None,
        callback: Callable = None,
        timeout: int = 3600,
        retries: int = 3,
        retry_delay: int = 60,
        depends_on: List[str] = None
    ) -> QueuedTask:
        """
        Add a task to the queue.

        Args:
            task_id: Task ID
            task_type: Task type (backup, restore, etc.)
            priority: Task priority
            payload: Task payload
            callback: Callback function
            timeout: Task timeout in seconds
            retries: Maximum retry count
            retry_delay: Delay between retries (seconds)
            depends_on: List of task IDs this task depends on

        Returns:
            QueuedTask instance
        """
        task = QueuedTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            payload=payload or {},
            callback=callback,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            depends_on=depends_on
        )

        with self._tasks_lock:
            self._tasks[task_id] = task

        with self._queue_lock:
            heapq.heappush(self._queue, task)

        logger.info(
            f"Task added to queue",
            extra={
                'task_id': task_id,
                'task_type': task_type,
                'priority': priority.name,
            }
        )

        return task

    def add_callback(self, event: str, callback: Callable):
        """
        Add a callback for task events.

        Args:
            event: Event name (started, completed, failed, cancelled, timeout)
            callback: Callback function (takes task as argument)
        """
        if event in self._task_callbacks:
            self._task_callbacks[event].append(callback)

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the queue.

        Args:
            task_id: Task ID

        Returns:
            True if task was removed, False otherwise
        """
        with self._tasks_lock:
            if task_id in self._tasks:
                task = self._tasks.pop(task_id)
                
                # If task is in queue, remove it
                with self._queue_lock:
                    # Rebuild queue without the task
                    new_queue = []
                    for t in self._queue:
                        if t.task_id != task_id:
                            new_queue.append(t)
                    heapq.heapify(new_queue)
                    self._queue = new_queue

                logger.info(f"Task removed from queue: {task_id}")
                return True

        return False

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled, False otherwise
        """
        with self._tasks_lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                
                if task.status == TaskStatus.RUNNING:
                    # Cannot cancel running task through queue
                    logger.warning(f"Cannot cancel running task: {task_id}")
                    return False
                
                if task.status in [TaskStatus.PENDING, TaskStatus.FAILED]:
                    task.mark_cancelled()
                    self._trigger_callback('cancelled', task)
                    self.remove_task(task_id)
                    logger.info(f"Task cancelled: {task_id}")
                    return True

        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task status dict or None
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            return {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'priority': task.priority.name,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'retry_count': task.retry_count,
                'error': task.error,
                'duration': task.get_duration(),
            }

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._queue_lock, self._running_lock, self._tasks_lock, self._completed_lock:
            return {
                'queued_tasks': len(self._queue),
                'running_tasks': len(self._running_tasks),
                'completed_tasks': len(self._completed_tasks),
                'total_tasks': len(self._tasks),
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'running': self._running,
            }

    def start(self):
        """Start the task queue worker."""
        if self._running:
            logger.warning("Task queue already running")
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Task queue started")

    def stop(self):
        """Stop the task queue worker."""
        if not self._running:
            return

        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("Task queue stopped")

    def _worker_loop(self):
        """Worker loop for processing tasks."""
        logger.info("Task queue worker started")

        while self._running:
            try:
                self._process_queue()
            except Exception as e:
                logger.exception(f"Error processing queue: {e}")
            
            time.sleep(self.check_interval)

        logger.info("Task queue worker stopped")

    def _process_queue(self):
        """Process tasks from the queue."""
        with self._running_lock:
            # Check if we can start more tasks
            with self._running_lock:
                if len(self._running_tasks) >= self.max_concurrent_tasks:
                    return

            # Get next task
            with self._queue_lock, self._completed_lock:
                if not self._queue:
                    return

                # Find next task that can be executed
                task = None
                temp_queue = []
                
                while self._queue:
                    candidate = heapq.heappop(self._queue)
                    
                    if candidate.can_execute(self._completed_tasks):
                        task = candidate
                        break
                    else:
                        # Put back in queue
                        temp_queue.append(candidate)
                
                # Put back tasks that couldn't be executed
                for t in temp_queue:
                    heapq.heappush(self._queue, t)

                if not task:
                    return

                # Start task
                self._start_task(task)

    def _start_task(self, task: QueuedTask):
        """Start executing a task."""
        task.mark_started()

        with self._running_lock:
            self._running_tasks[task.task_id] = task

        # Update database
        self._update_task_status(task.task_id, TaskStatus.RUNNING)

        # Trigger callback
        self._trigger_callback('started', task)

        # Execute task in separate thread
        thread = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
        thread.start()

        # Start timeout checker
        timeout_thread = threading.Thread(
            target=self._check_task_timeout,
            args=(task,),
            daemon=True
        )
        timeout_thread.start()

    def _execute_task(self, task: QueuedTask):
        """Execute a task."""
        try:
            logger.info(
                f"Executing task",
                extra={
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'priority': task.priority.name,
                }
            )

            # Call callback if provided
            if task.callback:
                result = task.callback(task.payload)
                # Store result
                if result:
                    self._store_task_result(task.task_id, result)
            else:
                # Default task execution
                result = self._execute_default_task(task)
                if result:
                    self._store_task_result(task.task_id, result)

            # Mark as completed
            task.mark_completed()

            with self._completed_lock:
                self._completed_tasks.add(task.task_id)

            # Update database
            self._update_task_status(task.task_id, TaskStatus.COMPLETED)

            # Trigger callback
            self._trigger_callback('completed', task)

            logger.info(
                f"Task completed",
                extra={
                    'task_id': task.task_id,
                    'duration': task.get_duration(),
                }
            )

        except Exception as e:
            logger.exception(
                f"Task execution failed",
                extra={'task_id': task.task_id, 'error': str(e)}
            )

            task.mark_failed(str(e))

            # Check if we should retry
            if task.should_retry():
                task.increment_retry()
                
                logger.info(
                    f"Retrying task",
                    extra={
                        'task_id': task.task_id,
                        'retry_count': task.retry_count,
                        'max_retries': task.retries,
                    }
                )

                # Add back to queue after delay
                time.sleep(task.retry_delay)
                self.add_task(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    priority=task.priority,
                    payload=task.payload,
                    callback=task.callback,
                    timeout=task.timeout,
                    retries=task.retries,
                    retry_delay=task.retry_delay,
                    depends_on=task.depends_on
                )
            else:
                # Mark as failed permanently
                self._update_task_status(task.task_id, TaskStatus.FAILED)
                self._trigger_callback('failed', task)

        finally:
            # Remove from running tasks
            with self._running_lock:
                self._running_tasks.pop(task.task_id, None)

    def _check_task_timeout(self, task: QueuedTask):
        """Check if task has timed out."""
        while task.status == TaskStatus.RUNNING and self._running:
            time.sleep(min(10, task.timeout))

            if task.status == TaskStatus.RUNNING:
                elapsed = (timezone.now() - task.started_at).total_seconds()
                if elapsed >= task.timeout:
                    logger.warning(
                        f"Task timeout detected",
                        extra={'task_id': task.task_id, 'elapsed': elapsed}
                    )
                    
                    task.mark_timeout()
                    self._update_task_status(task.task_id, TaskStatus.TIMEOUT)
                    self._trigger_callback('timeout', task)
                    
                    with self._running_lock:
                        self._running_tasks.pop(task.task_id, None)
                    
                    break

    def _execute_default_task(self, task: QueuedTask) -> Dict[str, Any]:
        """Execute default task logic based on task type."""
        task_type = task.task_type.lower()

        if task_type == 'backup':
            return self._execute_backup(task)
        elif task_type == 'restore':
            return self._execute_restore(task)
        elif task_type == 'cleanup':
            return self._execute_cleanup(task)
        elif task_type == 'snapshot':
            return self._execute_snapshot(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {}

    def _execute_backup(self, task: QueuedTask) -> Dict[str, Any]:
        """Execute backup task."""
        from .proxy_service import ProxyService
        
        proxy_id = task.payload.get('proxy_id')
        source_path = task.payload.get('source_path')
        repository_id = task.payload.get('repository_id')
        
        # Implementation depends on ProxyService
        logger.info(f"Executing backup for proxy {proxy_id}")
        
        # Update progress
        self._update_task_progress(task.task_id, 10, "Initializing backup...")
        time.sleep(2)  # Simulate work
        
        self._update_task_progress(task.task_id, 50, "Backing up files...")
        time.sleep(2)
        
        self._update_task_progress(task.task_id, 90, "Finalizing backup...")
        time.sleep(2)
        
        return {
            'status': 'success',
            'snapshot_id': f"snap-{task.task_id}",
            'files_count': task.payload.get('expected_files', 0),
        }

    def _execute_restore(self, task: QueuedTask) -> Dict[str, Any]:
        """Execute restore task."""
        logger.info(f"Executing restore: {task.task_id}")
        # Implementation...
        return {'status': 'success'}

    def _execute_cleanup(self, task: QueuedTask) -> Dict[str, Any]:
        """Execute cleanup task."""
        logger.info(f"Executing cleanup: {task.task_id}")
        # Implementation...
        return {'status': 'success'}

    def _execute_snapshot(self, task: QueuedTask) -> Dict[str, Any]:
        """Execute snapshot task."""
        logger.info(f"Executing snapshot: {task.task_id}")
        # Implementation...
        return {'status': 'success'}

    def _update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status in database."""
        try:
            with transaction.atomic():
                proxy_task = ProxyTask.objects.get(id=task_id)
                proxy_task.status = status.value
                
                if status == TaskStatus.COMPLETED:
                    proxy_task.progress = 100
                    proxy_task.completed_at = timezone.now()
                elif status == TaskStatus.FAILED:
                    proxy_task.completed_at = timezone.now()
                elif status == TaskStatus.TIMEOUT:
                    proxy_task.completed_at = timezone.now()
                    proxy_task.error = "Task timeout"
                
                proxy_task.save()
        except ProxyTask.DoesNotExist:
            logger.warning(f"Task not found in database: {task_id}")

    def _update_task_progress(self, task_id: str, progress: int, message: str):
        """Update task progress."""
        try:
            proxy_task = ProxyTask.objects.get(id=task_id)
            proxy_task.progress = progress
            proxy_task.message = message
            proxy_task.save()

            # Broadcast progress
            self._broadcast_task_progress(proxy_task)
        except ProxyTask.DoesNotExist:
            pass

    def _store_task_result(self, task_id: str, result: Dict[str, Any]):
        """Store task result."""
        try:
            proxy_task = ProxyTask.objects.get(id=task_id)
            proxy_task.result = result
            proxy_task.save()
        except ProxyTask.DoesNotExist:
            pass

    def _trigger_callback(self, event: str, task: QueuedTask):
        """Trigger callbacks for an event."""
        for callback in self._task_callbacks.get(event, []):
            try:
                callback(task)
            except Exception as e:
                logger.exception(f"Error in callback: {e}")

    def _broadcast_task_progress(self, task: ProxyTask):
        """Broadcast task progress via WebSocket."""
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        try:
            channel_layer.group_send(
                f'proxy_{task.proxy.id}',
                {
                    'type': 'task.progress',
                    'data': {
                        'task_id': str(task.id),
                        'task_type': task.task_type,
                        'progress': task.progress,
                        'message': task.message,
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to broadcast task progress: {e}")

    def clear_completed_tasks(self, days: int = 7):
        """
        Clear completed tasks from memory.

        Args:
            days: Keep tasks completed within the last N days
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        with self._tasks_lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task.completed_at and task.completed_at < cutoff:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
            
            with self._completed_lock:
                self._completed_tasks = {
                    tid for tid in self._completed_tasks 
                    if tid in self._tasks
                }
        
        logger.info(f"Cleared {len(to_remove)} completed tasks from memory")


# Global task queue instance
task_queue = TaskQueue(max_concurrent_tasks=5)


def get_task_queue() -> TaskQueue:
    """Get the global task queue instance."""
    return task_queue
