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
            'proxy_id': self.proxy_id,
            'server_time': timezone.now().isoformat()
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
                'heartbeat': self.handle_heartbeat,
                'register': self.handle_register,
                'task_update': self.handle_task_update,
                'task_result': self.handle_task_result,
                'log': self.handle_log,
                'status': self.handle_status,
                'backup_result': self.handle_backup_result,
                'restore_result': self.handle_restore_result,
                'mount_result': self.handle_mount_result,
                'snapshot_list_result': self.handle_snapshot_list_result,
                'test_connection_result': self.handle_test_connection_result,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_register(self, data):
        """
        Handle initial registration message from proxy.
        """
        install_token = data.get('install_token')
        proxy_info = data.get('proxy_info', {})

        success = await self.complete_registration(install_token, proxy_info)

        if success:
            await self.send(text_data=json.dumps({
                'type': 'register_ack',
                'status': 'success',
                'proxy_id': self.proxy_id
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'register_ack',
                'status': 'failed',
                'message': 'Invalid install token or proxy already registered'
            }))

    async def handle_heartbeat(self, data):
        """
        Handle heartbeat message from proxy.

        Updates proxy status and responds with any pending commands.
        """
        metrics = data.get('metrics', {})
        await self.update_proxy_heartbeat(metrics)

        # Check for pending tasks
        pending_tasks = await self.get_pending_tasks()

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'server_time': timezone.now().isoformat(),
            'pending_tasks': pending_tasks
        }))

    async def handle_task_update(self, data):
        """
        Handle task update message from proxy.
        """
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
        """
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
        """
        level = data.get('level', 'info')
        message = data.get('message')
        context = data.get('context', {})

        await self.store_log(level, message, context)

    async def handle_status(self, data):
        """
        Handle status report from proxy.
        """
        status_data = data.get('data', {})
        await self.update_proxy_status(status_data)

    async def handle_backup_result(self, data):
        """
        Handle backup task result from proxy.
        """
        task_id = data.get('task_id')
        snapshot_id = data.get('snapshot_id')
        stats = data.get('stats', {})
        error = data.get('error')

        await self.update_backup_result(task_id, snapshot_id, stats, error)

    async def handle_restore_result(self, data):
        """
        Handle restore task result from proxy.
        """
        task_id = data.get('task_id')
        stats = data.get('stats', {})
        error = data.get('error')

        await self.update_restore_result(task_id, stats, error)

    async def handle_mount_result(self, data):
        """
        Handle mount result from sync proxy.
        """
        repository_id = data.get('repository_id')
        mount_point = data.get('mount_point')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_mount_status(repository_id, mount_point, success, error)

    async def handle_snapshot_list_result(self, data):
        """
        Handle snapshot list result from proxy.
        """
        task_id = data.get('task_id')
        snapshots = data.get('snapshots', [])
        error = data.get('error')

        await self.update_snapshot_list_result(task_id, snapshots, error)

    async def handle_test_connection_result(self, data):
        """
        Handle connection test result from proxy.
        """
        resource_type = data.get('resource_type')
        resource_id = data.get('resource_id')
        success = data.get('success', False)
        error = data.get('error')
        details = data.get('details', {})

        await self.update_connection_status(resource_type, resource_id, success, error, details)

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
                proxy.status = ProxyNode.NodeStatus.ACTIVE
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
            proxy.status = ProxyNode.NodeStatus.ACTIVE
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
            'data': task_status
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
            'data': initial_status
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
