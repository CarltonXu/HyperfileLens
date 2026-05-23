"""Repository storage access management for Gateway tasks."""

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .config import GatewayConfig

logger = logging.getLogger('gateway-agent')


@dataclass
class RepositoryAccess:
    """Resolved repository access details."""

    repository: dict
    mount_path: str | None = None


class RepositoryStorageManager:
    """Prepare repository storage access before Kopia operations."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.storage_base = Path('/mnt/hyperfilelens')

    async def prepare(self, repository: dict) -> RepositoryAccess:
        repo_type = (repository or {}).get('type') or 'filesystem'
        if repo_type in ('nas', 'nfs', 'cifs', 'smb'):
            mount_path = await self.ensure_network_repository_mounted(repository)
            resolved = {
                **repository,
                'type': 'filesystem',
                'path': mount_path,
                'mounted_path': mount_path,
            }
            return RepositoryAccess(repository=resolved, mount_path=mount_path)
        return RepositoryAccess(repository=repository)

    async def ensure_network_repository_mounted(self, repository: dict) -> str:
        repo_id = str(repository.get('id') or '').replace('-', '')
        if not repo_id:
            raise ValueError('repository id is required for network repository mount')
        mount_path = str(self.storage_base / f"repository-{repo_id[:8]}")
        Path(mount_path).mkdir(parents=True, exist_ok=True)

        if await self.is_mounted(mount_path):
            logger.info("Repository storage already mounted path=%s", mount_path)
            return mount_path

        mount_type = (
            repository.get('mount_type')
            or repository.get('nas_type')
            or repository.get('protocol')
            or repository.get('type')
            or 'nfs'
        ).lower()
        if mount_type == 'smb':
            mount_type = 'cifs'

        if mount_type == 'cifs':
            await self.mount_cifs(repository, mount_path)
        else:
            await self.mount_nfs(repository, mount_path)

        if not await self.is_mounted(mount_path):
            raise RuntimeError(f"repository mount did not become active: {mount_path}")
        return mount_path

    async def is_mounted(self, mount_path: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            'findmnt',
            '-rn',
            '--target',
            mount_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def mount_nfs(self, repository: dict, mount_path: str) -> None:
        server = repository.get('server') or repository.get('nas_server') or ''
        export_path = (
            repository.get('export_path')
            or repository.get('nas_path')
            or repository.get('path')
            or ''
        )
        if not server or not export_path:
            raise ValueError('NFS repository requires server and export_path')

        source = f"{server}:{export_path}"
        args = ['mount', '-t', 'nfs']
        options = repository.get('mount_options') or ''
        if options:
            args.extend(['-o', options])
        args.extend([source, mount_path])
        await self.run_mount_command(args, mount_path)

    async def mount_cifs(self, repository: dict, mount_path: str) -> None:
        server = repository.get('server') or repository.get('nas_server') or ''
        share = (
            repository.get('share')
            or repository.get('export_path')
            or repository.get('nas_path')
            or repository.get('path')
            or ''
        )
        if not server or not share:
            raise ValueError('CIFS repository requires server and share')

        source = f"//{server}/{share.strip('/')}"
        credential_file = self.write_cifs_credentials(repository)
        options = []
        if credential_file:
            options.append(f"credentials={credential_file}")
        raw_options = repository.get('mount_options') or ''
        if raw_options:
            options.append(raw_options)

        args = ['mount', '-t', 'cifs']
        if options:
            args.extend(['-o', ','.join(options)])
        args.extend([source, mount_path])
        await self.run_mount_command(args, mount_path)

    def write_cifs_credentials(self, repository: dict) -> str:
        username = repository.get('username') or ''
        password = repository.get('password') or ''
        if not username and not password:
            return ''
        repo_id = str(repository.get('id') or '').replace('-', '')[:8]
        credential_dir = Path('/etc/hyperfilelens/gateway/credentials')
        credential_dir.mkdir(parents=True, exist_ok=True)
        credential_file = credential_dir / f"repository-{repo_id}.cifs"
        credential_file.write_text(
            f"username={username}\npassword={password}\n",
            encoding='utf-8',
        )
        os.chmod(credential_file, 0o600)
        return str(credential_file)

    async def run_mount_command(self, args: list[str], mount_path: str) -> None:
        logger.info("Mounting repository storage path=%s command=%s", mount_path, self.redact(args))
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = (stdout + stderr).decode().strip()
        if proc.returncode != 0:
            raise RuntimeError(output or f"mount failed for {mount_path}")
        logger.info("Mounted repository storage path=%s", mount_path)

    @staticmethod
    def redact(args: list[str]) -> str:
        return ' '.join('[REDACTED]' if 'password=' in arg else arg for arg in args)
