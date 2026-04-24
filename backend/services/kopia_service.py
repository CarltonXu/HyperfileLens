"""
HyperFileLens Backend - Kopia Backup Engine Integration

This module provides integration with Kopia backup engine for:
- Repository initialization and management
- Snapshot creation and management
- File backup and restore operations
- Connection testing and health checks
"""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class KopiaRepositoryConfig:
    """Configuration for Kopia repository connection."""
    repo_path: str  # e.g., "s3://bucket/path" or "/mnt/backup"
    repo_type: str  # "s3", "azure", "gs", "filesystem", etc.
    username: Optional[str] = None
    password: Optional[str] = None
    hostname: Optional[str] = None
   kv-password: Optional[str] = None  # Password for encrypting the repository


@dataclass
class KopiaSnapshot:
    """Represents a Kopia snapshot."""
    id: str
    source_path: str
    timestamp: datetime
    files_count: int
    total_size: int
    manifest_id: str
    root_kopia_id: str
    tags: Dict[str, str] = None


class KopiaService:
    """
    Service class for interacting with Kopia backup engine.
    
    Kopia is a cross-platform backup tool that provides:
    - Content-addressable storage
    - Deduplication
    - Compression
    - Encryption
    - Multi-backend support (S3, Azure, GCS, filesystem, etc.)
    """
    
    def __init__(self, kopia_path: str = "kopia"):
        """
        Initialize Kopia service.
        
        Args:
            kopia_path: Path to kopia binary. Defaults to 'kopia' in PATH.
        """
        self.kopia_path = kopia_path
        self._repo_config: Optional[KopiaRepositoryConfig] = None
    
    def _run_command(self, args: List[str], input_data: Optional[str] = None, 
                     timeout: int = 300) -> Tuple[int, str, str]:
        """
        Run a kopia command.
        
        Args:
            args: Command arguments
            input_data: Optional stdin input
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = [self.kopia_path] + args
        
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Kopia command timed out: {' '.join(cmd)}")
            return -1, "", "Command timed out"
        except FileNotFoundError:
            logger.error(f"Kopia binary not found at: {self.kopia_path}")
            return -1, "", f"Kopia binary not found: {self.kopia_path}"
        except Exception as e:
            logger.exception(f"Error running kopia command: {e}")
            return -1, "", str(e)
    
    def check_installed(self) -> Tuple[bool, str]:
        """
        Check if kopia is installed and get version.
        
        Returns:
            Tuple of (is_installed, version_string)
        """
        returncode, stdout, stderr = self._run_command(["--version"])
        
        if returncode == 0:
            version = stdout.strip().split('\n')[0] if stdout else "Unknown"
            return True, version
        
        return False, stderr.strip() or "Not installed"
    
    def init_repository(self, config: KopiaRepositoryConfig, 
                       force: bool = False) -> Tuple[bool, str]:
        """
        Initialize a Kopia repository.
        
        Args:
            config: Repository configuration
            force: Force reinitialization if exists
            
        Returns:
            Tuple of (success, message)
        """
        self._repo_config = config
        
        args = [
            "repository",
            "create",
            self._get_repo_connect_args(config),
        ]
        
        if force:
            args.append("--override-owner")
        
        # Set repository password
        if config.kv_password:
            input_data = config.kv_password
        
        returncode, stdout, stderr = self._run_command(
            args, 
            input_data=config.kv_password
        )
        
        if returncode == 0:
            logger.info(f"Repository initialized: {config.repo_path}")
            return True, "Repository initialized successfully"
        
        return False, stderr or "Failed to initialize repository"
    
    def connect_repository(self, config: KopiaRepositoryConfig) -> Tuple[bool, str]:
        """
        Connect to an existing Kopia repository.
        
        Args:
            config: Repository configuration
            
        Returns:
            Tuple of (success, message)
        """
        self._repo_config = config
        
        args = [
            "repository",
            "connect",
            self._get_repo_connect_args(config),
        ]
        
        returncode, stdout, stderr = self._run_command(
            args,
            input_data=config.kv_password
        )
        
        if returncode == 0:
            logger.info(f"Connected to repository: {config.repo_path}")
            return True, "Connected successfully"
        
        return False, stderr or "Failed to connect to repository"
    
    def disconnect_repository(self) -> Tuple[bool, str]:
        """
        Disconnect from current repository.
        
        Returns:
            Tuple of (success, message)
        """
        args = ["repository", "disconnect", "--force"]
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode == 0:
            self._repo_config = None
            return True, "Disconnected successfully"
        
        return False, stderr or "Failed to disconnect"
    
    def create_snapshot(self, paths: List[str], 
                       tags: Optional[Dict[str, str]] = None,
                       description: Optional[str] = None) -> Tuple[bool, str, Optional[KopiaSnapshot]]:
        """
        Create a backup snapshot of specified paths.
        
        Args:
            paths: List of paths to backup
            tags: Optional metadata tags
            description: Optional description
            
        Returns:
            Tuple of (success, message, snapshot)
        """
        if not self._repo_config:
            return False, "Not connected to repository", None
        
        args = [
            "snapshot",
            "create",
        ]
        
        # Add paths
        args.extend(paths)
        
        # Add tags if provided
        if tags:
            for key, value in tags.items():
                args.extend(["--tag", f"{key}={value}"])
        
        # Add description
        if description:
            args.extend(["--description", description])
        
        returncode, stdout, stderr = self._run_command(args, timeout=3600)
        
        if returncode == 0:
            # Parse snapshot info from output
            snapshot = self._parse_snapshot_output(stdout, paths[0] if paths else "")
            logger.info(f"Snapshot created: {snapshot.id if snapshot else 'unknown'}")
            return True, "Snapshot created successfully", snapshot
        
        return False, stderr or "Failed to create snapshot", None
    
    def list_snapshots(self, source_path: Optional[str] = None,
                       tags: Optional[Dict[str, str]] = None) -> List[KopiaSnapshot]:
        """
        List snapshots in the repository.
        
        Args:
            source_path: Optional filter by source path
            tags: Optional filter by tags
            
        Returns:
            List of snapshots
        """
        if not self._repo_config:
            return []
        
        args = [
            "snapshot",
            "list",
            "--json",
        ]
        
        if source_path:
            args.extend(["--path", source_path])
        
        if tags:
            for key, value in tags.items():
                args.extend(["--tag", f"{key}={value}"])
        
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode != 0 or not stdout:
            logger.warning(f"Failed to list snapshots: {stderr}")
            return []
        
        return self._parse_snapshots_json(stdout)
    
    def delete_snapshot(self, snapshot_id: str, 
                       force: bool = False) -> Tuple[bool, str]:
        """
        Delete a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to delete
            force: Force deletion
            
        Returns:
            Tuple of (success, message)
        """
        args = [
            "snapshot",
            "delete",
            snapshot_id,
        ]
        
        if force:
            args.append("--force")
        
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode == 0:
            logger.info(f"Snapshot deleted: {snapshot_id}")
            return True, "Snapshot deleted successfully"
        
        return False, stderr or "Failed to delete snapshot"
    
    def restore_snapshot(self, snapshot_id: str, 
                        target_path: str,
                        file_patterns: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Restore files from a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Target directory for restore
            file_patterns: Optional list of file patterns to restore
            
        Returns:
            Tuple of (success, message)
        """
        args = [
            "snapshot",
            "restore",
            snapshot_id,
            "--target", target_path,
        ]
        
        if file_patterns:
            for pattern in file_patterns:
                args.extend(["--file", pattern])
        
        returncode, stdout, stderr = self._run_command(args, timeout=3600)
        
        if returncode == 0:
            logger.info(f"Snapshot restored to: {target_path}")
            return True, "Restore completed successfully"
        
        return False, stderr or "Failed to restore snapshot"
    
    def mount_snapshot(self, snapshot_id: str,
                       mount_path: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Mount a snapshot as a filesystem.
        
        Args:
            snapshot_id: ID of the snapshot to mount
            mount_path: Optional custom mount path
            
        Returns:
            Tuple of (success, message, actual_mount_path)
        """
        if mount_path is None:
            mount_path = tempfile.mkdtemp(prefix="kopia_mount_")
        
        args = [
            "mount",
            snapshot_id,
            "--mount-point", mount_path,
        ]
        
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode == 0:
            logger.info(f"Snapshot mounted at: {mount_path}")
            return True, "Mounted successfully", mount_path
        
        return False, stderr or "Failed to mount snapshot", None
    
    def get_snapshot_info(self, snapshot_id: str) -> Optional[KopiaSnapshot]:
        """
        Get detailed information about a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot
            
        Returns:
            Snapshot object or None
        """
        snapshots = self.list_snapshots()
        for snap in snapshots:
            if snap.id == snapshot_id or snap.manifest_id == snapshot_id:
                return snap
        return None
    
    def get_repository_status(self) -> Dict:
        """
        Get repository status and statistics.
        
        Returns:
            Dictionary with repository status
        """
        args = ["repository", "status", "--json"]
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass
        
        return {"status": "error", "message": stderr or "Unknown error"}
    
    def verify_snapshot(self, snapshot_id: str) -> Tuple[bool, str]:
        """
        Verify integrity of a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to verify
            
        Returns:
            Tuple of (success, message)
        """
        args = [
            "snapshot",
            "verify",
            snapshot_id,
        ]
        
        returncode, stdout, stderr = self._run_command(args, timeout=3600)
        
        if returncode == 0:
            return True, "Verification passed"
        
        return False, stderr or "Verification failed"
    
    def _get_repo_connect_args(self, config: KopiaRepositoryConfig) -> str:
        """Generate repository connection arguments based on config."""
        if config.repo_type == "filesystem":
            return f"filesystem --path={config.repo_path}"
        elif config.repo_type == "s3":
            return f"s3 --bucket={config.repo_path} --endpoint={config.hostname or ''}"
        elif config.repo_type == "azure":
            return f"azure --container={config.repo_path}"
        elif config.repo_type == "gs":
            return f"gs --bucket={config.repo_path}"
        elif config.repo_type == "swift":
            return f"swift --container={config.repo_path}"
        else:
            return config.repo_path
    
    def _parse_snapshot_output(self, output: str, source_path: str) -> Optional[KopiaSnapshot]:
        """Parse kopia snapshot create output."""
        try:
            # Look for snapshot ID in output
            # Example: "Created snapshot with ID abc123..."
            for line in output.split('\n'):
                if 'Created snapshot with ID' in line or 'snapshot with ID' in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == 'id' and i + 1 < len(parts):
                            snapshot_id = parts[i + 1].rstrip('.')
                            return KopiaSnapshot(
                                id=snapshot_id,
                                source_path=source_path,
                                timestamp=datetime.now(),
                                files_count=0,
                                total_size=0,
                                manifest_id=snapshot_id,
                                root_kopia_id=snapshot_id
                            )
            return None
        except Exception as e:
            logger.warning(f"Failed to parse snapshot output: {e}")
            return None
    
    def _parse_snapshots_json(self, json_output: str) -> List[KopiaSnapshot]:
        """Parse JSON output from kopia snapshot list."""
        snapshots = []
        try:
            data = json.loads(json_output)
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                snap = KopiaSnapshot(
                    id=item.get('id', ''),
                    source_path=item.get('path', ''),
                    timestamp=datetime.fromisoformat(
                        item.get('startTime', datetime.now().isoformat())
                    ),
                    files_count=item.get('stats', {}).get('fileCount', 0),
                    total_size=item.get('stats', {}).get('size', 0),
                    manifest_id=item.get('manifestID', ''),
                    root_kopia_id=item.get('rootEntry', {}).get('objectID', ''),
                    tags=item.get('tags', {})
                )
                snapshots.append(snap)
        except Exception as e:
            logger.warning(f"Failed to parse snapshots JSON: {e}")
        
        return snapshots


class KopiaBackupExecutor:
    """
    High-level executor for backup operations using Kopia.
    
    This class provides a simplified interface for common backup tasks
    and integrates with the HyperFileLens task management system.
    """
    
    def __init__(self, kopia_service: Optional[KopiaService] = None):
        """
        Initialize backup executor.
        
        Args:
            kopia_service: Optional pre-configured Kopia service
        """
        self.kopia = kopia_service or KopiaService()
    
    def check_health(self) -> Dict:
        """Check overall backup system health."""
        is_installed, version = self.kopia.check_installed()
        
        status = {
            "kopia_installed": is_installed,
            "kopia_version": version,
            "repository_connected": self.kopia._repo_config is not None,
        }
        
        if status["repository_connected"]:
            repo_status = self.kopia.get_repository_status()
            status["repository_status"] = repo_status
        
        return status
    
    def execute_backup(self, paths: List[str], 
                      repository_config: KopiaRepositoryConfig,
                      tags: Optional[Dict[str, str]] = None,
                      description: Optional[str] = None) -> Dict:
        """
        Execute a complete backup operation.
        
        Args:
            paths: List of paths to backup
            repository_config: Repository configuration
            tags: Optional metadata tags
            description: Optional description
            
        Returns:
            Dictionary with operation results
        """
        result = {
            "success": False,
            "message": "",
            "snapshot_id": None,
        }
        
        # Check if kopia is installed
        is_installed, version = self.kopia.check_installed()
        if not is_installed:
            result["message"] = f"Kopia not installed: {version}"
            return result
        
        # Connect to repository
        success, message = self.kopia.connect_repository(repository_config)
        if not success:
            result["message"] = f"Failed to connect to repository: {message}"
            return result
        
        try:
            # Create snapshot
            success, message, snapshot = self.kopia.create_snapshot(
                paths=paths,
                tags=tags,
                description=description
            )
            
            result["success"] = success
            result["message"] = message
            if snapshot:
                result["snapshot_id"] = snapshot.id
                result["snapshot"] = {
                    "id": snapshot.id,
                    "source_path": snapshot.source_path,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "files_count": snapshot.files_count,
                    "total_size": snapshot.total_size,
                }
        finally:
            # Disconnect from repository
            self.kopia.disconnect_repository()
        
        return result
    
    def execute_restore(self, snapshot_id: str,
                       target_path: str,
                       repository_config: KopiaRepositoryConfig,
                       file_patterns: Optional[List[str]] = None) -> Dict:
        """
        Execute a restore operation.
        
        Args:
            snapshot_id: ID of snapshot to restore
            target_path: Target directory for restore
            repository_config: Repository configuration
            file_patterns: Optional file patterns to restore
            
        Returns:
            Dictionary with operation results
        """
        result = {
            "success": False,
            "message": "",
            "target_path": target_path,
        }
        
        # Connect to repository
        success, message = self.kopia.connect_repository(repository_config)
        if not success:
            result["message"] = f"Failed to connect to repository: {message}"
            return result
        
        try:
            # Restore snapshot
            success, message = self.kopia.restore_snapshot(
                snapshot_id=snapshot_id,
                target_path=target_path,
                file_patterns=file_patterns
            )
            
            result["success"] = success
            result["message"] = message
        finally:
            self.kopia.disconnect_repository()
        
        return result
    
    def list_available_snapshots(self,
                                  repository_config: KopiaRepositoryConfig,
                                  source_path: Optional[str] = None) -> List[Dict]:
        """
        List available snapshots in repository.
        
        Args:
            repository_config: Repository configuration
            source_path: Optional filter by source path
            
        Returns:
            List of snapshot dictionaries
        """
        # Connect to repository
        success, _ = self.kopia.connect_repository(repository_config)
        if not success:
            return []
        
        try:
            snapshots = self.kopia.list_snapshots(source_path=source_path)
            return [
                {
                    "id": s.id,
                    "source_path": s.source_path,
                    "timestamp": s.timestamp.isoformat(),
                    "files_count": s.files_count,
                    "total_size": s.total_size,
                    "tags": s.tags or {},
                }
                for s in snapshots
            ]
        finally:
            self.kopia.disconnect_repository()
