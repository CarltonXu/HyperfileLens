"""
Periodic Task Registry for HyperFileLens

This module provides utilities for registering periodic tasks
with django_celery_beat. It ensures that existing periodic
task entries are never overwritten, only new entries are created.

The register_periodic_tasks() function in each app's periodic_tasks
module should use core.periodic_registry to declare cron entries.
"""

from typing import Callable, Dict, Any, List
from celery import Celery
from celery.schedules import crontab
from django.conf import settings


class PeriodicRegistry:
    """
    Registry for managing periodic tasks with django_celery_beat.

    This registry ensures idempotent registration of periodic tasks,
    only creating missing entries and never overwriting existing ones.
    """

    def __init__(self):
        self._tasks: List[Dict[str, Any]] = []

    def add_task(
        self,
        name: str,
        task_name: str,
        crontab_args: Dict[str, Any],
        enabled: bool = True,
        description: str = '',
        kwargs: Dict[str, Any] = None,
    ) -> None:
        """
        Add a periodic task to the registry.

        Args:
            name: Unique name for the periodic task entry
            task_name: Full path to the Celery task (e.g., 'module.tasks.task_function')
            crontab_args: Arguments for crontab (minute, hour, day_of_week, day_of_month, month_of_year)
            enabled: Whether the task should be enabled by default
            description: Human-readable description of the task
            kwargs: Additional keyword arguments to pass to the task
        """
        self._tasks.append({
            'name': name,
            'task': task_name,
            'crontab': crontab_args,
            'enabled': enabled,
            'description': description,
            'kwargs': kwargs or {},
        })

    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all registered periodic tasks.

        Returns:
            List of task configuration dictionaries
        """
        return self._tasks.copy()


# Global registry instance
_registry = PeriodicRegistry()


def get_registry() -> PeriodicRegistry:
    """
    Get the global periodic task registry instance.

    Returns:
        The global PeriodicRegistry instance
    """
    return _registry


def register_periodic_task(
    name: str,
    task_name: str,
    crontab_args: Dict[str, Any],
    enabled: bool = True,
    description: str = '',
    kwargs: Dict[str, Any] = None,
) -> None:
    """
    Register a periodic task with the global registry.

    This is a convenience function that delegates to the global registry.

    Args:
        name: Unique name for the periodic task entry
        task_name: Full path to the Celery task
        crontab_args: Arguments for crontab
        enabled: Whether the task should be enabled by default
        description: Human-readable description of the task
        kwargs: Additional keyword arguments to pass to the task
    """
    _registry.add_task(
        name=name,
        task_name=task_name,
        crontab_args=crontab_args,
        enabled=enabled,
        description=description,
        kwargs=kwargs,
    )


def register_daily_task(
    name: str,
    task_name: str,
    hour: int = 0,
    minute: int = 0,
    enabled: bool = True,
    description: str = '',
    kwargs: Dict[str, Any] = None,
) -> None:
    """
    Register a daily periodic task.

    Convenience function for registering tasks that run once per day.

    Args:
        name: Unique name for the periodic task entry
        task_name: Full path to the Celery task
        hour: Hour of day (0-23)
        minute: Minute of hour (0-59)
        enabled: Whether the task should be enabled by default
        description: Human-readable description of the task
        kwargs: Additional keyword arguments to pass to the task
    """
    register_periodic_task(
        name=name,
        task_name=task_name,
        crontab_args={
            'minute': str(minute),
            'hour': str(hour),
            'day_of_week': '*',
            'day_of_month': '*',
            'month_of_year': '*',
        },
        enabled=enabled,
        description=description,
        kwargs=kwargs,
    )


def register_hourly_task(
    name: str,
    task_name: str,
    minute: int = 0,
    enabled: bool = True,
    description: str = '',
    kwargs: Dict[str, Any] = None,
) -> None:
    """
    Register an hourly periodic task.

    Convenience function for registering tasks that run once per hour.

    Args:
        name: Unique name for the periodic task entry
        task_name: Full path to the Celery task
        minute: Minute of hour when task should run (0-59)
        enabled: Whether the task should be enabled by default
        description: Human-readable description of the task
        kwargs: Additional keyword arguments to pass to the task
    """
    register_periodic_task(
        name=name,
        task_name=task_name,
        crontab_args={
            'minute': str(minute),
            'hour': '*',
            'day_of_week': '*',
            'day_of_month': '*',
            'month_of_year': '*',
        },
        enabled=enabled,
        description=description,
        kwargs=kwargs,
    )
