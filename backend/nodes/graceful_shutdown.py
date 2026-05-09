"""
Graceful shutdown functionality for HyperFileLens.

This module provides functionality for graceful shutdown of WebSocket
connections, tasks, and other resources to prevent data loss.
"""

import logging
import signal
import threading
import time
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from channels.layers import get_channel_layer

from .models import ProxyNode, ProxyTask
from .task_queue import get_task_queue

logger = logging.getLogger(__name__)


class GracefulShutdownManager:
    """
    Manager for graceful shutdown operations.

    Coordinates shutdown across multiple components:
    - WebSocket connections
    - Running tasks
    - Background services
    - Task queue
    """

    def __init__(self, shutdown_timeout: int = 30):
        """
        Initialize shutdown manager.

        Args:
            shutdown_timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_in_progress = False
        self.shutdown_requested_at = None

        # Components to shut down
        self._components: Dict[str, 'ShutdownComponent'] = {}

        # Callbacks
        self._pre_shutdown_callbacks: List[Callable] = []
        self._post_shutdown_callbacks: List[Callable] = []

        # Thread safety
        self._lock = threading.Lock()

    def register_component(
        self,
        name: str,
        component: 'ShutdownComponent'
    ):
        """
        Register a component for shutdown.

        Args:
            name: Component name
            component: Component instance with shutdown methods
        """
        with self._lock:
            self._components[name] = component
            logger.info(f"Registered shutdown component: {name}")

    def unregister_component(self, name: str):
        """
        Unregister a shutdown component.

        Args:
            name: Component name
        """
        with self._lock:
            if name in self._components:
                del self._components[name]
                logger.info(f"Unregistered shutdown component: {name}")

    def add_pre_shutdown_callback(self, callback: Callable):
        """
        Add a callback to run before shutdown.

        Args:
            callback: Callback function
        """
        self._pre_shutdown_callbacks.append(callback)

    def add_post_shutdown_callback(self, callback: Callable):
        """
        Add a callback to run after shutdown.

        Args:
            callback: Callback function
        """
        self._post_shutdown_callbacks.append(callback)

    def initiate_shutdown(self, reason: str = "manual"):
        """
        Initiate graceful shutdown.

        Args:
            reason: Reason for shutdown
        """
        with self._lock:
            if self.shutdown_in_progress:
                logger.warning("Shutdown already in progress")
                return

            self.shutdown_in_progress = True
            self.shutdown_requested_at = timezone.now()

        logger.info(
            f"Graceful shutdown initiated",
            extra={'reason': reason, 'timeout': self.shutdown_timeout}
        )

        # Run pre-shutdown callbacks
        self._run_pre_shutdown_callbacks()

        # Shutdown components
        self._shutdown_components()

        # Run post-shutdown callbacks
        self._run_post_shutdown_callbacks()

        logger.info("Graceful shutdown completed")

    def _run_pre_shutdown_callbacks(self):
        """Run all pre-shutdown callbacks."""
        logger.info("Running pre-shutdown callbacks")

        for callback in self._pre_shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.exception(f"Error in pre-shutdown callback: {e}")

    def _shutdown_components(self):
        """Shutdown all registered components."""
        logger.info("Shutting down components")

        components = list(self._components.items())
        shutdown_start = time.time()

        for name, component in components:
            try:
                logger.info(f"Shutting down component: {name}")
                
                if hasattr(component, 'graceful_shutdown'):
                    # Component has graceful shutdown method
                    component.graceful_shutdown(timeout=self.shutdown_timeout)
                elif hasattr(component, 'shutdown'):
                    # Component has shutdown method
                    component.shutdown()
                elif hasattr(component, 'stop'):
                    # Component has stop method
                    component.stop()
                elif hasattr(component, 'close'):
                    # Component has close method
                    component.close()
                else:
                    logger.warning(f"Component {name} has no shutdown method")

            except Exception as e:
                logger.exception(f"Error shutting down component {name}: {e}")

        shutdown_duration = time.time() - shutdown_start
        logger.info(f"Components shutdown in {shutdown_duration:.2f} seconds")

    def _run_post_shutdown_callbacks(self):
        """Run all post-shutdown callbacks."""
        logger.info("Running post-shutdown callbacks")

        for callback in self._post_shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.exception(f"Error in post-shutdown callback: {e}")

    def get_shutdown_status(self) -> Dict[str, Any]:
        """
        Get current shutdown status.

        Returns:
            Dictionary with shutdown status information
        """
        with self._lock:
            return {
                'shutdown_in_progress': self.shutdown_in_progress,
                'shutdown_requested_at': self.shutdown_requested_at.isoformat() if self.shutdown_requested_at else None,
                'components': list(self._components.keys()),
                'timeout': self.shutdown_timeout,
            }

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self.shutdown_in_progress

    def get_time_until_shutdown(self) -> Optional[float]:
        """
        Get time remaining until forced shutdown.

        Returns:
            Seconds remaining, or None if not shutting down
        """
        if not self.shutdown_in_progress or not self.shutdown_requested_at:
            return None

        elapsed = (timezone.now() - self.shutdown_requested_at).total_seconds()
        remaining = self.shutdown_timeout - elapsed
        return max(0, remaining)


class WebSocketConnectionManager:
    """
    Manager for WebSocket connections with graceful shutdown support.
    """

    def __init__(self):
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_connection(
        self,
        connection_id: str,
        proxy_id: str,
        user_id: str = None,
        consumer=None
    ):
        """
        Add a WebSocket connection.

        Args:
            connection_id: Connection ID
            proxy_id: Proxy node ID
            user_id: User ID
            consumer: Consumer instance
        """
        with self._lock:
            self._connections[connection_id] = {
                'proxy_id': proxy_id,
                'user_id': user_id,
                'consumer': consumer,
                'connected_at': timezone.now(),
            }

        logger.info(
            f"WebSocket connection added",
            extra={
                'connection_id': connection_id,
                'proxy_id': proxy_id,
            }
        )

    def remove_connection(self, connection_id: str):
        """
        Remove a WebSocket connection.

        Args:
            connection_id: Connection ID
        """
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections.pop(connection_id)
                logger.info(
                    f"WebSocket connection removed",
                    extra={
                        'connection_id': connection_id,
                        'proxy_id': conn['proxy_id'],
                    }
                )

    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection details.

        Args:
            connection_id: Connection ID

        Returns:
            Connection details or None
        """
        with self._lock:
            return self._connections.get(connection_id)

    def get_connections_for_proxy(self, proxy_id: str) -> List[str]:
        """
        Get all connection IDs for a proxy.

        Args:
            proxy_id: Proxy node ID

        Returns:
            List of connection IDs
        """
        with self._lock:
            return [
                conn_id for conn_id, conn in self._connections.items()
                if conn['proxy_id'] == proxy_id
            ]

    def get_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all connections.

        Returns:
            Dictionary of connections
        """
        with self._lock:
            return self._connections.copy()

    def graceful_shutdown(self, timeout: int = 30):
        """
        Gracefully shutdown all WebSocket connections.

        Args:
            timeout: Maximum time to wait for connections to close (seconds)
        """
        logger.info("Starting graceful WebSocket shutdown")

        # Get all connections
        connections = self.get_all_connections()

        # Send shutdown notification to all connections
        self._broadcast_shutdown_notification(connections)

        # Wait for connections to close
        shutdown_start = time.time()
        
        while connections and (time.time() - shutdown_start) < timeout:
            time.sleep(1)
            connections = self.get_all_connections()

        # Force close remaining connections
        if connections:
            logger.warning(f"Force closing {len(connections)} remaining connections")
            self._force_close_connections(connections)

        logger.info("WebSocket shutdown completed")

    def _broadcast_shutdown_notification(self, connections: Dict[str, Dict[str, Any]]):
        """Broadcast shutdown notification to all connections."""
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        try:
            message = {
                'type': 'server.shutdown',
                'timestamp': timezone.now().isoformat(),
                'payload': {
                    'message': 'Server is shutting down',
                    'reconnect_after': 60,  # Suggest reconnect after 60 seconds
                }
            }

            # Send to each connection's group
            for conn_id, conn in connections.items():
                proxy_id = conn['proxy_id']
                group_name = f'proxy_{proxy_id}'
                
                channel_layer.group_send(
                    group_name,
                    {
                        'type': 'server.shutdown',
                        'data': message
                    }
                )
        except Exception as e:
            logger.error(f"Failed to broadcast shutdown notification: {e}")

    def _force_close_connections(self, connections: Dict[str, Dict[str, Any]]):
        """Force close remaining connections."""
        for conn_id, conn in connections.items():
            try:
                consumer = conn.get('consumer')
                if consumer and hasattr(consumer, 'close'):
                    consumer.close(code=1000, reason='Server shutdown')
            except Exception as e:
                logger.error(f"Failed to close connection {conn_id}: {e}")


class TaskGracefulShutdown:
    """
    Manager for graceful task shutdown.
    """

    def __init__(self):
        self._running_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_task(
        self,
        task_id: str,
        task_type: str,
        proxy_id: str,
        callback=None
    ):
        """
        Register a running task for graceful shutdown.

        Args:
            task_id: Task ID
            task_type: Task type
            proxy_id: Proxy node ID
            callback: Cancellation callback
        """
        with self._lock:
            self._running_tasks[task_id] = {
                'task_type': task_type,
                'proxy_id': proxy_id,
                'callback': callback,
                'started_at': timezone.now(),
            }

    def unregister_task(self, task_id: str):
        """
        Unregister a task.

        Args:
            task_id: Task ID
        """
        with self._lock:
            if task_id in self._running_tasks:
                task = self._running_tasks.pop(task_id)
                logger.info(
                    f"Task unregistered",
                    extra={'task_id': task_id, 'task_type': task['task_type']}
                )

    def graceful_shutdown(self, timeout: int = 30):
        """
        Gracefully shutdown all running tasks.

        Args:
            timeout: Maximum time to wait for tasks to complete (seconds)
        """
        logger.info("Starting graceful task shutdown")

        with self._lock:
            tasks = list(self._running_tasks.items())

        if not tasks:
            logger.info("No running tasks to shutdown")
            return

        # Cancel tasks
        cancelled_count = 0
        for task_id, task_info in tasks:
            try:
                # Mark tasks as cancelling in database
                ProxyTask.objects.filter(id=task_id).update(
                    status='cancelled'
                )

                # Call cancellation callback
                if task_info.get('callback'):
                    task_info['callback'](task_id)

                cancelled_count += 1
            except Exception as e:
                logger.exception(f"Error cancelling task {task_id}: {e}")

        logger.info(
            f"Task shutdown completed",
            extra={'cancelled_tasks': cancelled_count}
        )

    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of running tasks.

        Returns:
            List of running task information
        """
        with self._lock:
            return [
                {
                    'task_id': task_id,
                    'task_type': info['task_type'],
                    'proxy_id': info['proxy_id'],
                    'duration': (timezone.now() - info['started_at']).total_seconds(),
                }
                for task_id, info in self._running_tasks.items()
            ]


class ShutdownSignalHandler:
    """
    Handler for shutdown signals (SIGINT, SIGTERM).
    """

    def __init__(self, shutdown_manager: GracefulShutdownManager):
        """
        Initialize signal handler.

        Args:
            shutdown_manager: GracefulShutdownManager instance
        """
        self.shutdown_manager = shutdown_manager

    def setup(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """
        Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received shutdown signal: {signal_name}")

        # Initiate graceful shutdown
        self.shutdown_manager.initiate_shutdown(reason=signal_name)


# Global instances
shutdown_manager = GracefulShutdownManager(shutdown_timeout=30)
websocket_manager = WebSocketConnectionManager()
task_shutdown_manager = TaskGracefulShutdown()
signal_handler = ShutdownSignalHandler(shutdown_manager)


def get_shutdown_manager() -> GracefulShutdownManager:
    """Get the global shutdown manager instance."""
    return shutdown_manager


def get_websocket_manager() -> WebSocketConnectionManager:
    """Get the global WebSocket manager instance."""
    return websocket_manager


def get_task_shutdown_manager() -> TaskGracefulShutdown:
    """Get the global task shutdown manager instance."""
    return task_shutdown_manager
