"""Gateway WebSocket agent runtime."""

import asyncio
import json
import logging

try:
    import psutil
except ImportError:  # pragma: no cover - installer should provide psutil
    psutil = None

try:
    import websockets
except ImportError:  # pragma: no cover - installer should provide websockets
    websockets = None

from .ai import AIClient
from .config import GatewayConfig
from .kopia import KopiaClient
from .monitor import SystemMonitor
from .storage import RepositoryStorageManager

logger = logging.getLogger('gateway-agent')

class GatewayAgent:
    """
    Gateway Agent that connects to the control plane and handles commands.
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.gateway_id = config.gateway_id
        self.ws_url = config.websocket_url()
        
        # Components
        self.kopia = KopiaClient(config)
        self.storage = RepositoryStorageManager(config)
        self.monitor = SystemMonitor()
        self.ai = AIClient(config)
        
        # State
        self._connected = False
        self._registered = False
        self._running = False
        self._ws = None
        
    async def start(self):
        """Start the gateway agent."""
        logger.info(f"Starting Gateway Agent for {self.gateway_id}")
        logger.info(f"Connecting to {self.ws_url}")
        
        self._running = True
        
        # Main connection loop
        while self._running:
            try:
                await self._connect_and_run()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self._connected = False
            
            if self._running:
                logger.info(f"Reconnecting in {self.config.reconnect_delay} seconds...")
                await asyncio.sleep(self.config.reconnect_delay)
    
    async def stop(self):
        """Stop the gateway agent."""
        logger.info("Stopping Gateway Agent")
        self._running = False
        
        # Stop all mounts
        for mount_id in list(self.kopia._mounts.keys()):
            await self.kopia.unmount(mount_id)
        
        # Stop server
        await self.kopia.stop_server()
        
        # Close WebSocket
        if self._ws:
            await self._ws.close()
    
    async def _connect_and_run(self):
        """Connect to server and run message loop."""
        if websockets is None:
            raise ImportError("websockets library is required")
        
        async with websockets.connect(
            self.ws_url,
            extra_headers={'Authorization': f'Token {self.config.api_token}'}
        ) as ws:
            self._ws = ws
            self._connected = True
            logger.info("Connected to control plane")
            
            # Send registration if needed
            if self.config.install_token:
                await self._register()
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            try:
                # Message handling loop
                async for message in ws:
                    await self._handle_message(message)
            finally:
                heartbeat_task.cancel()
    
    async def _register(self):
        """Send registration message."""
        system_info = self.monitor.get_system_info()
        kopia_version = await self.kopia.get_version()
        
        registration = {
            'type': 'register',
            'install_token': self.config.install_token,
            'gateway_info': {
                'hostname': system_info['hostname'],
                'ip_address': self._get_local_ip(),
                'version': '1.0.0',
                'os': f"{system_info['os']} {system_info.get('os_version', '')}",
                'capabilities': ['mount', 'unmount', 'snapshot_mount', 'kopia_server', 
                               'kopia_command', 'index', 'ai_query'],
                'kopia_version': kopia_version or 'unknown',
                'cpu_cores': system_info.get('cpu_cores', 1),
                'memory_gb': system_info.get('memory_total_gb', 0),
                'disk_gb': system_info.get('disk_total_gb', 0)
            }
        }
        
        await self._ws.send(json.dumps(registration))
        logger.info("Sent registration")
    
    def _get_local_ip(self) -> str:
        """Get local IP address."""
        if psutil:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:  # IPv4
                        if not addr.address.startswith('127.'):
                            return addr.address
        return '0.0.0.0'
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._connected and self._running:
            try:
                metrics = self.monitor.get_metrics()
                mounts = await self.kopia.list_mounts()
                
                heartbeat = {
                    'type': 'heartbeat',
                    'metrics': {
                        'cpu_usage': metrics['cpu_usage'],
                        'memory_usage': metrics['memory_usage'],
                        'disk_usage': metrics['disk_usage'],
                        'mount_count': len(mounts),
                        'network_bytes_sent': metrics.get('network_bytes_sent', 0),
                        'network_bytes_recv': metrics.get('network_bytes_recv', 0),
                        'load_average': metrics.get('load_average'),
                        'process_count': metrics.get('process_count'),
                        'cpu_cores': metrics.get('cpu_cores'),
                        'cpu_physical': metrics.get('cpu_physical'),
                        'memory_total': metrics.get('memory_total'),
                        'memory_used': metrics.get('memory_used'),
                        'memory_free': metrics.get('memory_free'),
                        'disk_total': metrics.get('disk_total'),
                        'disk_used': metrics.get('disk_used'),
                        'disk_free': metrics.get('disk_free'),
                        'network_packets_sent': metrics.get('network_packets_sent'),
                        'network_packets_recv': metrics.get('network_packets_recv'),
                        'network_interfaces': metrics.get('network_interfaces'),
                        'disk_io': metrics.get('disk_io'),
                        'uptime': metrics.get('uptime'),
                    },
                    'mounts': [m['mount_point'] for m in mounts]
                }
                
                await self._ws.send(json.dumps(heartbeat))
                logger.info(
                    "Sent heartbeat cpu=%.1f%% memory=%.1f%% disk=%.1f%% mounts=%s interfaces=%s disk_io=%s",
                    metrics.get('cpu_usage') or 0,
                    metrics.get('memory_usage') or 0,
                    metrics.get('disk_usage') or 0,
                    len(mounts),
                    len((metrics.get('network_interfaces') or {}).get('interfaces') or []),
                    len(metrics.get('disk_io') or []),
                )
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            logger.debug(f"Received message: {msg_type}")
            
            handlers = {
                'connection_established': self._handle_connection_established,
                'register_ack': self._handle_register_ack,
                'heartbeat_ack': self._handle_heartbeat_ack,
                'mount': self._handle_mount,
                'unmount': self._handle_unmount,
                'snapshot_mount': self._handle_snapshot_mount,
                'server_start': self._handle_server_start,
                'server_stop': self._handle_server_stop,
                'server_status': self._handle_server_status,
                'kopia_command': self._handle_kopia_command,
                'list_mounts': self._handle_list_mounts,
                'init_repository': self._handle_init_repository,
                'connect_repository': self._handle_connect_repository,
                'index_snapshot': self._handle_index_snapshot,
                'index_start': self._handle_index_start,
                'index_stop': self._handle_index_stop,
                'ai_query': self._handle_ai_query,
                'ai_summarize_snapshot': self._handle_ai_summarize_snapshot,
                'system_info': self._handle_system_info,
            }
            
            handler = handlers.get(msg_type)
            if handler:
                await handler(data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    # ==================== Message Handlers ====================
    
    async def _handle_connection_established(self, data):
        """Handle connection acknowledgment."""
        logger.info(f"Connection established: {data.get('server_time')}")
    
    async def _handle_register_ack(self, data):
        """Handle registration acknowledgment."""
        if data.get('status') == 'success':
            self._registered = True
            api_token = data.get('api_token')
            if api_token:
                self.config.save_runtime_credentials(api_token=api_token, install_token='')
            else:
                self.config.save_runtime_credentials(install_token='')
            logger.info("Registration successful")
        else:
            logger.error(f"Registration failed: {data.get('message')}")
    
    async def _handle_heartbeat_ack(self, data):
        """Handle heartbeat acknowledgment."""
        pending_tasks = data.get('pending_tasks', [])
        if pending_tasks:
            logger.info(f"Pending tasks: {len(pending_tasks)}")
    
    async def _handle_mount(self, data):
        """Handle mount command."""
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        mount_point = data.get('mount_point')
        
        result = await self.kopia.mount_repository(repository_id, mount_point)
        
        response = {
            'type': 'mount_result',
            'task_id': task_id,
            'repository_id': repository_id,
            'mount_point': result.get('mount_point'),
            'success': result.get('status') == 'success',
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_unmount(self, data):
        """Handle unmount command."""
        task_id = data.get('task_id')
        mount_id = data.get('mount_id')
        repository_id = data.get('repository_id')
        
        # Find mount by repository_id if mount_id not provided
        if not mount_id:
            for mid, mount in self.kopia._mounts.items():
                if mount.repository_id == repository_id:
                    mount_id = mid
                    break
        
        result = await self.kopia.unmount(mount_id) if mount_id else {'status': 'error', 'message': 'Mount not found'}
        
        response = {
            'type': 'unmount_result',
            'task_id': task_id,
            'repository_id': repository_id,
            'success': result.get('status') == 'success',
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_snapshot_mount(self, data):
        """Handle snapshot mount command."""
        task_id = data.get('task_id')
        snapshot_id = data.get('snapshot_id')
        mount_point = data.get('mount_point')
        read_only = data.get('read_only', True)
        
        result = await self.kopia.mount_snapshot(snapshot_id, mount_point, read_only)
        
        response = {
            'type': 'snapshot_mount_result',
            'task_id': task_id,
            'snapshot_id': snapshot_id,
            'mount_point': result.get('mount_point'),
            'success': result.get('status') == 'success',
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_server_start(self, data):
        """Handle server start command."""
        task_id = data.get('task_id')
        port = data.get('port', 51515)
        password = data.get('password')
        tls = data.get('tls', True)
        
        result = await self.kopia.start_server(port, password, tls)
        
        response = {
            'type': 'server_start_result',
            'task_id': task_id,
            'success': result.get('status') in ['success', 'already_running'],
            'port': result.get('port', port),
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_server_stop(self, data):
        """Handle server stop command."""
        task_id = data.get('task_id')
        
        result = await self.kopia.stop_server()
        
        response = {
            'type': 'server_stop_result',
            'task_id': task_id,
            'success': result.get('status') in ['success', 'not_running'],
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_server_status(self, data):
        """Handle server status request."""
        status = self.kopia.get_server_status()
        
        response = {
            'type': 'server_status',
            **status
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_kopia_command(self, data):
        """Handle Kopia command execution."""
        task_id = data.get('task_id')
        command = data.get('command')
        args = data.get('args', [])
        
        result = await self.kopia.execute_command(command, args)
        
        response = {
            'type': 'kopia_command_result',
            'task_id': task_id,
            'command': command,
            'success': result.get('status') == 'success',
            'output': result.get('output'),
            'error': result.get('error') or result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_list_mounts(self, data):
        """Handle list mounts request."""
        task_id = data.get('task_id')
        
        mounts = await self.kopia.list_mounts()
        
        response = {
            'type': 'mount_list_result',
            'task_id': task_id,
            'mounts': mounts
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_init_repository(self, data):
        """Handle repository initialization."""
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        storage_path = data.get('storage_path')
        password = data.get('password')
        
        result = await self.kopia.init_repository(storage_path, password)
        
        response = {
            'type': 'init_repository_result',
            'task_id': task_id,
            'repository_id': repository_id,
            'success': result.get('status') == 'success',
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_connect_repository(self, data):
        """Handle repository connection."""
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        storage_path = data.get('storage_path')
        password = data.get('password')
        
        result = await self.kopia.connect_repository(storage_path, password)
        
        response = {
            'type': 'connect_repository_result',
            'task_id': task_id,
            'repository_id': repository_id,
            'success': result.get('status') == 'success',
            'error': result.get('message')
        }
        
        await self._ws.send(json.dumps(response))

    async def _handle_index_snapshot(self, data):
        """Handle snapshot indexing command."""
        task_id = data.get('task_id')
        job_id = data.get('job_id')
        object_id = data.get('object_id')
        repository = data.get('repository') or {}
        password = data.get('password') or ''

        async def send(message: dict):
            await self._ws.send(json.dumps(message))

        try:
            if not job_id or not object_id:
                raise ValueError('job_id and object_id are required')
            repository_access = await self.storage.prepare(repository)
            connect_result = await self.kopia.connect_repository_config(
                repository_access.repository,
                password,
            )
            if connect_result.get('status') != 'success':
                raise RuntimeError(connect_result.get('message') or 'repository connect failed')

            await send({
                'type': 'index_progress',
                'task_id': task_id,
                'job_id': job_id,
                'status': 'running',
                'progress': 1,
                'current_path': '/',
            })

            indexed_files = 0
            indexed_bytes = 0
            batch: list[dict] = []

            async def flush():
                nonlocal batch
                if not batch:
                    return
                await send({
                    'type': 'index_batch',
                    'task_id': task_id,
                    'job_id': job_id,
                    'files': batch,
                })
                batch = []

            async def walk(object_path: str, relative_path: str = ''):
                nonlocal indexed_files, indexed_bytes, batch
                entries = await self.kopia.list_object(object_path)
                for entry in entries:
                    name = entry['name']
                    child_relative = f"{relative_path.rstrip('/')}/{name}".strip('/')
                    extension = ''
                    if not entry.get('is_directory') and '.' in name:
                        extension = '.' + name.rsplit('.', 1)[-1].lower()
                    size = int(entry.get('size') or 0)
                    indexed_files += 1
                    indexed_bytes += size
                    batch.append({
                        'path': child_relative,
                        'name': name,
                        'extension': extension,
                        'size': size,
                        'modified_time': entry.get('modified_time'),
                        'is_directory': bool(entry.get('is_directory')),
                        'depth': child_relative.count('/'),
                    })
                    if len(batch) >= 500:
                        await flush()
                    if indexed_files % 1000 == 0:
                        await send({
                            'type': 'index_progress',
                            'task_id': task_id,
                            'job_id': job_id,
                            'status': 'running',
                            'progress': 50,
                            'indexed_files': indexed_files,
                            'indexed_bytes': indexed_bytes,
                            'current_path': child_relative,
                        })
                    if entry.get('is_directory'):
                        await walk(f"{object_path.rstrip('/')}/{name}", child_relative)

            await walk(object_id)
            await flush()
            await send({
                'type': 'index_completed',
                'task_id': task_id,
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'total_files': indexed_files,
                'indexed_files': indexed_files,
                'total_bytes': indexed_bytes,
                'indexed_bytes': indexed_bytes,
            })
        except Exception as e:
            logger.error(f"Snapshot indexing failed: {e}")
            await send({
                'type': 'index_failed',
                'task_id': task_id,
                'job_id': job_id,
                'error': str(e),
            })
    
    async def _handle_index_start(self, data):
        """Handle index start command."""
        task_id = data.get('task_id')
        repository_id = data.get('repository_id')
        paths = data.get('paths')
        
        # TODO: Implement indexing
        
        response = {
            'type': 'index_status',
            'status': 'started',
            'repository_id': repository_id
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_index_stop(self, data):
        """Handle index stop command."""
        # TODO: Implement indexing stop
        
        response = {
            'type': 'index_status',
            'status': 'stopped'
        }
        
        await self._ws.send(json.dumps(response))
    
    async def _handle_ai_query(self, data):
        """Handle AI query."""
        task_id = data.get('task_id')
        query_id = data.get('query_id')
        query = data.get('query')
        context = data.get('context') or {}
        repository = data.get('repository') or {}
        password = data.get('password') or ''
        provider_config = data.get('ai_provider_config') or {}

        try:
            if not query:
                raise ValueError('query is required')
            if repository and password:
                repository_access = await self.storage.prepare(repository)
                connect_result = await self.kopia.connect_repository_config(repository_access.repository, password)
                if connect_result.get('status') != 'success':
                    raise RuntimeError(connect_result.get('message') or 'repository connect failed')
                context['content_samples'] = await self._collect_query_content_samples(context)

            result = await self.ai.answer_query(query, context, 'zh-CN', provider_config)
            result['query_id'] = query_id
            result['candidate_count'] = context.get('candidate_count') or len(context.get('candidate_files') or [])
            response = {
                'type': 'ai_query_result',
                'task_id': task_id,
                'success': True,
                'result': result,
            }
        except Exception as e:
            logger.error(f"AI query failed: {e}")
            response = {
                'type': 'ai_query_result',
                'task_id': task_id,
                'success': False,
                'error': str(e),
                'result': {'query_id': query_id},
            }

        await self._ws.send(json.dumps(response))

    async def _collect_query_content_samples(self, context: dict) -> list[dict]:
        samples = []
        text_extensions = {
            '.txt', '.md', '.csv', '.json', '.yaml', '.yml', '.xml',
            '.html', '.css', '.scss', '.js', '.ts', '.py', '.go', '.sh',
            '.log', '.conf', '.ini',
        }
        for item in (context.get('candidate_files') or [])[:8]:
            extension = (item.get('extension') or '').lower()
            if extension and extension not in text_extensions:
                continue
            object_id = item.get('object_id')
            path = item.get('path')
            if not object_id or not path:
                continue
            text = await self.kopia.read_object_text(object_id, path, max_bytes=12000)
            if not text.strip():
                continue
            samples.append({
                'path': path,
                'snapshot_name': item.get('snapshot_name'),
                'repository_name': item.get('repository_name'),
                'text': text[:12000],
            })
            if len(samples) >= 5:
                break
        return samples

    async def _handle_ai_summarize_snapshot(self, data):
        """Handle snapshot AI summary."""
        task_id = data.get('task_id')
        job_id = data.get('job_id')
        snapshot_context = data.get('snapshot_context') or {}
        language = data.get('language') or 'zh-CN'
        provider_config = data.get('ai_provider_config') or {}
        repository = data.get('repository') or {}
        password = data.get('password') or ''
        try:
            await self._ws.send(json.dumps({
                'type': 'ai_summary_progress',
                'task_id': task_id,
                'job_id': job_id,
                'status': 'running',
                'progress': 20,
            }))
            if repository and password:
                repository_access = await self.storage.prepare(repository)
                connect_result = await self.kopia.connect_repository_config(repository_access.repository, password)
                if connect_result.get('status') != 'success':
                    raise RuntimeError(connect_result.get('message') or 'repository connect failed')
                snapshot_context['content_samples'] = await self._collect_query_content_samples(snapshot_context)
            result = await self.ai.summarize_snapshot(snapshot_context, language, provider_config)
            await self._ws.send(json.dumps({
                'type': 'ai_summary_result',
                'task_id': task_id,
                'job_id': job_id,
                'success': True,
                'result': result,
            }))
        except Exception as e:
            logger.error(f"AI summary failed: {e}")
            await self._ws.send(json.dumps({
                'type': 'ai_summary_failed',
                'task_id': task_id,
                'job_id': job_id,
                'error': str(e),
            }))
    
    async def _handle_system_info(self, data):
        """Handle system info request."""
        info = self.monitor.get_system_info()
        metrics = self.monitor.get_metrics()
        
        response = {
            'type': 'system_info_result',
            'system': info,
            'metrics': metrics
        }
        
        await self._ws.send(json.dumps(response))
