"""
WebSocket Consumers for Nodes Application

This module provides WebSocket consumers for real-time
node communication, task execution, and status updates.
"""

import json
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
        await self.update_node_connection_status('disconnected')

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

        await self.send(text_data=json.dumps({
            'type': 'task_update_ack',
            'task_id': task_id,
            'received_at': timezone.now().isoformat()
        }))

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
    def update_node_heartbeat(self, data):
        """
        Update node heartbeat in database.

        Args:
            data: Heartbeat data dictionary
        """
        from .models import Node, NodeHeartbeat

        try:
            node = Node.objects.get(node_id=self.node_id)
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
    def update_node_connection_status(self, status):
        """
        Update node connection status in database.

        Args:
            status: Connection status string
        """
        from .models import NodeConnection

        try:
            connection = NodeConnection.objects.filter(
                node_id=self.node_id,
                status='connected'
            ).first()
            if connection:
                connection.status = status
                connection.disconnected_at = timezone.now()
                connection.save()
        except Exception:
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

        Args:
            task_id: Task identifier
            status: New status
            progress: Progress percentage
            result: Task result data
        """
        from .models import NodeTaskAssignment

        try:
            assignment = NodeTaskAssignment.objects.get(task_id=task_id)
            assignment.status = status
            assignment.progress = progress
            if result:
                assignment.result = result
            if status == 'completed':
                assignment.completed_at = timezone.now()
            assignment.save()
        except NodeTaskAssignment.DoesNotExist:
            pass

    @sync_to_async
    def store_log(self, level, message, metadata):
        """
        Store log message from node.

        Args:
            level: Log level
            message: Log message
            metadata: Additional metadata
        """
        from audit_log.models import AuditLog

        try:
            AuditLog.objects.create(
                action=f'node_log_{level}',
                user=None,  # System log
                resource_type='node',
                resource_id=self.node_id,
                details={
                    'level': level,
                    'message': message,
                    'metadata': metadata
                }
            )
        except Exception:
            pass

    @sync_to_async
    def update_node_status(self, cpu_usage, memory_usage, disk_usage):
        """
        Update node status information.

        Args:
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
        """
        from .models import Node

        try:
            node = Node.objects.get(node_id=self.node_id)
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

        total_nodes = Node.objects.count()
        online_nodes = Node.objects.filter(
            last_heartbeat__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()

        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'offline_nodes': total_nodes - online_nodes,
            'server_time': timezone.now().isoformat()
        }
