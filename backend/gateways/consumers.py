"""
WebSocket Consumers for Gateway Nodes

This module provides WebSocket consumers for real-time
gateway communication, Kopia operations, and AI insights.
"""

import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async
from audit_log.services import AuditService


class GatewayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for gateway connections.

    Handles real-time communication with gateway nodes for:
    - Registration and heartbeats
    - Kopia mount operations
    - AI insights queries
    - Monitoring data reporting
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        Authenticates the gateway and establishes the connection.
        """
        self.gateway_id = self.scope['url_route']['kwargs']['gateway_id']
        self.room_group_name = f'gateway_{self.gateway_id}'

        # Verify gateway credentials
        valid = await self.verify_gateway()
        if not valid:
            await self.close(code=4001)
            return

        # Join gateway group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Update gateway connection status
        await self.update_gateway_online_status(True)

        # Send connection acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'gateway_id': self.gateway_id,
            'server_time': timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Cleans up connection state and updates gateway status.
        """
        # Leave gateway group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Update gateway connection status
        await self.update_gateway_online_status(False)

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.

        Processes commands from the gateway and responds accordingly.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            handlers = {
                'heartbeat': self.handle_heartbeat,
                'register': self.handle_register,
                'metrics': self.handle_metrics,
                'task_update': self.handle_task_update,
                'task_result': self.handle_task_result,
                'mount_result': self.handle_mount_result,
                'unmount_result': self.handle_unmount_result,
                'snapshot_mount_result': self.handle_snapshot_mount_result,
                'server_status': self.handle_server_status,
                'server_start_result': self.handle_server_start_result,
                'server_stop_result': self.handle_server_stop_result,
                'kopia_command_result': self.handle_kopia_command_result,
                'capabilities': self.handle_capabilities,
                'index_status': self.handle_index_status,
                'index_progress': self.handle_index_progress,
                'index_batch': self.handle_index_batch,
                'index_completed': self.handle_index_completed,
                'index_failed': self.handle_index_failed,
                'ai_query_result': self.handle_ai_query_result,
                'ai_summary_progress': self.handle_ai_summary_progress,
                'ai_summary_result': self.handle_ai_summary_result,
                'ai_summary_failed': self.handle_ai_summary_failed,
                'stats_report': self.handle_stats_report,
                'error': self.handle_error,
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

    # ==================== Registration & Heartbeat ====================

    async def handle_register(self, data):
        """
        Handle initial registration message from gateway.
        
        Expected data:
        {
            'type': 'register',
            'install_token': 'token from install command',
            'gateway_info': {
                'hostname': 'gateway-host',
                'ip_address': '192.168.1.100',
                'version': '1.0.0',
                'os': 'Ubuntu 22.04',
                'capabilities': ['mount', 'ai_query', 'index'],
                'kopia_version': '0.15.0',
                'cpu_cores': 8,
                'memory_gb': 16,
                'disk_gb': 500
            }
        }
        """
        install_token = data.get('install_token')
        gateway_info = data.get('gateway_info', {})

        result = await self.complete_registration(install_token, gateway_info)

        if result.get('success'):
            await self.send(text_data=json.dumps({
                'type': 'register_ack',
                'status': 'success',
                'gateway_id': self.gateway_id,
                'api_token': result.get('api_token'),
                'install_token_used': True,
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'register_ack',
                'status': 'failed',
                'message': result.get('message') or 'Invalid install token or gateway already registered'
            }))

    async def handle_heartbeat(self, data):
        """
        Handle heartbeat message from gateway.

        Updates gateway status and responds with any pending commands.
        """
        metrics = data.get('metrics', {})
        mounts = data.get('mounts', [])
        
        await self.update_gateway_heartbeat(metrics, mounts)

        # Check for pending tasks
        pending_tasks = await self.get_pending_tasks()

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'server_time': timezone.now().isoformat(),
            'pending_tasks': pending_tasks
        }))

    async def handle_metrics(self, data):
        """
        Handle detailed metrics report from gateway.
        
        Expected data:
        {
            'type': 'metrics',
            'metrics': {
                'cpu_usage': 45.2,
                'memory_usage': 60.5,
                'disk_usage': 30.1,
                'network_in': 1024000,
                'network_out': 512000,
                'mount_count': 3,
                'active_mounts': ['snapshot-1', 'snapshot-2'],
                'index_count': 15000,
                'ai_queries_per_hour': 25
            }
        }
        """
        metrics = data.get('metrics', {})
        await self.store_gateway_metrics(metrics)

        await self.send(text_data=json.dumps({
            'type': 'metrics_ack',
            'server_time': timezone.now().isoformat()
        }))

    async def handle_capabilities(self, data):
        """
        Handle capabilities report from gateway.
        
        Expected data:
        {
            'type': 'capabilities',
            'capabilities': {
                'mount': True,
                'ai_query': True,
                'index': True,
                'kopia_server': True,
                'supported_storage': ['nas', 's3', 'local']
            }
        }
        """
        capabilities = data.get('capabilities', {})
        await self.update_gateway_capabilities(capabilities)

        await self.send(text_data=json.dumps({
            'type': 'capabilities_ack',
            'server_time': timezone.now().isoformat()
        }))

    # ==================== Kopia Mount Operations ====================

    async def handle_mount_result(self, data):
        """
        Handle mount result from gateway.
        
        Expected data:
        {
            'type': 'mount_result',
            'task_id': 'uuid',
            'repository_id': 'uuid',
            'mount_point': '/mnt/kopia/repo-1',
            'success': True,
            'error': None
        }
        """
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        mount_point = data.get('mount_point')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_mount_status(repository_id, mount_point, success, error)
        
        # Broadcast to task group
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'mount',
                    'success': success,
                    'result': {
                        'repository_id': repository_id,
                        'mount_point': mount_point
                    },
                    'error': error
                }
            }
        )

    async def handle_unmount_result(self, data):
        """
        Handle unmount result from gateway.
        
        Expected data:
        {
            'type': 'unmount_result',
            'task_id': 'uuid',
            'repository_id': 'uuid',
            'success': True,
            'error': None
        }
        """
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_unmount_status(repository_id, success, error)
        
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'unmount',
                    'success': success,
                    'result': {'repository_id': repository_id},
                    'error': error
                }
            }
        )

    async def handle_snapshot_mount_result(self, data):
        """
        Handle snapshot mount result from gateway.
        
        Expected data:
        {
            'type': 'snapshot_mount_result',
            'task_id': 'uuid',
            'snapshot_id': 'uuid',
            'mount_point': '/mnt/kopia/snapshot-1',
            'success': True,
            'error': None
        }
        """
        task_id = data.get('task_id')
        snapshot_id = data.get('snapshot_id')
        mount_point = data.get('mount_point')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_snapshot_mount_status(snapshot_id, mount_point, success, error)
        
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'snapshot_mount',
                    'success': success,
                    'result': {
                        'snapshot_id': snapshot_id,
                        'mount_point': mount_point
                    },
                    'error': error
                }
            }
        )

    # ==================== Kopia Server Operations ====================

    async def handle_server_status(self, data):
        """
        Handle Kopia server status report from gateway.
        
        Expected data:
        {
            'type': 'server_status',
            'status': 'running',
            'port': 51515,
            'tls': True,
            'connected_clients': 2
        }
        """
        status = data.get('status')
        port = data.get('port')
        tls = data.get('tls', True)
        connected_clients = data.get('connected_clients', 0)

        await self.update_server_status(status, port, tls, connected_clients)

    async def handle_server_start_result(self, data):
        """
        Handle Kopia server start result from gateway.
        
        Expected data:
        {
            'type': 'server_start_result',
            'task_id': 'uuid',
            'success': True,
            'port': 51515,
            'error': None
        }
        """
        task_id = data.get('task_id')
        success = data.get('success', False)
        port = data.get('port')
        error = data.get('error')

        await self.update_server_running(True, port)
        
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'server_start',
                    'success': success,
                    'result': {'port': port},
                    'error': error
                }
            }
        )

    async def handle_server_stop_result(self, data):
        """
        Handle Kopia server stop result from gateway.
        
        Expected data:
        {
            'type': 'server_stop_result',
            'task_id': 'uuid',
            'success': True,
            'error': None
        }
        """
        task_id = data.get('task_id')
        success = data.get('success', False)
        error = data.get('error')

        await self.update_server_running(False)
        
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'server_stop',
                    'success': success,
                    'result': {},
                    'error': error
                }
            }
        )

    # ==================== Kopia Commands ====================

    async def handle_kopia_command_result(self, data):
        """
        Handle Kopia command execution result from gateway.
        
        Expected data:
        {
            'type': 'kopia_command_result',
            'task_id': 'uuid',
            'command': 'snapshot list',
            'success': True,
            'output': '...',
            'error': None
        }
        """
        task_id = data.get('task_id')
        command = data.get('command')
        success = data.get('success', False)
        output = data.get('output')
        error = data.get('error')

        await self.store_command_result(task_id, command, success, output, error)
        
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'kopia_command',
                    'success': success,
                    'result': {
                        'command': command,
                        'output': output
                    },
                    'error': error
                }
            }
        )

    # ==================== Indexing & AI ====================

    async def handle_index_status(self, data):
        """
        Handle file index status report from gateway.
        
        Expected data:
        {
            'type': 'index_status',
            'status': 'indexing',
            'total_files': 100000,
            'indexed_files': 50000,
            'progress': 50.0
        }
        """
        status = data.get('status')
        total_files = data.get('total_files', 0)
        indexed_files = data.get('indexed_files', 0)
        progress = data.get('progress', 0)

        await self.update_index_status(status, total_files, indexed_files, progress)

    async def handle_ai_query_result(self, data):
        """
        Handle AI query result from gateway.
        
        Expected data:
        {
            'type': 'ai_query_result',
            'task_id': 'uuid',
            'success': True,
            'result': {
                'answer': '...',
                'sources': [...],
                'confidence': 0.95
            },
            'error': None
        }
        """
        task_id = data.get('task_id')
        success = data.get('success', False)
        result = data.get('result', {})
        error = data.get('error')

        await self.store_ai_query_result(task_id, success, result, error)
        await self.channel_layer.group_send(
            f'task_{task_id}',
            {
                'type': 'task_result',
                'data': {
                    'task_id': task_id,
                    'task_type': 'ai_query',
                    'success': success,
                    'result': result,
                    'error': error
                }
            }
        )

    async def handle_ai_summary_progress(self, data):
        await self.update_ai_summary_progress(data)

    async def handle_ai_summary_result(self, data):
        await self.complete_ai_summary_job(data)

    async def handle_ai_summary_failed(self, data):
        await self.fail_ai_summary_job(data)

    # ==================== Statistics ====================

    async def handle_stats_report(self, data):
        """
        Handle statistics report from gateway.
        
        Expected data:
        {
            'type': 'stats_report',
            'stats': {
                'total_mounts': 10,
                'total_queries': 1500,
                'total_files_indexed': 50000,
                'storage_used_gb': 120.5
            }
        }
        """
        stats = data.get('stats', {})
        await self.store_gateway_stats(stats)

    # ==================== Task Management ====================

    async def handle_task_update(self, data):
        """
        Handle task update message from gateway.
        """
        task_id = data.get('task_id')
        status = data.get('status')
        progress = data.get('progress', 0)
        message = data.get('message', '')

        await self.update_task_status(task_id, status, progress, message)

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
        Handle task result message from gateway.
        """
        task_id = data.get('task_id')
        task_type = data.get('task_type')
        success = data.get('success', False)
        result = data.get('result', {})
        error = data.get('error')

        await self.complete_task(task_id, success, result, error)

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

    async def handle_error(self, data):
        """
        Handle error message from gateway.
        """
        error_code = data.get('error_code')
        error_message = data.get('error_message')
        context = data.get('context', {})

        await self.store_gateway_error(error_code, error_message, context)

    async def handle_index_progress(self, data):
        await self.update_index_progress(data)

    async def handle_index_batch(self, data):
        await self.save_index_batch(data)

    async def handle_index_completed(self, data):
        await self.complete_index_job(data)

    async def handle_index_failed(self, data):
        await self.fail_index_job(data)

    # ==================== Channel Layer Methods ====================

    async def send_command(self, event):
        """
        Send a command to the gateway via WebSocket.
        """
        await self.send(text_data=json.dumps(event['data']))

    # ==================== Database Operations ====================

    @database_sync_to_async
    def verify_gateway(self):
        """Verify gateway exists and is valid."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            auth_header = ''
            for name, value in self.scope.get('headers', []):
                if name == b'authorization':
                    auth_header = value.decode()
                    break
            api_token = auth_header[6:].strip() if auth_header.startswith('Token ') else ''

            if gateway.install_token_used:
                return bool(api_token and api_token == gateway.api_token)
            if api_token:
                return api_token == gateway.api_token
            return True
        except Gateway.DoesNotExist:
            return False

    @database_sync_to_async
    def update_gateway_online_status(self, online):
        """Update gateway online status."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.status = Gateway.GatewayStatus.ACTIVE if online else Gateway.GatewayStatus.OFFLINE
            gateway.last_heartbeat = timezone.now()
            gateway.save(update_fields=['status', 'last_heartbeat'])
            
            # Audit log
            if online:
                AuditService.log_gateway_online(gateway)
            else:
                AuditService.log_gateway_offline(gateway)
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def complete_registration(self, install_token, gateway_info):
        """Complete gateway registration."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)

            # Treat repeated registration from an authenticated, already
            # registered gateway as idempotent.
            already_registered = gateway.install_token_used and not gateway.install_token
            if already_registered:
                gateway.hostname = gateway_info.get('hostname', gateway.hostname)
                gateway.internal_ip = gateway_info.get('ip_address') or gateway.internal_ip
                gateway.version = gateway_info.get('version', gateway.version)
                gateway.os_version = gateway_info.get('os', gateway.os_version)
                gateway.capabilities = gateway_info.get('capabilities', gateway.capabilities)
                gateway.kopia_version = gateway_info.get('kopia_version', gateway.kopia_version)
                gateway.status = Gateway.GatewayStatus.ACTIVE
                gateway.last_heartbeat = timezone.now()
                gateway.save(update_fields=[
                    'hostname', 'internal_ip', 'version', 'os_version',
                    'capabilities', 'kopia_version', 'status',
                    'last_heartbeat', 'updated_at',
                ])
                return {'success': True, 'api_token': gateway.api_token}
            
            # Verify install token
            if not install_token or gateway.install_token != install_token:
                return {'success': False, 'message': 'Invalid install token'}
            
            # Update gateway info
            gateway.hostname = gateway_info.get('hostname', gateway.hostname)
            gateway.internal_ip = gateway_info.get('ip_address') or gateway.internal_ip
            gateway.version = gateway_info.get('version', '')
            gateway.os_version = gateway_info.get('os', 'Linux')
            gateway.capabilities = gateway_info.get('capabilities', [])
            gateway.kopia_version = gateway_info.get('kopia_version', '')
            gateway.cpu_cores = gateway_info.get('cpu_cores', 0)
            gateway.memory_total = int(float(gateway_info.get('memory_gb') or 0) * 1024 * 1024 * 1024)
            gateway.disk_total = int(float(gateway_info.get('disk_gb') or 0) * 1024 * 1024 * 1024)
            gateway.status = Gateway.GatewayStatus.ACTIVE
            if not gateway.api_token:
                gateway.generate_api_token()
            gateway.install_token = ''
            gateway.install_token_used = True
            gateway.registered_at = timezone.now()
            gateway.installed_at = gateway.installed_at or gateway.registered_at
            gateway.save()
            
            # Audit log
            AuditService.log_gateway_register(gateway)
            return {'success': True, 'api_token': gateway.api_token}
        except Gateway.DoesNotExist:
            return {'success': False, 'message': 'Gateway not found'}

    @database_sync_to_async
    def update_gateway_heartbeat(self, metrics, mounts):
        """Update gateway heartbeat data."""
        from gateways.models import Gateway, GatewayHeartbeat
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.last_heartbeat = timezone.now()
            
            # Update metrics
            if metrics:
                gateway.cpu_usage = metrics.get('cpu_usage', 0)
                gateway.memory_usage = metrics.get('memory_usage', 0)
                gateway.disk_usage = metrics.get('disk_usage', 0)
                gateway.network_bytes_sent = metrics.get('network_bytes_sent', gateway.network_bytes_sent)
                gateway.network_bytes_recv = metrics.get('network_bytes_recv', gateway.network_bytes_recv)
                gateway.cpu_cores = metrics.get('cpu_cores') or gateway.cpu_cores
                gateway.memory_total = metrics.get('memory_total') or gateway.memory_total
                gateway.disk_total = metrics.get('disk_total') or gateway.disk_total
            gateway.active_mounts = len(mounts)
            
            gateway.save()
            
            # Store heartbeat history
            GatewayHeartbeat.objects.create(
                gateway=gateway,
                cpu_usage=metrics.get('cpu_usage', 0),
                memory_usage=metrics.get('memory_usage', 0),
                disk_usage=metrics.get('disk_usage', 0),
                active_mounts=len(mounts),
                network_bytes_sent=metrics.get('network_bytes_sent', 0),
                network_bytes_recv=metrics.get('network_bytes_recv', 0),
                load_average=metrics.get('load_average'),
                process_count=metrics.get('process_count')
            )
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def store_gateway_metrics(self, metrics):
        """Store detailed gateway metrics."""
        from gateways.models import Gateway, GatewayHeartbeat
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            
            gateway.cpu_usage = metrics.get('cpu_usage', 0)
            gateway.memory_usage = metrics.get('memory_usage', 0)
            gateway.disk_usage = metrics.get('disk_usage', 0)
            gateway.active_mounts = metrics.get('mount_count', metrics.get('active_mounts', 0))
            gateway.network_bytes_sent = metrics.get('network_bytes_sent', gateway.network_bytes_sent)
            gateway.network_bytes_recv = metrics.get('network_bytes_recv', gateway.network_bytes_recv)
            gateway.cpu_cores = metrics.get('cpu_cores') or gateway.cpu_cores
            gateway.memory_total = metrics.get('memory_total') or gateway.memory_total
            gateway.disk_total = metrics.get('disk_total') or gateway.disk_total
            gateway.save()
            
            GatewayHeartbeat.objects.create(
                gateway=gateway,
                cpu_usage=metrics.get('cpu_usage', 0),
                memory_usage=metrics.get('memory_usage', 0),
                disk_usage=metrics.get('disk_usage', 0),
                active_mounts=metrics.get('mount_count', metrics.get('active_mounts', 0)),
                network_bytes_sent=metrics.get('network_bytes_sent', 0),
                network_bytes_recv=metrics.get('network_bytes_recv', 0),
                load_average=metrics.get('load_average'),
                process_count=metrics.get('process_count')
            )
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def update_gateway_capabilities(self, capabilities):
        """Update gateway capabilities."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.capabilities = capabilities
            gateway.save(update_fields=['capabilities'])
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def update_mount_status(self, repository_id, mount_point, success, error):
        """Update mount status."""
        from repository.models import Repository
        try:
            repo = Repository.objects.get(id=repository_id)
            repo.mount_point = mount_point if success else ''
            repo.mount_status = 'mounted' if success else 'error'
            repo.mount_error = error or ''
            repo.save()
            
            # Audit log
            if success:
                AuditService.log_gateway_mount(repo, mount_point)
            else:
                AuditService.log_gateway_mount_failed(repo, error)
        except Repository.DoesNotExist:
            pass

    @database_sync_to_async
    def update_unmount_status(self, repository_id, success, error):
        """Update unmount status."""
        from repository.models import Repository
        try:
            repo = Repository.objects.get(id=repository_id)
            repo.mount_point = ''
            repo.mount_status = 'unmounted' if success else 'error'
            repo.save()
            
            if success:
                AuditService.log_gateway_unmount(repo)
        except Repository.DoesNotExist:
            pass

    @database_sync_to_async
    def update_snapshot_mount_status(self, snapshot_id, mount_point, success, error):
        """Update snapshot mount status."""
        # TODO: Implement when snapshot model is available
        pass

    @database_sync_to_async
    def update_server_status(self, status, port, tls, connected_clients):
        """Update Kopia server status."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.kopia_server_status = status
            gateway.kopia_server_port = port
            gateway.kopia_server_tls = tls
            gateway.save()
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def update_server_running(self, running, port=None):
        """Update server running status."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.kopia_server_status = 'running' if running else 'stopped'
            if port:
                gateway.kopia_server_port = port
            gateway.save()
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def store_command_result(self, task_id, command, success, output, error):
        """Store Kopia command result."""
        # TODO: Implement command result storage
        pass

    @database_sync_to_async
    def update_index_status(self, status, total_files, indexed_files, progress):
        """Update file index status."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            gateway.index_status = status
            gateway.index_total_files = total_files
            gateway.indexed_files = indexed_files
            gateway.save()
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def update_index_progress(self, data):
        from insights.services import update_index_progress
        update_index_progress(data.get('job_id'), data)

    @database_sync_to_async
    def save_index_batch(self, data):
        from insights.services import save_index_batch
        save_index_batch(data.get('job_id'), data.get('files') or [])

    @database_sync_to_async
    def complete_index_job(self, data):
        from insights.services import complete_index_job
        complete_index_job(data.get('job_id'), data)

    @database_sync_to_async
    def fail_index_job(self, data):
        from insights.services import fail_index_job
        fail_index_job(data.get('job_id'), data.get('error') or data.get('error_message'))

    @database_sync_to_async
    def update_ai_summary_progress(self, data):
        from insights.services import update_ai_job_progress
        update_ai_job_progress(data.get('job_id'), data)

    @database_sync_to_async
    def complete_ai_summary_job(self, data):
        from insights.services import complete_ai_summary_job
        complete_ai_summary_job(data.get('job_id'), data)

    @database_sync_to_async
    def fail_ai_summary_job(self, data):
        from insights.services import fail_ai_job
        fail_ai_job(data.get('job_id'), data.get('error') or data.get('error_message'))

    @database_sync_to_async
    def store_ai_query_result(self, task_id, success, result, error):
        """Store AI query result."""
        # TODO: Implement AI query result storage
        pass

    @database_sync_to_async
    def store_gateway_stats(self, stats):
        """Store gateway statistics."""
        from gateways.models import Gateway
        try:
            gateway = Gateway.objects.get(id=self.gateway_id)
            # Store stats as needed
            gateway.save()
        except Gateway.DoesNotExist:
            pass

    @database_sync_to_async
    def get_pending_tasks(self):
        """Get pending tasks for gateway."""
        # TODO: Implement task queue
        return []

    @database_sync_to_async
    def update_task_status(self, task_id, status, progress, message):
        """Update task status."""
        # TODO: Implement task status update
        pass

    @database_sync_to_async
    def complete_task(self, task_id, success, result, error):
        """Complete a task."""
        # TODO: Implement task completion
        pass

    @database_sync_to_async
    def store_gateway_error(self, error_code, error_message, context):
        """Store gateway error."""
        # TODO: Implement error storage
        pass


class TaskConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for task monitoring.
    Clients can connect to monitor task progress in real-time.
    """

    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'

        # Join task group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave task group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def task_progress(self, event):
        """Send task progress update to client."""
        await self.send(text_data=json.dumps({
            'type': 'task_progress',
            'data': event['data']
        }))

    async def task_result(self, event):
        """Send task result to client."""
        await self.send(text_data=json.dumps({
            'type': 'task_result',
            'data': event['data']
        }))


class StatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system status streaming.
    """

    async def connect(self):
        self.room_group_name = 'status'

        # Join status group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave status group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def status_update(self, event):
        """Send status update to client."""
        await self.send(text_data=json.dumps(event['data']))
