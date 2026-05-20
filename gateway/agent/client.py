"""
HyperFileLens Gateway Agent

A Python-based agent for Gateway nodes that:
1. Connects to the control plane via WebSocket
2. Handles Kopia mount operations
3. Manages Kopia server
4. Executes Kopia commands
5. Provides file indexing and AI query capabilities

Requirements:
- Python 3.10+
- websockets
- psutil
- kopia (installed separately)
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import uuid
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

try:
    import psutil
except ImportError:
    psutil = None

try:
    import websockets
except ImportError:
    websockets = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gateway-agent')


@dataclass
class GatewayConfig:
    """Gateway Agent configuration."""
    # Connection settings
    server_url: str = os.getenv('SERVER_URL', 'ws://localhost:8000')
    gateway_id: str = os.getenv('GATEWAY_ID', '')
    api_token: str = os.getenv('API_TOKEN', '')
    install_token: str = os.getenv('INSTALL_TOKEN', '')
    
    # WebSocket settings
    ws_protocol: str = os.getenv('WS_PROTOCOL', 'ws')
    reconnect_delay: int = int(os.getenv('RECONNECT_DELAY', '5'))
    heartbeat_interval: int = int(os.getenv('HEARTBEAT_INTERVAL', '10'))
    
    # Gateway info
    name: str = os.getenv('GATEWAY_NAME', 'gateway-01')
    hostname: str = platform.node()
    
    # Kopia settings
    kopia_path: str = os.getenv('KOPIA_PATH', '/usr/bin/kopia')
    mount_base_path: str = os.getenv('MOUNT_BASE_PATH', '/mnt/kopia')
    max_concurrent_mounts: int = int(os.getenv('MAX_MOUNTS', '10'))
    
    # Repository settings
    repo_path: str = os.getenv('REPO_PATH', '/var/lib/hyperfilelens/repository')
    repo_password: str = os.getenv('KOPIA_PASSWORD', '')

    # AI settings
    ai_enabled: bool = os.getenv('AI_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    ai_provider: str = os.getenv('AI_PROVIDER', 'local')
    ai_base_url: str = os.getenv('AI_BASE_URL', os.getenv('AI_API_URL', 'https://api.openai.com/v1'))
    ai_api_key: str = os.getenv('AI_API_KEY', '')
    ai_model: str = os.getenv('AI_MODEL', 'gpt-4.1-mini')
    ai_timeout: int = int(os.getenv('AI_TIMEOUT', '60'))
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', '/var/log/hyperfilelens/gateway.log')


@dataclass
class MountInfo:
    """Information about an active mount."""
    mount_id: str
    repository_id: str
    mount_point: str
    snapshot_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    process: Optional[subprocess.Popen] = None


class AIClient:
    """Gateway-side AI provider with a local fallback."""

    def __init__(self, config: GatewayConfig):
        self.config = config

    async def summarize_snapshot(self, snapshot_context: dict, language: str = 'zh-CN', provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        enabled = provider_config.get('enabled', self.config.ai_enabled)
        provider = provider_config.get('provider') or self.config.ai_provider
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        if enabled and api_key and provider in {'openai', 'openai_compatible'}:
            try:
                return await asyncio.to_thread(self._summarize_with_openai_compatible, snapshot_context, language, provider_config)
            except Exception as exc:
                logger.warning(f"AI provider failed, falling back to local summary: {exc}")
        return self._local_summary(snapshot_context, language)

    def _summarize_with_openai_compatible(self, snapshot_context: dict, language: str, provider_config: Optional[dict] = None) -> dict:
        provider_config = provider_config or {}
        prompt = self._build_prompt(snapshot_context, language)
        provider = provider_config.get('provider') or self.config.ai_provider
        base_url = provider_config.get('base_url') or self.config.ai_base_url
        api_key = provider_config.get('api_key') or self.config.ai_api_key
        model = provider_config.get('model') or self.config.ai_model
        timeout = int(provider_config.get('timeout') or self.config.ai_timeout)
        url = base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a backup data intelligence analyst. Return concise JSON only.',
                },
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.2,
            'response_format': {'type': 'json_object'},
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                **((provider_config.get('config') or {}).get('headers') or {}),
            },
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
        content = data['choices'][0]['message']['content']
        result = json.loads(content)
        result.setdefault('provider', provider)
        result.setdefault('model', model)
        return result

    def _build_prompt(self, snapshot_context: dict, language: str) -> str:
        compact = json.dumps(snapshot_context, ensure_ascii=False)[:24000]
        return f"""
Language: {language}

Analyze this backup snapshot using the structured rule insights below.
Return JSON with keys:
- title
- summary
- risk_level: info|warning|critical
- findings: array of {{title,severity,description,evidence}}
- recommended_actions: array of {{type,label,description}}
- related_paths: array of important paths

Snapshot context:
{compact}
"""

    def _local_summary(self, snapshot_context: dict, language: str) -> dict:
        insights = {item.get('type'): item for item in snapshot_context.get('insights', [])}
        snapshot = snapshot_context.get('snapshot', {})
        categories = (insights.get('file_categories') or {}).get('evidence', {}).get('categories', [])
        duplicate_groups = (insights.get('duplicates') or {}).get('evidence', {}).get('groups', [])
        cold = (insights.get('cold_data') or {}).get('evidence', {})
        growth = (insights.get('growth') or {}).get('evidence', {})
        top_category = categories[0] if categories else {}
        findings = []
        if top_category:
            findings.append({
                'title': 'Dominant file category',
                'severity': 'info',
                'description': f"{top_category.get('category')} is the largest category with {top_category.get('count')} files.",
                'evidence': top_category,
            })
        if duplicate_groups:
            findings.append({
                'title': 'Duplicate candidates detected',
                'severity': 'warning',
                'description': f"{len(duplicate_groups)} duplicate candidate groups were found by name and size.",
                'evidence': {'groups': duplicate_groups[:5]},
            })
        if cold.get('count'):
            findings.append({
                'title': 'Cold data exists',
                'severity': 'warning',
                'description': f"{cold.get('count')} files have not changed for more than {cold.get('days', 90)} days.",
                'evidence': cold,
            })
        risk_level = 'warning' if duplicate_groups or cold.get('count') else 'info'
        return {
            'title': 'AI snapshot summary',
            'summary': f"Snapshot {snapshot.get('name') or snapshot.get('id')} contains {snapshot.get('file_count') or 0} files. Rule insights were analyzed by the Gateway local AI fallback.",
            'risk_level': risk_level,
            'findings': findings,
            'recommended_actions': [
                {'type': 'review_duplicates', 'label': 'Review duplicate candidates', 'description': 'Validate duplicate groups before cleanup.'},
                {'type': 'review_cold_data', 'label': 'Review cold data', 'description': 'Consider archive policy for long-unmodified data.'},
            ],
            'related_paths': [
                path
                for group in duplicate_groups[:3]
                for path in (group.get('paths') or [])[:2]
            ],
            'provider': 'local',
            'model': 'rule-summary',
            'growth': growth,
        }


class KopiaClient:
    """Kopia CLI wrapper for Gateway operations."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.kopia_path = Path(config.kopia_path)
        self.repo_path = Path(config.repo_path)
        self.mount_base = Path(config.mount_base_path)
        
        # Active mounts
        self._mounts: dict[str, MountInfo] = {}
        
        # Kopia server process
        self._server_process: Optional[subprocess.Popen] = None
        self._server_status = 'stopped'
        self._server_port = 51515
        
    async def check_installed(self) -> bool:
        """Check if Kopia is installed."""
        return self.kopia_path.exists()
    
    async def get_version(self) -> Optional[str]:
        """Get Kopia version."""
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.kopia_path), 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                # Parse version from output
                output = stdout.decode()
                for line in output.split('\n'):
                    if 'kopia' in line.lower():
                        return line.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get Kopia version: {e}")
            return None
    
    # ==================== Repository Operations ====================
    
    async def init_repository(self, storage_path: str, password: str) -> dict:
        """
        Initialize a new Kopia repository.
        
        Args:
            storage_path: Path to storage location
            password: Repository password
            
        Returns:
            dict with status and details
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.kopia_path), 'repository', 'create', 'filesystem',
                f'--path={storage_path}',
                f'--password={password}',
                '--override-hostname=gateway',
                '--override-username=hfl',
                '--ignore-unknown-parameters',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Repository created at {storage_path}")
                return {'status': 'success', 'path': storage_path}
            else:
                error = stderr.decode()
                logger.error(f"Failed to create repository: {error}")
                return {'status': 'error', 'message': error}
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def connect_repository(self, storage_path: str, password: str) -> dict:
        """Connect to existing repository."""
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.kopia_path), 'repository', 'connect', 'filesystem',
                f'--path={storage_path}',
                f'--password={password}',
                '--override-hostname=gateway',
                '--override-username=hfl',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Connected to repository at {storage_path}")
                return {'status': 'success', 'path': storage_path}
            else:
                error = stderr.decode()
                logger.error(f"Failed to connect: {error}")
                return {'status': 'error', 'message': error}
        except Exception as e:
            logger.error(f"Error connecting to repository: {e}")
            return {'status': 'error', 'message': str(e)}

    async def connect_repository_config(self, repository: dict, password: str) -> dict:
        """Connect to a repository using the control-plane repository payload."""
        repo_type = (repository or {}).get('type', 'filesystem')
        try:
            if repo_type == 's3':
                endpoint = (repository.get('endpoint') or '').replace('http://', '').replace('https://', '').rstrip('/')
                args = [
                    str(self.kopia_path), 'repository', 'connect', 's3',
                    '--bucket', repository.get('bucket', ''),
                    '--password', password,
                    '--endpoint', endpoint,
                    '--region', repository.get('region') or 'us-east-1',
                    '--access-key', repository.get('access_key', ''),
                    '--secret-access-key', repository.get('secret_key', ''),
                ]
                if repository.get('prefix'):
                    args.extend(['--prefix', repository.get('prefix')])
                if repository.get('use_tls') is False:
                    args.append('--disable-tls')
            else:
                storage_path = repository.get('path') or repository.get('url') or self.config.repo_path
                if storage_path.startswith('file://'):
                    storage_path = urlparse(storage_path).path
                args = [
                    str(self.kopia_path), 'repository', 'connect', 'filesystem',
                    f'--path={storage_path}',
                    f'--password={password}',
                    '--override-hostname=gateway',
                    '--override-username=hfl',
                ]

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            output = (stdout + stderr).decode()
            if proc.returncode == 0 or 'already connected' in output.lower():
                return {'status': 'success'}
            return {'status': 'error', 'message': output}
        except Exception as e:
            logger.error(f"Error connecting repository config: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # ==================== Mount Operations ====================
    
    async def mount_repository(self, repository_id: str, mount_point: str = None) -> dict:
        """
        Mount a Kopia repository for file access.
        
        Args:
            repository_id: Repository identifier
            mount_point: Custom mount point (optional)
            
        Returns:
            dict with status and mount info
        """
        if not mount_point:
            mount_point = str(self.mount_base / repository_id)
        
        # Create mount point
        Path(mount_point).mkdir(parents=True, exist_ok=True)
        
        try:
            # Mount the repository
            proc = await asyncio.create_subprocess_exec(
                str(self.kopia_path), 'mount',
                mount_point,
                '--fuse',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a bit for mount to complete
            await asyncio.sleep(2)
            
            if proc.returncode is None:
                # Process is still running = mount successful
                mount_id = str(uuid.uuid4())
                self._mounts[mount_id] = MountInfo(
                    mount_id=mount_id,
                    repository_id=repository_id,
                    mount_point=mount_point,
                    process=proc
                )
                logger.info(f"Mounted repository {repository_id} at {mount_point}")
                return {
                    'status': 'success',
                    'mount_id': mount_id,
                    'mount_point': mount_point
                }
            else:
                _, stderr = await proc.communicate()
                error = stderr.decode()
                logger.error(f"Failed to mount: {error}")
                return {'status': 'error', 'message': error}
                
        except Exception as e:
            logger.error(f"Error mounting repository: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def mount_snapshot(self, snapshot_id: str, mount_point: str = None,
                            read_only: bool = True) -> dict:
        """
        Mount a specific snapshot.
        
        Args:
            snapshot_id: Snapshot identifier
            mount_point: Custom mount point (optional)
            read_only: Mount as read-only
            
        Returns:
            dict with status and mount info
        """
        if not mount_point:
            mount_point = str(self.mount_base / 'snapshots' / snapshot_id)
        
        Path(mount_point).mkdir(parents=True, exist_ok=True)
        
        try:
            args = [str(self.kopia_path), 'mount', mount_point]
            if snapshot_id:
                args.append(f'--snapshot-id={snapshot_id}')
            args.append('--fuse')
            
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.sleep(2)
            
            if proc.returncode is None:
                mount_id = str(uuid.uuid4())
                self._mounts[mount_id] = MountInfo(
                    mount_id=mount_id,
                    repository_id='',
                    mount_point=mount_point,
                    snapshot_id=snapshot_id,
                    process=proc
                )
                logger.info(f"Mounted snapshot {snapshot_id} at {mount_point}")
                return {
                    'status': 'success',
                    'mount_id': mount_id,
                    'mount_point': mount_point
                }
            else:
                _, stderr = await proc.communicate()
                error = stderr.decode()
                logger.error(f"Failed to mount snapshot: {error}")
                return {'status': 'error', 'message': error}
                
        except Exception as e:
            logger.error(f"Error mounting snapshot: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def unmount(self, mount_id: str) -> dict:
        """
        Unmount a repository or snapshot.
        
        Args:
            mount_id: Mount identifier
            
        Returns:
            dict with status
        """
        if mount_id not in self._mounts:
            return {'status': 'error', 'message': 'Mount not found'}
        
        mount_info = self._mounts[mount_id]
        
        try:
            # Try graceful unmount first
            if mount_info.process and mount_info.process.returncode is None:
                mount_info.process.terminate()
                try:
                    await asyncio.wait_for(mount_info.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    mount_info.process.kill()
                    await mount_info.process.wait()
            
            # Try fusermount -u as fallback
            proc = await asyncio.create_subprocess_exec(
                'fusermount', '-u', mount_info.mount_point,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            del self._mounts[mount_id]
            logger.info(f"Unmounted {mount_info.mount_point}")
            
            return {'status': 'success'}
            
        except Exception as e:
            logger.error(f"Error unmounting: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def list_mounts(self) -> list:
        """List all active mounts."""
        return [
            {
                'mount_id': m.mount_id,
                'repository_id': m.repository_id,
                'snapshot_id': m.snapshot_id,
                'mount_point': m.mount_point,
                'created_at': m.created_at.isoformat()
            }
            for m in self._mounts.values()
        ]
    
    # ==================== Server Operations ====================
    
    async def start_server(self, port: int = 51515, password: str = None,
                          tls: bool = True) -> dict:
        """
        Start Kopia server for remote access.
        
        Args:
            port: Server port
            password: Server password
            tls: Enable TLS
            
        Returns:
            dict with status
        """
        if self._server_status == 'running':
            return {'status': 'already_running', 'port': self._server_port}
        
        try:
            args = [
                str(self.kopia_path), 'server', 'start',
                f'--address=0.0.0.0:{port}',
                '--server-control-username=kopia-control',
            ]
            
            if password:
                args.append(f'--server-control-password={password}')
            else:
                args.append('--server-control-password=random')
            
            if tls:
                args.append('--tls-generate-cert')
            
            self._server_process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.sleep(2)
            
            if self._server_process.returncode is None:
                self._server_status = 'running'
                self._server_port = port
                logger.info(f"Kopia server started on port {port}")
                return {'status': 'success', 'port': port}
            else:
                _, stderr = await self._server_process.communicate()
                error = stderr.decode()
                logger.error(f"Failed to start server: {error}")
                return {'status': 'error', 'message': error}
                
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def stop_server(self) -> dict:
        """Stop Kopia server."""
        if self._server_status != 'running' or not self._server_process:
            return {'status': 'not_running'}
        
        try:
            self._server_process.terminate()
            try:
                await asyncio.wait_for(self._server_process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self._server_process.kill()
                await self._server_process.wait()
            
            self._server_status = 'stopped'
            self._server_process = None
            logger.info("Kopia server stopped")
            
            return {'status': 'success'}
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_server_status(self) -> dict:
        """Get server status."""
        return {
            'status': self._server_status,
            'port': self._server_port,
            'tls': True
        }
    
    # ==================== Commands ====================
    
    async def execute_command(self, command: str, args: list = None) -> dict:
        """
        Execute a Kopia command.
        
        Args:
            command: Kopia command (e.g., 'snapshot list')
            args: Additional arguments
            
        Returns:
            dict with output
        """
        cmd_parts = [str(self.kopia_path)] + command.split()
        if args:
            cmd_parts.extend(args)
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            return {
                'status': 'success' if proc.returncode == 0 else 'error',
                'output': stdout.decode(),
                'error': stderr.decode() if proc.returncode != 0 else None,
                'returncode': proc.returncode
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def list_snapshots(self) -> dict:
        """List all snapshots."""
        return await self.execute_command('snapshot list')

    async def list_object(self, object_path: str) -> list[dict]:
        """List a Kopia object path."""
        json_result = await self._list_object_json(object_path)
        if json_result is not None:
            return json_result
        return await self._list_object_text(object_path)

    async def _list_object_json(self, object_path: str) -> Optional[list[dict]]:
        proc = await asyncio.create_subprocess_exec(
            str(self.kopia_path), 'ls', '--json', '--long', object_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
        try:
            payload = json.loads(stdout.decode() or '[]')
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            items = payload.get('entries') or payload.get('items') or []
        else:
            items = payload
        result = []
        for item in items:
            name = item.get('name') or item.get('path') or ''
            if not name or name in ('.', '..'):
                continue
            item_type = item.get('type') or item.get('mode') or ''
            is_directory = bool(item.get('isDir') or item.get('is_directory') or str(item_type).startswith('d') or item_type == 'dir')
            result.append({
                'name': name.rstrip('/'),
                'size': int(item.get('size') or item.get('length') or 0),
                'modified_time': item.get('mtime') or item.get('modTime') or item.get('modified') or None,
                'is_directory': is_directory,
            })
        return result

    async def _list_object_text(self, object_path: str) -> list[dict]:
        proc = await asyncio.create_subprocess_exec(
            str(self.kopia_path), 'ls', '--long', object_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode() or stdout.decode())
        entries = []
        for raw in stdout.decode().splitlines():
            line = raw.strip()
            if not line or line.startswith('total '):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            mode = parts[0]
            name = parts[-1].rstrip('/')
            if name in ('.', '..'):
                continue
            size = 0
            for part in parts[1:-1]:
                try:
                    size = int(part)
                    break
                except ValueError:
                    continue
            entries.append({
                'name': name,
                'size': size,
                'modified_time': None,
                'is_directory': mode.startswith('d'),
            })
        return entries
    
    async def get_stats(self) -> dict:
        """Get repository statistics."""
        return await self.execute_command('repository stats')
    
    async def verify(self, snapshot_id: str = None, verify_percent: int = 5) -> dict:
        """Verify snapshots."""
        args = [f'--verify-files-percent={verify_percent}']
        if snapshot_id:
            args.append(f'--snapshot-id={snapshot_id}')
        return await self.execute_command('snapshot verify', args)


class SystemMonitor:
    """System monitoring utilities."""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get CPU usage percentage."""
        if psutil:
            return psutil.cpu_percent(interval=1)
        return 0.0
    
    @staticmethod
    def get_memory_usage() -> float:
        """Get memory usage percentage."""
        if psutil:
            return psutil.virtual_memory().percent
        return 0.0
    
    @staticmethod
    def get_disk_usage(path: str = '/') -> float:
        """Get disk usage percentage."""
        if psutil:
            return psutil.disk_usage(path).percent
        return 0.0
    
    @staticmethod
    def get_system_info() -> dict:
        """Get system information."""
        info = {
            'hostname': platform.node(),
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'cpu_cores': os.cpu_count() or 1,
            'architecture': platform.machine(),
        }
        
        if psutil:
            mem = psutil.virtual_memory()
            info['memory_total_gb'] = round(mem.total / (1024**3), 2)
            info['memory_available_gb'] = round(mem.available / (1024**3), 2)
            
            disk = psutil.disk_usage('/')
            info['disk_total_gb'] = round(disk.total / (1024**3), 2)
            info['disk_free_gb'] = round(disk.free / (1024**3), 2)
        
        return info
    
    @staticmethod
    def get_metrics() -> dict:
        """Get current system metrics."""
        return {
            'cpu_usage': SystemMonitor.get_cpu_usage(),
            'memory_usage': SystemMonitor.get_memory_usage(),
            'disk_usage': SystemMonitor.get_disk_usage(),
            'timestamp': datetime.now().isoformat()
        }


class GatewayAgent:
    """
    Gateway Agent that connects to the control plane and handles commands.
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.gateway_id = config.gateway_id
        self.ws_url = f"{config.server_url.replace('http', config.ws_protocol)}/ws/gateway/{config.gateway_id}/"
        
        # Components
        self.kopia = KopiaClient(config)
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
                        'mount_count': len(mounts)
                    },
                    'mounts': [m['mount_point'] for m in mounts]
                }
                
                await self._ws.send(json.dumps(heartbeat))
                logger.debug("Sent heartbeat")
                
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
            connect_result = await self.kopia.connect_repository_config(repository, password)
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
        query = data.get('query')
        context = data.get('context')
        repository_ids = data.get('repository_ids')
        
        # TODO: Implement AI query
        
        response = {
            'type': 'ai_query_result',
            'task_id': task_id,
            'success': False,
            'error': 'AI query not implemented',
            'result': {}
        }
        
        await self._ws.send(json.dumps(response))

    async def _handle_ai_summarize_snapshot(self, data):
        """Handle snapshot AI summary."""
        task_id = data.get('task_id')
        job_id = data.get('job_id')
        snapshot_context = data.get('snapshot_context') or {}
        language = data.get('language') or 'zh-CN'
        provider_config = data.get('ai_provider_config') or {}
        try:
            await self._ws.send(json.dumps({
                'type': 'ai_summary_progress',
                'task_id': task_id,
                'job_id': job_id,
                'status': 'running',
                'progress': 20,
            }))
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


async def main():
    """Main entry point."""
    # Load configuration
    config = GatewayConfig()
    
    # Set log level
    logging.getLogger().setLevel(config.log_level)
    
    # Create and start agent
    agent = GatewayAgent(config)
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.stop()


if __name__ == '__main__':
    asyncio.run(main())
