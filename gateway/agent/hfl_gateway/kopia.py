"""Kopia CLI integration for the Gateway agent."""

import asyncio
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .config import GatewayConfig

logger = logging.getLogger('gateway-agent')

@dataclass
class MountInfo:
    """Information about an active mount."""
    mount_id: str
    repository_id: str
    mount_point: str
    snapshot_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    process: Optional[subprocess.Popen] = None


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
                output = stdout.decode().strip()
                for line in output.split('\n'):
                    if 'kopia' in line.lower():
                        return line.strip()
                if output:
                    return output.splitlines()[0].strip()
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
                logger.info(
                    "Connecting filesystem Kopia repository path=%s type=%s",
                    storage_path,
                    repo_type,
                )
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
            logger.debug(
                "Kopia repository connect completed type=%s returncode=%s output=%s",
                repo_type,
                proc.returncode,
                self._truncate(output),
            )
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
            logger.debug("Executing Kopia command args=%s", self._redact_args(cmd_parts))
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stdout_text = stdout.decode(errors='ignore')
            stderr_text = stderr.decode(errors='ignore')
            logger.debug(
                "Kopia command completed returncode=%s stdout=%s stderr=%s",
                proc.returncode,
                self._truncate(stdout_text),
                self._truncate(stderr_text),
            )
            
            return {
                'status': 'success' if proc.returncode == 0 else 'error',
                'output': stdout_text,
                'error': stderr_text if proc.returncode != 0 else None,
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
        logger.debug("Listing Kopia object path=%s", object_path)
        json_result = await self._list_object_json(object_path)
        if json_result is not None:
            logger.debug("Listed Kopia object path=%s format=json entries=%s", object_path, len(json_result))
            return json_result
        text_result = await self._list_object_text(object_path)
        logger.debug("Listed Kopia object path=%s format=text entries=%s", object_path, len(text_result))
        return text_result

    async def _list_object_json(self, object_path: str) -> Optional[list[dict]]:
        args = [str(self.kopia_path), 'ls', '--json', '--long', object_path]
        logger.debug("Executing Kopia ls json args=%s", self._redact_args(args))
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.debug("Kopia ls json timed out path=%s", object_path)
            return None
        if proc.returncode != 0:
            logger.debug(
                "Kopia ls json failed path=%s returncode=%s stderr=%s",
                object_path,
                proc.returncode,
                self._truncate(stderr.decode(errors='ignore')),
            )
            return None
        try:
            payload = json.loads(stdout.decode() or '[]')
        except json.JSONDecodeError:
            logger.debug(
                "Kopia ls json parse failed path=%s stdout=%s",
                object_path,
                self._truncate(stdout.decode(errors='ignore')),
            )
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
        args = [str(self.kopia_path), 'ls', '--long', object_path]
        logger.debug("Executing Kopia ls text args=%s", self._redact_args(args))
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("Kopia ls text timed out path=%s", object_path)
            raise RuntimeError(f"kopia ls timed out path={object_path}")
        if proc.returncode != 0:
            stdout_text = stdout.decode(errors='ignore')
            stderr_text = stderr.decode(errors='ignore')
            logger.debug(
                "Kopia ls text failed path=%s returncode=%s stdout=%s stderr=%s",
                object_path,
                proc.returncode,
                self._truncate(stdout_text),
                self._truncate(stderr_text),
            )
            raise RuntimeError(f"kopia ls failed path={object_path}: {stderr_text or stdout_text}")
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

    async def read_object_text(self, object_id: str, path: str = '', max_bytes: int = 20000) -> str:
        """Read a bounded UTF-8 text sample from a Kopia object path."""
        object_path = object_id.rstrip('/')
        if path:
            object_path = f"{object_path}/{path.strip('/')}"
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self.kopia_path), 'show', object_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
            if proc.returncode != 0:
                logger.debug(
                    "Unable to read object text path=%s error=%s",
                    object_path,
                    stderr.decode(errors='ignore'),
                )
                return ''
            return stdout[:max_bytes].decode('utf-8', errors='ignore')
        except asyncio.TimeoutError:
            logger.debug("Timed out reading object text path=%s", object_path)
            return ''
        except Exception as e:
            logger.debug("Error reading object text path=%s error=%s", object_path, e)
            return ''

    @staticmethod
    def _truncate(value: str, limit: int = 1200) -> str:
        value = (value or '').strip()
        if len(value) <= limit:
            return value
        return value[:limit] + '...<truncated>'

    @staticmethod
    def _redact_args(args: list[str]) -> list[str]:
        redacted = []
        skip_next = False
        sensitive_flags = {
            '--password',
            '--access-key',
            '--secret-access-key',
            '--token',
            '--server-control-password',
        }
        for arg in args:
            if skip_next:
                redacted.append('[REDACTED]')
                skip_next = False
                continue
            if arg in sensitive_flags:
                redacted.append(arg)
                skip_next = True
                continue
            if any(arg.startswith(flag + '=') for flag in sensitive_flags):
                key = arg.split('=', 1)[0]
                redacted.append(f"{key}=[REDACTED]")
                continue
            redacted.append(arg)
        return redacted
    
    async def get_stats(self) -> dict:
        """Get repository statistics."""
        return await self.execute_command('repository stats')
    
    async def verify(self, snapshot_id: str = None, verify_percent: int = 5) -> dict:
        """Verify snapshots."""
        args = [f'--verify-files-percent={verify_percent}']
        if snapshot_id:
            args.append(f'--snapshot-id={snapshot_id}')
        return await self.execute_command('snapshot verify', args)
