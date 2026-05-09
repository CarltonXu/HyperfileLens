"""
WebSocket Consumers for Proxy Nodes

This module provides WebSocket consumers for real-time
proxy communication, task execution, and status updates.
"""

import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async
from audit_log.services import AuditService
from alerts import get_manager
from .graceful_shutdown import shutdown_manager, websocket_manager, signal_handler
from .metrics_service import metrics_service
from core.websocket_validation import validate_and_log, ValidationResult


# Global alert manager instance
alert_manager = get_manager()


class ProxyConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for proxy connections.

    Handles real-time communication with agent and sync proxies.
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        Authenticates the proxy and establishes the connection.
        """
        self.proxy_id = self.scope['url_route']['kwargs']['proxy_id']
        self.room_group_name = f'proxy_{self.proxy_id}'

        # Verify proxy credentials
        valid = await self.verify_proxy()
        if not valid:
            await self.close(code=4001)
            return

        # Join proxy group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Update proxy connection status
        await self.update_proxy_online_status(True)

        # Create connection record
        await self.create_connection_record()

        # Send connection acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'proxy_id': self.proxy_id,
            }
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Cleans up connection state and updates proxy status.
        """
        # Leave proxy group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Update proxy connection status
        await self.update_proxy_online_status(False)

        # Check for proxy timeout alert
        await self.check_proxy_timeout_alert()

        # Update connection record
        await self.close_connection_record()

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.

        Processes commands from the proxy and responds accordingly.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            handlers = {
                # Control messages
                'register': self.handle_register,
                'heartbeat': self.handle_heartbeat,
                'ping': self.handle_ping,

                # Task status updates (unified format)
                'task_start': self.handle_task_start,
                'task_progress': self.handle_task_progress,
                'task_complete': self.handle_task_complete,

                # Log and status
                'log': self.handle_log,
                'status': self.handle_status,

                # Legacy result handlers (for backwards compatibility)
                'task_update': self.handle_task_update,  # Legacy
                'task_result': self.handle_task_result,  # Legacy
                'backup_result': self.handle_backup_result,
                'restore_result': self.handle_restore_result,
                'mount_result': self.handle_mount_result,
                'snapshot_list_result': self.handle_snapshot_list_result,
                'test_connection_result': self.handle_test_connection_result,
                'test_storage_result': self.handle_test_storage_result,
                'init_repository_result': self.handle_init_repository_result,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'id': str(uuid.uuid4()),
                    'timestamp': timezone.now().isoformat(),
                    'payload': {
                        'message': f'Unknown message type: {message_type}'
                    }
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'id': str(uuid.uuid4()),
                'timestamp': timezone.now().isoformat(),
                'payload': {
                    'message': 'Invalid JSON format'
                }
            }))

    async def handle_register(self, data):
        """
        Handle registration confirmation message from proxy.

        Registration is already done via HTTP API during installation.
        This message just confirms that the proxy is connecting via WebSocket.
        """
        # The proxy has already been registered via HTTP API
        # This is just a connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'register_ack',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'status': 'success',
                'proxy_id': self.proxy_id
            }
        }))

    async def handle_heartbeat(self, data):
        """
        Handle heartbeat message from proxy.

        Updates proxy status and responds with any pending commands.
        """
        metrics = data.get('metrics', {})
        await self.update_proxy_heartbeat(metrics)

        # Check for resource alerts
        await self.check_resource_alerts(metrics)

        # Check for pending tasks
        pending_tasks = await self.get_pending_tasks()

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'server_time': timezone.now().isoformat(),
                'pending_tasks': pending_tasks
            }
        }))

    async def handle_ping(self, data):
        """Handle ping message from proxy."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {}
        }))

    # ==================== Unified Task Status Handlers ====================

    async def handle_task_start(self, data):
        """
        Handle task start notification from proxy.

        Expected format:
        {
            'type': 'task_start',
            'payload': {
                'task_id': 'uuid',
                'task_type': 'backup|restore|mount|test_storage|init_repository',
                'timestamp': 'iso timestamp'
            }
        }
        """
        payload = data.get('payload', {})
        task_id = payload.get('task_id')
        task_type = payload.get('task_type')

        # Extract data from payload if present
        if payload:
            task_id = payload.get('task_id')
            task_type = payload.get('task_type')
        else:
            # Legacy format
            task_id = data.get('task_id')
            task_type = data.get('task_type')

        await self.update_task_status(task_id, 'running', 0, 'Task started')

        # Broadcast to task group
        if task_id:
            await self.channel_layer.group_send(
                f'task_{task_id}',
                {
                    'type': 'task_start',
                    'data': {
                        'task_id': task_id,
                        'task_type': task_type,
                        'status': 'running',
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

    async def handle_task_progress(self, data):
        """
        Handle task progress update from proxy.

        Expected format:
        {
            'type': 'task_progress',
            'payload': {
                'task_id': 'uuid',
                'progress': 50,
                'message': 'Processing...',
                'current_file': '/path/to/file',
                'total_files': 100,
                'processed_files': 25,
                'processed_bytes': 1024000,
                'total_bytes': 4096000,
                'speed_mbps': 5.2,
                'eta': '5m 30s',
                'timestamp': 'iso timestamp'
            }
        }
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            progress = payload.get('progress', 0)
            message = payload.get('message', '')
        else:
            # Legacy format
            task_id = data.get('task_id')
            progress = data.get('progress', 0)
            message = data.get('message', '')

        await self.update_task_progress(
            task_id, progress, message,
            current_file=payload.get('current_file'),
            total_files=payload.get('total_files', 0),
            processed_files=payload.get('processed_files', 0),
            processed_bytes=payload.get('processed_bytes', 0),
            total_bytes=payload.get('total_bytes', 0),
            speed_mbps=payload.get('speed_mbps', 0.0),
            eta=payload.get('eta', '')
        )

        # Broadcast to task group
        if task_id:
            await self.channel_layer.group_send(
                f'task_{task_id}',
                {
                    'type': 'task_progress',
                    'data': {
                        'task_id': task_id,
                        'status': 'running',
                        'progress': progress,
                        'message': message,
                        'current_file': payload.get('current_file'),
                        'total_files': payload.get('total_files', 0),
                        'processed_files': payload.get('processed_files', 0),
                        'processed_bytes': payload.get('processed_bytes', 0),
                        'total_bytes': payload.get('total_bytes', 0),
                        'speed_mbps': payload.get('speed_mbps', 0.0),
                        'eta': payload.get('eta', ''),
                    }
                }
            )

    async def handle_task_complete(self, data):
        """
        Handle task completion notification from proxy.

        Expected format:
        {
            'type': 'task_complete',
            'payload': {
                'task_id': 'uuid',
                'task_type': 'backup|restore|mount|test_storage|init_repository',
                'success': true,
                'result': {...},
                'error': 'error message if failed',
                'timestamp': 'iso timestamp'
            }
        }
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            task_type = payload.get('task_type')
            success = payload.get('success', False)
            result = payload.get('result', {})
            error = payload.get('error')
        else:
            # Legacy format
            task_id = data.get('task_id')
            task_type = data.get('task_type')
            success = data.get('success', False)
            result = data.get('result', {})
            error = data.get('error')

        await self.complete_task(task_id, success, result, error)

        # Create alert for failed tasks
        if not success and task_id and error:
            await self.create_task_failed_alert(task_id, error)

        # Broadcast to task group
        if task_id:
            await self.channel_layer.group_send(
                f'task_{task_id}',
                {
                    'type': 'task_result',
                    'data': {
                        'task_id': task_id,
                        'task_type': task_type,
                        'success': success,
                        'result': result,
                        'error': error
                    }
                }
            )

    async def handle_task_update(self, data):
        """
        Handle task update message from proxy.

        Proxy format: {type: 'task_update', payload: {task_id, status, progress, message}}
        Legacy format: {type: 'task_update', task_id, status, progress, message}
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            status = payload.get('status')
            progress = payload.get('progress', 0)
            message = payload.get('message', '')
        else:
            task_id = data.get('task_id')
            status = data.get('status')
            progress = data.get('progress', 0)
            message = data.get('message', '')

        await self.update_task_status(task_id, status, progress, message)

        # Broadcast to task group for real-time UI updates
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_progress',
                'data': {
                    'task_id': task_id,
                    'status': status,
                    'progress': progress,
                    'message': message
                }
            }
        )

    async def handle_task_result(self, data):
        """
        Handle task result message from proxy.

        Proxy format: {type: 'task_result', payload: {task_id, task_type, success, result, error}}
        Legacy format: {type: 'task_result', task_id, task_type, success, result, error}
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            task_type = payload.get('task_type')
            success = payload.get('success', False)
            result = payload.get('result', {})
            error = payload.get('error')
        else:
            task_id = data.get('task_id')
            task_type = data.get('task_type')
            success = data.get('success', False)
            result = data.get('result', {})
            error = data.get('error')

        await self.complete_task(task_id, success, result, error)

        # Broadcast to task group
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': task_type,
                    'success': success,
                    'result': result,
                    'error': error
                }
            }
        )

    async def handle_log(self, data):
        """
        Handle log message from proxy.

        Proxy format: {type: 'log', payload: {level, message, context}}
        Legacy format: {type: 'log', level, message, context}
        """
        payload = data.get('payload', {})
        if payload:
            level = payload.get('level', 'info')
            message = payload.get('message')
            context = payload.get('context', {})
        else:
            level = data.get('level', 'info')
            message = data.get('message')
            context = data.get('context', {})

        await self.store_log(level, message, context)

    async def handle_status(self, data):
        """
        Handle status report from proxy.

        Proxy format: {type: 'status', payload: {data: {...}}}
        Legacy format: {type: 'status', data: {...}}
        """
        payload = data.get('payload', {})
        if payload:
            status_data = payload.get('data', {})
        else:
            status_data = data.get('data', {})
        await self.update_proxy_status(status_data)

    async def handle_backup_result(self, data):
        """
        Handle backup task result from proxy.

        Proxy format: {type: 'backup_result', payload: {task_id, snapshot_id, stats, error}}
        Legacy format: {type: 'backup_result', task_id, snapshot_id, stats, error}
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            snapshot_id = payload.get('snapshot_id')
            stats = payload.get('stats', {})
            error = payload.get('error')
        else:
            task_id = data.get('task_id')
            snapshot_id = data.get('snapshot_id')
            stats = data.get('stats', {})
            error = data.get('error')

        await self.update_backup_result(task_id, snapshot_id, stats, error)

    async def handle_restore_result(self, data):
        """
        Handle restore task result from proxy.

        Proxy format: {type: 'restore_result', payload: {task_id, stats, error}}
        Legacy format: {type: 'restore_result', task_id, stats, error}
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            stats = payload.get('stats', {})
            error = payload.get('error')
        else:
            task_id = data.get('task_id')
            stats = data.get('stats', {})
            error = data.get('error')

        await self.update_restore_result(task_id, stats, error)

    async def handle_mount_result(self, data):
        """
        Handle mount result from sync proxy.

        Proxy format: {type: 'mount_result', payload: {repository_id, mount_point, success, error}}
        Legacy format: {type: 'mount_result', repository_id, mount_point, success, error}
        """
        payload = data.get('payload', {})
        if payload:
            repository_id = payload.get('repository_id')
            mount_point = payload.get('mount_point')
            success = payload.get('success', False)
            error = payload.get('error')
        else:
            repository_id = data.get('repository_id')
            mount_point = data.get('mount_point')
            success = data.get('success', False)
            error = data.get('error')

        await self.update_mount_status(repository_id, mount_point, success, error)

    async def handle_snapshot_list_result(self, data):
        """
        Handle snapshot list result from proxy.

        Proxy format: {type: 'snapshot_list_result', payload: {task_id, snapshots, error}}
        Legacy format: {type: 'snapshot_list_result', task_id, snapshots, error}
        """
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            snapshots = payload.get('snapshots', [])
            error = payload.get('error')
        else:
            task_id = data.get('task_id')
            snapshots = data.get('snapshots', [])
            error = data.get('error')

        await self.update_snapshot_list_result(task_id, snapshots, error)

    async def handle_test_connection_result(self, data):
        """
        Handle connection test result from proxy.

        Proxy format: {type: 'test_connection_result', payload: {resource_type, resource_id, success, error, details}}
        Legacy format: {type: 'test_connection_result', resource_type, resource_id, success, error, details}
        """
        payload = data.get('payload', {})
        if payload:
            resource_type = payload.get('resource_type')
            resource_id = payload.get('resource_id')
            success = payload.get('success', False)
            error = payload.get('error')
            details = payload.get('details', {})
        else:
            resource_type = data.get('resource_type')
            resource_id = data.get('resource_id')
            success = data.get('success', False)
            error = data.get('error')
            details = data.get('details', {})

        await self.update_connection_status(resource_type, resource_id, success, error, details)

    async def handle_test_storage_result(self, data):
        """
        Handle storage test result from sync proxy.

        Expected data format:
        {
            'type': 'test_storage_result',
            'payload': {
                'task_id': 'uuid',
                'success': True/False,
                'result': {
                    'storage_type': 'nas/s3/local',
                    'repository_id': 'uuid',
                    'connectivity': {...},
                    'write_test': {...},
                    'space_info': {...}
                },
                'error': 'error message if failed',
                'timestamp': 'iso timestamp'
            }
        }
        """
        # Extract data from payload if present (proxy format)
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            success = payload.get('success', False)
            result = payload.get('result', {})
            error = payload.get('error')
        else:
            # Legacy format (data at top level)
            task_id = data.get('task_id')
            success = data.get('success', False)
            result = data.get('result', {})
            error = data.get('error')
        repository_id = result.get('repository_id')

        # Update repository connection test status
        await self.update_storage_test_result(repository_id, task_id, success, result, error)

        # Broadcast to task group for real-time UI updates
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'test_storage',
                    'success': success,
                    'result': result,
                    'error': error
                }
            }
        )

    async def handle_init_repository_result(self, data):
        """
        Handle repository initialization result from sync proxy.

        Expected data format:
        {
            'type': 'init_repository_result',
            'payload': {
                'task_id': 'uuid',
                'repository_id': 'uuid',
                'success': True/False,
                'error': 'error message if failed',
                'timestamp': 'iso timestamp'
            }
        }
        """
        # Extract data from payload if present (proxy format)
        payload = data.get('payload', {})
        if payload:
            task_id = payload.get('task_id')
            repository_id = payload.get('repository_id')
            success = payload.get('success', False)
            error = payload.get('error')
        else:
            # Legacy format (data at top level)
            task_id = data.get('task_id')
            repository_id = data.get('repository_id')
            success = data.get('success', False)
            error = data.get('error')

        # Update repository initialization status
        await self.update_repository_init_result(repository_id, task_id, success, error)

        # Broadcast to task group for real-time UI updates
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'init_repository',
                    'repository_id': repository_id,
                    'success': success,
                    'error': error
                }
            }
        )

    # Send methods for group broadcasts
    async def proxy_message(self, event):
        """Handler for proxy message events."""
        await self.send(text_data=json.dumps(event['data']))

    async def command_message(self, event):
        """Handler for command message events."""
        await self.send(text_data=json.dumps(event['data']))

    async def task_message(self, event):
        """Handler for task message events."""
        await self.send(text_data=json.dumps(event['data']))

    # Database operations
    @sync_to_async
    def verify_proxy(self):
        """Verify proxy exists and is valid."""
        from .models import ProxyNode
        try:
            ProxyNode.objects.get(id=self.proxy_id)
            return True
        except ProxyNode.DoesNotExist:
            return False

    @sync_to_async
    def update_proxy_online_status(self, online):
        """Update proxy online status."""
        from .models import ProxyNode, NodeConnection
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            if online:
                proxy.status = ProxyNode.NodeStatus.ONLINE
                if not proxy.registered_at:
                    proxy.registered_at = timezone.now()
            else:
                proxy.status = ProxyNode.NodeStatus.OFFLINE
            proxy.save(update_fields=['status', 'registered_at', 'updated_at'])
            
            # Record audit log for online/offline status
            # Use the first superuser as the actor for system-triggered events
            from accounts.models import User
            system_user = User.objects.filter(is_superuser=True).first()
            if system_user:
                if online:
                    AuditService.log_proxy_online(system_user, proxy)
                else:
                    AuditService.log_proxy_offline(system_user, proxy)
        except ProxyNode.DoesNotExist:
            pass

    @sync_to_async
    def create_connection_record(self):
        """Create connection record."""
        from .models import ProxyNode, NodeConnection
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            NodeConnection.objects.create(
                proxy=proxy,
                status=NodeConnection.ConnectionStatus.CONNECTED,
                remote_address=self.scope.get('client', [None])[0],
                user_agent=self.scope.get('headers', {}).get(b'user-agent', b'').decode()
            )
        except Exception:
            pass

    @sync_to_async
    def close_connection_record(self):
        """Close connection record."""
        from .models import NodeConnection
        try:
            conn = NodeConnection.objects.filter(
                proxy_id=self.proxy_id,
                status=NodeConnection.ConnectionStatus.CONNECTED
            ).order_by('-connected_at').first()
            if conn:
                conn.disconnect()
        except Exception:
            pass

    @sync_to_async
    def complete_registration(self, install_token, proxy_info):
        """Complete proxy registration."""
        from .models import ProxyNode
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id, install_token=install_token)
            proxy.install_token = ''  # Clear token after use
            proxy.status = ProxyNode.NodeStatus.ONLINE
            proxy.registered_at = timezone.now()
            proxy.installed_at = timezone.now()

            if proxy_info:
                proxy.hostname = proxy_info.get('hostname', '')
                proxy.internal_ip = proxy_info.get('internal_ip')
                proxy.operating_system = proxy_info.get('os', '')
                proxy.os_version = proxy_info.get('os_version', '')
                proxy.version = proxy_info.get('version', '')
                proxy.kopia_version = proxy_info.get('kopia_version', '')
                proxy.cpu_cores = proxy_info.get('cpu_cores')
                proxy.memory_total = proxy_info.get('memory_total')
                proxy.disk_total = proxy_info.get('disk_total')
                proxy.capabilities = proxy_info.get('capabilities', {})

            proxy.save()
            
            # Record audit log for proxy registration
            # Use the first superuser as the actor for system-triggered events
            from accounts.models import User
            system_user = User.objects.filter(is_superuser=True).first()
            if system_user:
                AuditService.log_proxy_register(system_user, proxy)
            
            return True
        except ProxyNode.DoesNotExist:
            return False

    @sync_to_async
    def update_proxy_heartbeat(self, metrics):
        """Update proxy heartbeat."""
        from .models import ProxyNode, ProxyHeartbeat
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            proxy.last_heartbeat = timezone.now()

            if metrics:
                proxy.cpu_usage = metrics.get('cpu_usage')
                proxy.memory_usage = metrics.get('memory_usage')
                proxy.disk_usage = metrics.get('disk_usage')
                proxy.active_tasks = metrics.get('active_tasks', 0)

            proxy.save()

            # Create heartbeat record
            ProxyHeartbeat.objects.create(
                proxy=proxy,
                cpu_usage=metrics.get('cpu_usage'),
                memory_usage=metrics.get('memory_usage'),
                disk_usage=metrics.get('disk_usage'),
                network_in=metrics.get('network_in'),
                network_out=metrics.get('network_out'),
                active_tasks=metrics.get('active_tasks', 0),
                completed_tasks=metrics.get('completed_tasks', 0),
                failed_tasks=metrics.get('failed_tasks', 0),
                metadata=metrics.get('metadata', {})
            )
        except ProxyNode.DoesNotExist:
            pass

    @sync_to_async
    def get_pending_tasks(self):
        """Get pending tasks for the proxy."""
        from .models import ProxyTask
        tasks = ProxyTask.objects.filter(
            proxy_id=self.proxy_id,
            status=ProxyTask.TaskStatus.PENDING
        ).values('id', 'task_type', 'parameters', 'timeout_seconds')

        result = []
        for task in tasks:
            result.append({
                'task_id': str(task['id']),
                'task_type': task['task_type'],
                'parameters': task['parameters'],
                'timeout_seconds': task['timeout_seconds']
            })
        return result

    @sync_to_async
    def update_task_status(self, task_id, status, progress, message):
        """Update task status."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=task_id, proxy_id=self.proxy_id)
            task.status = status
            task.progress = progress
            task.progress_message = message
            if status == 'accepted':
                task.accepted_at = timezone.now()
            elif status == 'running':
                task.started_at = timezone.now()
            task.save()
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def update_task_progress(self, task_id, progress, message,
                            current_file=None, total_files=None,
                            processed_files=None, processed_bytes=None,
                            total_bytes=None, speed_mbps=None, eta=None):
        """Update task with detailed progress information."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=task_id, proxy_id=self.proxy_id)
            task.status = ProxyTask.TaskStatus.RUNNING
            task.progress = progress
            task.progress_message = message
            # Update detailed progress fields if provided
            if current_file is not None:
                task.current_file = current_file
            if total_files is not None:
                task.total_files = total_files
            if processed_files is not None:
                task.processed_files = processed_files
            if processed_bytes is not None:
                task.processed_bytes = processed_bytes
            if total_bytes is not None:
                task.total_bytes = total_bytes
            if speed_mbps is not None:
                task.speed_mbps = speed_mbps
            if eta is not None:
                task.eta = eta
            task.save()
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def complete_task(self, task_id, success, result, error):
        """Complete a task."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=task_id, proxy_id=self.proxy_id)
            if success:
                task.status = ProxyTask.TaskStatus.COMPLETED
            else:
                task.status = ProxyTask.TaskStatus.FAILED
                task.error_message = error or ''
            task.result = result
            task.progress = 100
            task.completed_at = timezone.now()
            task.save()
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def check_resource_alerts(self, metrics):
        """Check and create alerts for resource thresholds."""
        from .models import ProxyNode
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            alert_manager.check_resource_alerts(proxy, metrics)
        except ProxyNode.DoesNotExist:
            pass

    @sync_to_async
    def create_task_failed_alert(self, task_id, error):
        """Create an alert for a failed task."""
        from .models import ProxyTask, ProxyNode
        try:
            task = ProxyTask.objects.get(id=task_id, proxy_id=self.proxy_id)
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            alert_manager.check_task_failed(task, error)
        except (ProxyTask.DoesNotExist, ProxyNode.DoesNotExist):
            pass

    @sync_to_async
    def check_proxy_timeout_alert(self):
        """Check if proxy should trigger timeout alert."""
        from .models import ProxyNode
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            alert_manager.check_proxy_timeout(proxy)
        except ProxyNode.DoesNotExist:
            pass

    @sync_to_async
    def store_log(self, level, message, context):
        """Store log message from proxy."""
        import logging
        logger = logging.getLogger('hyperfilelens.proxy')

        log_msg = f"[Proxy {self.proxy_id}] {message}"
        if level == 'error':
            logger.error(log_msg, extra=context)
        elif level == 'warning':
            logger.warning(log_msg, extra=context)
        else:
            logger.info(log_msg, extra=context)

    @sync_to_async
    def update_proxy_status(self, status_data):
        """Update proxy status information."""
        from .models import ProxyNode
        try:
            proxy = ProxyNode.objects.get(id=self.proxy_id)
            proxy.version = status_data.get('version', proxy.version)
            proxy.kopia_version = status_data.get('kopia_version', proxy.kopia_version)
            proxy.capabilities = status_data.get('capabilities', proxy.capabilities)
            proxy.save(update_fields=['version', 'kopia_version', 'capabilities', 'updated_at'])
        except ProxyNode.DoesNotExist:
            pass

    @sync_to_async
    def update_backup_result(self, task_id, snapshot_id, stats, error):
        """Update backup task result."""
        from .models import ProxyTask
        from backup_tasks.models import BackupTask, BackupSnapshot
        try:
            task = ProxyTask.objects.get(id=task_id)
            if error:
                task.fail(error)
            else:
                task.complete({'snapshot_id': snapshot_id, 'stats': stats})

                # Create snapshot record if backup task exists
                if task.repository_id:
                    BackupSnapshot.objects.create(
                        name=f'snapshot-{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                        repository_id=task.repository_id,
                        storage_path=snapshot_id,
                        total_size=stats.get('total_size', 0),
                        file_count=stats.get('file_count', 0),
                    )
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def update_restore_result(self, task_id, stats, error):
        """Update restore task result."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=task_id)
            if error:
                task.fail(error)
            else:
                task.complete(stats)
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def update_mount_status(self, repository_id, mount_point, success, error):
        """Update mount status."""
        from repository.models import Repository
        try:
            repo = Repository.objects.get(id=repository_id)
            if success:
                repo.mount_status = 'mounted'
                repo.mount_point = mount_point
            else:
                repo.mount_status = 'error'
                repo.mount_error = error
            repo.save()
        except Repository.DoesNotExist:
            pass

    @sync_to_async
    def update_snapshot_list_result(self, task_id, snapshots, error):
        """Update snapshot list result."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=task_id)
            if error:
                task.fail(error)
            else:
                task.complete({'snapshots': snapshots, 'count': len(snapshots)})
        except ProxyTask.DoesNotExist:
            pass

    @sync_to_async
    def update_connection_status(self, resource_type, resource_id, success, error, details):
        """Update connection status for repository or source resource."""
        if resource_type == 'repository':
            from repository.models import Repository
            try:
                repo = Repository.objects.get(id=resource_id)
                repo.connection_status = 'connected' if success else 'error'
                repo.last_connection_test = timezone.now()
                if error:
                    repo.connection_error = error
                repo.save()
            except Repository.DoesNotExist:
                pass
        elif resource_type == 'source_resource':
            from source_resources.models import SourceResource
            try:
                resource = SourceResource.objects.get(id=resource_id)
                resource.connection_status = 'connected' if success else 'error'
                resource.last_connection_test = timezone.now()
                if error:
                    resource.connection_error = error
                resource.save()
            except SourceResource.DoesNotExist:
                pass

    def create_quota_alert(self, repo, usage_percentage):
        """Create a quota exceeded alert for the repository (sync function)."""
        from alerts.types import AlertType, AlertSeverity

        try:
            # Create alert using the alert manager
            alert_manager.create_alert(
                alert_type=AlertType.REPOSITORY_QUOTA_EXCEEDED.value,
                severity=AlertSeverity.WARNING,
                title=f"Repository Quota Warning: {repo.name}",
                message=f"Repository '{repo.name}' has exceeded {usage_percentage:.1f}% of quota "
                       f"(used: {repo.used_space / (1024**3):.2f}GB, quota: {repo.quota_bytes / (1024**3):.2f}GB)",
                entity_type='repository.Repository',
                entity_id=str(repo.id),
                entity_name=repo.name,
                repository=repo,
                details={
                    'quota_bytes': repo.quota_bytes,
                    'used_space': repo.used_space,
                    'usage_percentage': usage_percentage,
                    'quota_warning_threshold': repo.quota_warning_threshold,
                    'capacity': repo.capacity,
                },
                metric_value=usage_percentage,
                threshold_value=repo.quota_warning_threshold,
                source='repository',
            )
            logger.info(f"[Quota Alert] Created alert for repository '{repo.name}' (ID: {repo.id})")
        except Exception as e:
            logger.error(f"[Quota Alert] Failed to create alert for repository '{repo.name}': {e}")

    @sync_to_async
    def update_storage_test_result(self, repository_id, task_id, success, result, error):
        """Update storage test result for repository."""
        from repository.models import Repository
        from .models import ProxyTask
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Update task status
            task = ProxyTask.objects.filter(id=task_id).first()
            if task:
                if success:
                    task.complete(result)
                else:
                    task.fail(error or 'Storage test failed')
            
            # Update repository status
            if repository_id:
                repo = Repository.objects.get(id=repository_id)
                repo.last_connection_test = timezone.now()

                # Prepare detailed test results
                test_details = {
                    'success': success,
                    'timestamp': timezone.now().isoformat(),
                    'connectivity': result.get('connectivity', {}),
                    'write_test': result.get('write_test', {}),
                    'space_info': result.get('space_info', {}),
                }

                if success:
                    # Build summary message
                    connectivity = result.get('connectivity', {})
                    write_test = result.get('write_test', {})
                    space_info = result.get('space_info', {})

                    summary_parts = []
                    if connectivity:
                        if connectivity.get('reachable'):
                            summary_parts.append(f"Connected (response time: {connectivity.get('response_time', 0)}ms)")
                        else:
                            summary_parts.append(f"Not reachable: {connectivity.get('error', 'Unknown error')}")

                    if write_test:
                        if write_test.get('writable'):
                            write_speed = write_test.get('write_speed', 0)
                            read_speed = write_test.get('read_speed', 0)
                            summary_parts.append(f"Writable (write: {write_speed} KB/s, read: {read_speed} KB/s)")
                        else:
                            summary_parts.append(f"Not writable: {write_test.get('error', 'Unknown error')}")

                    repo.connection_test_result = ' | '.join(summary_parts) if summary_parts else 'Connection test successful'
                    repo.connection_test_details = test_details
                    repo.status = Repository.STATUS_ACTIVE

                    # Update actual capacity and used space from space_info (NOT the quota!)
                    # capacity is the actual detected capacity, quota_bytes is user-defined limit
                    if space_info:
                        actual_capacity = space_info.get('total_bytes', 0)
                        actual_used = space_info.get('used_bytes', 0)

                        # Only update capacity if we detected a value
                        if actual_capacity > 0:
                            repo.capacity = actual_capacity

                        repo.used_space = actual_used

                        # Check if user has quota enabled and check quota warning
                        if repo.quota_enabled and repo.quota_bytes > 0:
                            usage_percentage = (actual_used / repo.quota_bytes) * 100
                            if usage_percentage >= repo.quota_warning_threshold:
                                logger.warning(
                                    f"[Quota Alert] Repository '{repo.name}' (ID: {repository_id}) - "
                                    f"usage {usage_percentage:.1f}% exceeds quota warning threshold "
                                    f"{repo.quota_warning_threshold}% (used: {actual_used / (1024**3):.2f}GB, "
                                    f"quota: {repo.quota_bytes / (1024**3):.2f}GB)"
                                )
                                # Create quota alert (sync call)
                                self.create_quota_alert(repo, usage_percentage)

                    logger.info(
                        f"[Storage Test] Repository '{repo.name}' (ID: {repository_id}) - success={success}, "
                        f"connectivity={connectivity.get('reachable')}, "
                        f"writable={write_test.get('writable')}, "
                        f"actual_capacity_gb={repo.capacity / (1024**3):.2f}, "
                        f"used_space_gb={repo.used_space / (1024**3):.2f}, "
                        f"quota_enabled={repo.quota_enabled}, "
                        f"quota_bytes_gb={repo.quota_bytes / (1024**3):.2f}"
                    )
                else:
                    repo.connection_test_result = f"Connection test failed: {error}"
                    repo.connection_test_details = test_details
                    repo.status = Repository.STATUS_ERROR
                    repo.status_message = error

                    logger.warning(
                        f"[Storage Test] Repository '{repo.name}' (ID: {repository_id}) - failed: {error}"
                    )

                # Save repository with updated test results
                repo.save()
        except Repository.DoesNotExist:
            logger.warning(f"[Storage Test] Repository not found: {repository_id}")
        except Exception as e:
            logger.error(f"[Storage Test] Error updating result: {e}")

    @sync_to_async
    def update_repository_init_result(self, repository_id, task_id, success, error):
        """Update repository initialization result."""
        from repository.models import Repository
        from .models import ProxyTask
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Update task status
            task = ProxyTask.objects.filter(id=task_id).first()
            if task:
                if success:
                    task.complete({'repository_id': repository_id})
                else:
                    task.fail(error or 'Repository initialization failed')
            
            # Update repository status
            if repository_id:
                repo = Repository.objects.get(id=repository_id)
                
                if success:
                    repo.kopia_initialized = True
                    repo.kopia_repository_id = repository_id
                    repo.status = Repository.STATUS_ACTIVE
                    repo.status_message = ''
                else:
                    repo.status = Repository.STATUS_ERROR
                    repo.status_message = error or 'Repository initialization failed'
                
                repo.save()
                logger.info(
                    f"[Repository Init] Repository '{repo.name}' (ID: {repository_id}) - "
                    f"success={success}, error={error}"
                )
        except Repository.DoesNotExist:
            logger.warning(f"[Repository Init] Repository not found: {repository_id}")
        except Exception as e:
            logger.error(f"[Repository Init] Error updating result: {e}")


class TaskConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for task execution.

    Handles real-time task progress and result streaming.
    """

    async def connect(self):
        """Handle WebSocket connection for task."""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'

        # Join task group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current task status
        task_status = await self.get_task_status()
        await self.send(text_data=json.dumps({
            'type': 'task_status',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'data': task_status
            }
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages."""
        pass

    async def task_progress(self, event):
        """Handler for task progress events."""
        await self.send(text_data=json.dumps(event['data']))

    async def task_result(self, event):
        """Handler for task result events."""
        await self.send(text_data=json.dumps(event['data']))

    @sync_to_async
    def get_task_status(self):
        """Get current task status."""
        from .models import ProxyTask
        try:
            task = ProxyTask.objects.get(id=self.task_id)
            return {
                'task_id': str(task.id),
                'task_type': task.task_type,
                'status': task.status,
                'progress': task.progress,
                'progress_message': task.progress_message,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }
        except ProxyTask.DoesNotExist:
            return {'error': 'Task not found'}


class StatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system status streaming.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.room_group_name = 'system_status'

        # Join status group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial status
        initial_status = await self.get_system_status()
        await self.send(text_data=json.dumps({
            'type': 'initial_status',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'data': initial_status
            }
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages."""
        pass

    async def status_update(self, event):
        """Handler for status update events."""
        await self.send(text_data=json.dumps(event['data']))

    @sync_to_async
    def get_system_status(self):
        """Get current system status."""
        from .models import ProxyNode, ProxyTask
        from backup_tasks.models import BackupTask
        from repository.models import Repository

        total_proxies = ProxyNode.objects.count()
        online_proxies = sum(1 for p in ProxyNode.objects.all() if p.is_online())

        return {
            'total_proxies': total_proxies,
            'online_proxies': online_proxies,
            'offline_proxies': total_proxies - online_proxies,
            'agent_proxies': ProxyNode.objects.filter(role=ProxyNode.Role.AGENT).count(),
            'sync_proxies': ProxyNode.objects.filter(role=ProxyNode.Role.SYNC).count(),
            'total_backup_tasks': BackupTask.objects.count(),
            'running_tasks': ProxyTask.objects.filter(status='running').count(),
            'total_repositories': Repository.objects.count(),
            'server_time': timezone.now().isoformat()
        }


# Utility functions for sending commands to proxies
async def send_backup_command(proxy_id, task_data):
    """
    Send backup command to a proxy.

    Args:
        proxy_id: Target proxy ID
        task_data: Backup task data
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'proxy_{proxy_id}',
        {
            'type': 'task_message',
            'data': {
                'type': 'backup',
                'payload': task_data
            }
        }
    )


async def send_restore_command(proxy_id, task_data):
    """Send restore command to a proxy."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'proxy_{proxy_id}',
        {
            'type': 'task_message',
            'data': {
                'type': 'restore',
                'payload': task_data
            }
        }
    )


async def send_mount_command(proxy_id, task_data):
    """Send mount command to a sync proxy."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'proxy_{proxy_id}',
        {
            'type': 'task_message',
            'data': {
                'type': 'mount',
                'payload': task_data
            }
        }
    )


async def send_snapshot_list_command(proxy_id, task_data):
    """Send snapshot list command to a proxy."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'proxy_{proxy_id}',
        {
            'type': 'task_message',
            'data': {
                'type': 'snapshot_list',
                'payload': task_data
            }
        }
    )


async def send_test_connection_command(proxy_id, resource_type, resource_id, config):
    """Send test connection command to a proxy."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'proxy_{proxy_id}',
        {
            'type': 'task_message',
            'data': {
                'type': 'test_connection',
                'payload': {
                    'resource_type': resource_type,
                    'resource_id': str(resource_id),
                    'config': config
                }
            }
        }
    )


# Alias for backwards compatibility
NodeConsumer = ProxyConsumer
