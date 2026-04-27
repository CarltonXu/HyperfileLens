"""
Kopia repository mounting functionality
"""
import os
import subprocess
import asyncio
import logging
from typing import Optional
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)


class KopiaMount:
    """Manages Kopia repository mounting"""
    
    def __init__(self):
        self.mount_path = Path(settings.KOPIA_MOUNT_PATH)
        self.repo_path = Path(settings.REPO_PATH)
        self.password = settings.KOPIA_PASSWORD
        self._mount_process: Optional[subprocess.Popen] = None
        self._is_mounted = False
    
    async def init_repository(self) -> dict:
        """Initialize a new Kopia repository if not exists"""
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        # Check if repository already exists
        config_file = self.repo_path / "kopia.repository"
        if config_file.exists():
            return {"status": "exists", "path": str(self.repo_path)}
        
        # Create new repository
        try:
            proc = await asyncio.create_subprocess_exec(
                "kopia", "repository", "create", "filesystem",
                f"--path={self.repo_path}",
                f"--password={self.password}",
                "--override-hostname=gateway",
                "--override-username=hfl",
                "--ignore-unknown-parameters",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Repository created at {self.repo_path}")
                return {"status": "created", "path": str(self.repo_path)}
            else:
                logger.error(f"Failed to create repository: {stderr.decode()}")
                return {"status": "error", "message": stderr.decode()}
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return {"status": "error", "message": str(e)}
    
    async def connect_repository(self) -> dict:
        """Connect to existing repository"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "kopia", "repository", "connect", "filesystem",
                f"--path={self.repo_path}",
                f"--password={self.password}",
                "--override-hostname=gateway",
                "--override-username=hfl",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Connected to repository at {self.repo_path}")
                return {"status": "connected", "path": str(self.repo_path)}
            else:
                logger.error(f"Failed to connect: {stderr.decode()}")
                return {"status": "error", "message": stderr.decode()}
        except Exception as e:
            logger.error(f"Error connecting to repository: {e}")
            return {"status": "error", "message": str(e)}
    
    async def mount(self) -> dict:
        """Mount the repository for file access"""
        if self._is_mounted:
            return {"status": "already_mounted", "path": str(self.mount_path)}
        
        # Ensure mount directory exists
        self.mount_path.mkdir(parents=True, exist_ok=True)
        
        # Connect first
        connect_result = await self.connect_repository()
        if connect_result.get("status") == "error":
            # Try to initialize if connect fails
            init_result = await self.init_repository()
            if init_result.get("status") == "error":
                return init_result
        
        try:
            # Mount the repository
            self._mount_process = await asyncio.create_subprocess_exec(
                "kopia", "mount", str(self.mount_path),
                f"--password={self.password}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a bit for mount to complete
            await asyncio.sleep(2)
            
            if self._mount_process.returncode is None:
                self._is_mounted = True
                logger.info(f"Repository mounted at {self.mount_path}")
                return {"status": "mounted", "path": str(self.mount_path)}
            else:
                stdout, stderr = await self._mount_process.communicate()
                logger.error(f"Mount failed: {stderr.decode()}")
                return {"status": "error", "message": stderr.decode()}
        except Exception as e:
            logger.error(f"Error mounting repository: {e}")
            return {"status": "error", "message": str(e)}
    
    async def unmount(self) -> dict:
        """Unmount the repository"""
        if not self._is_mounted:
            return {"status": "not_mounted"}
        
        try:
            # Use fusermount to unmount
            proc = await asyncio.create_subprocess_exec(
                "fusermount", "-u", str(self.mount_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            self._is_mounted = False
            self._mount_process = None
            logger.info(f"Repository unmounted from {self.mount_path}")
            return {"status": "unmounted"}
        except Exception as e:
            logger.error(f"Error unmounting: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_status(self) -> dict:
        """Get mount status"""
        return {
            "is_mounted": self._is_mounted,
            "mount_path": str(self.mount_path),
            "repo_path": str(self.repo_path)
        }
    
    def is_mounted(self) -> bool:
        """Check if repository is mounted"""
        return self._is_mounted


# Global instance
kopia_mount = KopiaMount()
