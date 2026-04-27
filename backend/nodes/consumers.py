"""
WebSocket Consumers for Nodes Application

This module provides WebSocket consumers for real-time
node communication, task execution, and status updates.
"""

import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async


class NodeConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for node connections.

    Handles real-time communication with source proxy
    and target gateway nodes.
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        Authenticates the node and establishes the connection.
        """
        self.node_id = self.scope['url_route']['kwargs']['node_id']
        self.room_group_name = f'node_{self.node_id}'

        # Join node group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Update node connection status
        await self.update_node_online_status(True)

        # Send connection acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'node_id': self.node_id,
            'server_time': timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Cleans up connection state and updates node status.
        """
        # Leave node group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Update node connection status
        await self.update_node_online_status(False)

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.

        Processes commands from the node and responds accordingly.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'heartbeat':
                await self.handle_heartbeat(data)
            elif message_type == 'task_update':
                await self.handle_task_update(data)
            elif message_type == 'log':
                await self.handle_log(data)
            elif message_type == 'status':
                await self.handle_status(data)
            elif message_type == 'backup_result':
                await self.handle_backup_result(data)
            elif message_type == 'restore_result':
                await self.handle_restore_result(data)
            elif message_type == 'test_connection_result':
                await self.handle_test_connection_result(data)
            elif message_type == 'init_repo_result':
                await self.handle_init_repo_result(data)
            elif message_type == 'mount_result':
                await self.handle_mount_result(data)
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

    async def handle_heartbeat(self, data):
        """
        Handle heartbeat message from node.

        Updates node status and responds with any pending commands.
        """
        await self.update_node_heartbeat(data)

        # Check for pending tasks or commands
        pending_commands = await self.get_pending_commands()

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'server_time': timezone.now().isoformat(),
            'pending_commands': pending_commands
        }))

    async def handle_task_update(self, data):
        """
        Handle task update message from node.

        Updates task status and progress.
        """
        task_id = data.get('task_id')
        status = data.get('status')
        progress = data.get('progress', 0)
        result = data.get('result', {})

        await self.update_task_status(task_id, status, progress, result)

        # Broadcast to task group for real-time UI updates
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_progress',
                'data': {
                    'task_id': task_id,
                    'status': status,
                    'progress': progress,
                    'result': result
                }
            }
        )

    async def handle_log(self, data):
        """
        Handle log message from node.

        Stores or forwards log data.
        """
        log_level = data.get('level', 'info')
        message = data.get('message')
        metadata = data.get('metadata', {})

        await self.store_log(log_level, message, metadata)

    async def handle_status(self, data):
        """
        Handle status report from node.

        Updates node system information.
        """
        cpu_usage = data.get('cpu_usage')
        memory_usage = data.get('memory_usage')
        disk_usage = data.get('disk_usage')

        await self.update_node_status(cpu_usage, memory_usage, disk_usage)

    async def handle_backup_result(self, data):
        """
        Handle backup task result from node.

        Updates backup task status and creates snapshot record.
        """
        task_id = data.get('task_id')
        success = data.get('success', False)
        snapshot_id = data.get('snapshot_id')
        error = data.get('error')
        stats = data.get('stats', {})

        await self.update_backup_task_result(task_id, success, snapshot_id, error, stats)

        # Broadcast to task group
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'success': success,
                    'snapshot_id': snapshot_id,
                    'error': error,
                    'stats': stats
                }
            }
        )

    async def handle_restore_result(self, data):
        """
        Handle restore task result from node.

        Updates recovery task status.
        """
        task_id = data.get('task_id')
        success = data.get('success', False)
        error = data.get('error')
        stats = data.get('stats', {})

        await self.update_recovery_task_result(task_id, success, error, stats)

        # Broadcast to task group
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'success': success,
                    'error': error,
                    'stats': stats
                }
            }
        )

    async def handle_test_connection_result(self, data):
        """
        Handle connection test result from node.

        Updates repository or source resource connection status.
        """
        resource_type = data.get('resource_type')  # 'repository' or 'source_resource'
        resource_id = data.get('resource_id')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_connection_status(resource_type, resource_id, success, error)

    async def handle_init_repo_result(self, data):
        """
        Handle repository initialization result from node.

        Updates repository Kopia status.
        """
        repository_id = data.get('repository_id')
        success = data.get('success', False)
        repo_id = data.get('repo_id')  # Kopia repository ID
        error = data.get('error')

        await self.update_repo_init_status(repository_id, success, repo_id, error)

    async def handle_mount_result(self, data):
        """
        Handle mount result from node.

        Updates mount status for gateway nodes.
        """
        repository_id = data.get('repository_id')
        success = data.get('success', False)
        mount_point = data.get('mount_point')
        error = data.get('error')

        await self.update_mount_status(repository_id, success, mount_point, error)

    # Send methods for group broadcasts
    async def node_message(self, event):
        """
        Handler for node message events.

        Sends messages to the node via WebSocket.
        """
        await self.send(text_data=json.dumps(event['data']))

    async def command_message(self, event):
        """
        Handler for command message events.

        Sends commands to the node via WebSocket.
        """
        await self.send(text_data=json.dumps(event['data']))

    # Database operations
    @sync_to_async
    def update_node_online_status(self, online):
        """
        Update node online status in database.
        """
        from .models import Node

        try:
            node = Node.objects.get(id=self.node_id)
            if online:
                node.status = Node.NodeStatus.ACTIVE
            else:
                node.status = Node.NodeStatus.INACTIVE
            node.save(update_fields=['status', 'updated_at'])
        except Node.DoesNotExist:
            pass

    @sync_to_async
    def update_node_heartbeat(self, data):
        """
        Update node heartbeat in database.

        Args:
            data: Heartbeat data dictionary
        """
        from .models import Node, NodeHeartbeat

        try:
            node = Node.objects.get(id=self.node_id)
            node.last_heartbeat = timezone.now()
            node.save(update_fields=['last_heartbeat', 'updated_at'])

            # Create heartbeat record
            NodeHeartbeat.objects.create(
                node=node,
                cpu_usage=data.get('cpu_usage'),
                memory_usage=data.get('memory_usage'),
                disk_usage=data.get('disk_usage'),
                network_in=data.get('network_in'),
                network_out=data.get('network_out'),
                active_tasks=data.get('active_tasks', 0),
                metadata=data.get('metadata', {})
            )
        except Node.DoesNotExist:
            pass

    @sync_to_async
    def get_pending_commands(self):
        """
        Get pending commands for the node.

        Returns:
            List of pending commands
        """
        # TODO: Implement command queue retrieval
        return []

    @sync_to_async
    def update_task_status(self, task_id, status, progress, result):
        """
        Update task status in database.
        """
        from backup_tasks.models import BackupTask

        try:
            task = BackupTask.objects.get(id=task_id)
            task.status = status
            task.progress = progress
            if result:
                task.result = result
            if status == BackupTask.STATUS_COMPLETED:
                task.completed_at = timezone.now()
            task.save()
        except BackupTask.DoesNotExist:
            pass

    @sync_to_async
    def store_log(self, level, message, metadata):
        """
        Store log message from node.
        """
        import logging
        logger = logging.getLogger('hyperfilelens.node')
        
        if level == 'error':
            logger.error(f"[Node {self.node_id}] {message}", extra=metadata)
        elif level == 'warning':
            logger.warning(f"[Node {self.node_id}] {message}", extra=metadata)
        else:
            logger.info(f"[Node {self.node_id}] {message}", extra=metadata)

    @sync_to_async
    def update_node_status(self, cpu_usage, memory_usage, disk_usage):
        """
        Update node status information.
        """
        from .models import Node

        try:
            node = Node.objects.get(id=self.node_id)
            if not node.metadata:
                node.metadata = {}
            node.metadata['last_status'] = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'timestamp': timezone.now().isoformat()
            }
            node.save(update_fields=['metadata', 'updated_at'])
        except Node.DoesNotExist:
            pass

    @sync_to_async
    def update_backup_task_result(self, task_id, success, snapshot_id, error, stats):
        """
        Update backup task result and create snapshot.
        """
        from backup_tasks.models import BackupTask, BackupSnapshot

        try:
            task = BackupTask.objects.get(id=task_id)
            
            if success:
                task.status = BackupTask.STATUS_COMPLETED
                task.progress = 100
                
                # Create snapshot record
                BackupSnapshot.objects.create(
                    name=f'{task.name} - {timezone.now().strftime("%Y%m%d_%H%M%S")}',
                    task=task,
                    repository=task.target_repository,
                    storage_path=snapshot_id,
                    manifest_path='',
                    total_size=stats.get('total_size', 0),
                    file_count=stats.get('file_count', 0),
                    checksum=stats.get('checksum', '')
                )
            else:
                task.status = BackupTask.STATUS_FAILED
                task.error_message = error
            
            task.save()
        except BackupTask.DoesNotExist:
            pass

    @sync_to_async
    def update_recovery_task_result(self, task_id, success, error, stats):
        """
        Update recovery task result.
        """
        from recovery_tasks.models import RecoveryTask

        try:
            task = RecoveryTask.objects.get(id=task_id)
            
            if success:
                task.status = RecoveryTask.STATUS_COMPLETED
                task.progress = 100
                task.restored_files = stats.get('restored_files', 0)
                task.restored_size = stats.get('restored_size', 0)
            else:
                task.status = RecoveryTask.STATUS_FAILED
                task.error_message = error
            
            task.save()
        except RecoveryTask.DoesNotExist:
            pass

    @sync_to_async
    def update_connection_status(self, resource_type, resource_id, success, error):
        """
        Update connection status for repository or source resource.
        """
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

    @sync_to_async
    def update_repo_init_status(self, repository_id, success, repo_id, error):
        """
        Update repository Kopia initialization status.
        """
        from repository.models import Repository

        try:
            repo = Repository.objects.get(id=repository_id)
            repo.kopia_initialized = success
            if success:
                repo.kopia_repository_id = repo_id
                repo.status = Repository.STATUS_ACTIVE
            else:
                repo.connection_error = error
            repo.save()
        except Repository.DoesNotExist:
            pass

    @sync_to_async
    def update_mount_status(self, repository_id, success, mount_point, error):
        """
        Update mount status for gateway nodes.
        """
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


class TaskConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for task execution.

    Handles real-time task progress and result streaming.
    """

    async def connect(self):
        """
        Handle WebSocket connection for task.
        """
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
        """
        Handle WebSocket disconnection.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming messages.
        """
        pass

    async def task_progress(self, event):
        """
        Handler for task progress events.

        Sends progress updates to connected clients.
        """
        await self.send(text_data=json.dumps(event['data']))

    async def task_result(self, event):
        """
        Handler for task result events.

        Sends final results to connected clients.
        """
        await self.send(text_data=json.dumps(event['data']))

    @sync_to_async
    def get_task_status(self):
        """
        Get current task status.
        """
        from backup_tasks.models import BackupTask

        try:
            task = BackupTask.objects.get(id=self.task_id)
            return {
                'task_id': str(task.id),
                'name': task.name,
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }
        except BackupTask.DoesNotExist:
            return {'error': 'Task not found'}


class StatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system status streaming.

    Provides real-time system status updates to administrators.
    """

    async def connect(self):
        """
        Handle WebSocket connection.
        """
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
        """
        Handle WebSocket disconnection.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming messages.
        """
        pass

    async def status_update(self, event):
        """
        Handler for status update events.

        Sends status updates to connected clients.
        """
        await self.send(text_data=json.dumps(event['data']))

    @sync_to_async
    def get_system_status(self):
        """
        Get current system status.

        Returns:
            Dictionary with system status information
        """
        from .models import Node
        from backup_tasks.models import BackupTask
        from repository.models import Repository

        total_nodes = Node.objects.count()
        online_nodes = Node.objects.filter(
            last_heartbeat__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()

        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'offline_nodes': total_nodes - online_nodes,
            'total_backup_tasks': BackupTask.objects.count(),
            'running_tasks': BackupTask.objects.filter(status=BackupTask.STATUS_RUNNING).count(),
            'total_repositories': Repository.objects.count(),
            'server_time': timezone.now().isoformat()
        }


# Utility functions for sending commands to nodes
async def send_backup_command(node_id, task_data):
    """
    Send backup command to a node.

    Args:
        node_id: Target node ID
        task_data: Backup task data including:
            - task_id: Backup task ID
            - source_path: Path to backup
            - repo_config: Repository configuration
            - exclude_patterns: Patterns to exclude
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'node_{node_id}',
        {
            'type': 'command_message',
            'data': {
                'type': 'backup',
                'payload': task_data
            }
        }
    )


async def send_restore_command(node_id, task_data):
    """
    Send restore command to a node.

    Args:
        node_id: Target node ID
        task_data: Restore task data including:
            - task_id: Recovery task ID
            - snapshot_id: Snapshot to restore from
            - target_path: Path to restore to
            - repo_config: Repository configuration
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'node_{node_id}',
        {
            'type': 'command_message',
            'data': {
                'type': 'restore',
                'payload': task_data
            }
        }
    )


async def send_test_connection_command(node_id, resource_type, resource_id, config):
    """
    Send test connection command to a node.

    Args:
        node_id: Target node ID
        resource_type: 'repository' or 'source_resource'
        resource_id: Resource ID
        config: Connection configuration
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'node_{node_id}',
        {
            'type': 'command_message',
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


async def send_init_repo_command(node_id, repository_id, config):
    """
    Send initialize repository command to a node.

    Args:
        node_id: Target node ID
        repository_id: Repository ID
        config: Repository configuration including credentials
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'node_{node_id}',
        {
            'type': 'command_message',
            'data': {
                'type': 'init_repo',
                'payload': {
                    'repository_id': str(repository_id),
                    'config': config
                }
            }
        }
    )
