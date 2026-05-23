"""
Gateway Service for WebSocket Communication

This module provides methods for sending commands to Gateway nodes
via WebSocket for operations like mounting, Kopia server management, etc.
"""

import json
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from audit_log.services import AuditService


class GatewayService:
    """
    Service class for communicating with Gateway nodes via WebSocket.
    
    Provides methods to send commands for:
    - Mount/unmount operations
    - Kopia server management
    - Kopia commands execution
    - Indexing operations
    - AI queries
    """
    
    @staticmethod
    def send_command(gateway_id: str, command: dict) -> str:
        """
        Send a command to a gateway via WebSocket.
        
        Args:
            gateway_id: UUID of the gateway
            command: Command dict to send
            
        Returns:
            task_id: UUID of the task for tracking
        """
        channel_layer = get_channel_layer()
        task_id = str(uuid.uuid4())
        
        command['task_id'] = task_id
        command['timestamp'] = timezone.now().isoformat()
        
        async_to_sync(channel_layer.group_send)(
            f'gateway_{gateway_id}',
            {
                'type': 'send_command',
                'data': command
            }
        )
        
        return task_id

    # ==================== Mount Operations ====================

    @classmethod
    def mount_repository(cls, gateway_id: str, repository_id: str, 
                         mount_point: str = None) -> str:
        """
        Send mount repository command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository to mount
            mount_point: Optional custom mount point
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'mount',
            'repository_id': repository_id,
            'mount_point': mount_point
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_gateway_mount_command(gateway_id, repository_id, mount_point)
        
        return task_id

    @classmethod
    def unmount_repository(cls, gateway_id: str, repository_id: str) -> str:
        """
        Send unmount repository command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository to unmount
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'unmount',
            'repository_id': repository_id
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_gateway_unmount_command(gateway_id, repository_id)
        
        return task_id

    @classmethod
    def mount_snapshot(cls, gateway_id: str, snapshot_id: str,
                       mount_point: str = None, read_only: bool = True) -> str:
        """
        Send mount snapshot command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            snapshot_id: UUID of the snapshot to mount
            mount_point: Optional custom mount point
            read_only: Whether to mount as read-only
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'snapshot_mount',
            'snapshot_id': snapshot_id,
            'mount_point': mount_point,
            'read_only': read_only
        }
        
        return cls.send_command(gateway_id, command)

    @classmethod
    def list_mounts(cls, gateway_id: str) -> str:
        """
        Request list of active mounts from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'list_mounts'
        }
        
        return cls.send_command(gateway_id, command)

    # ==================== Kopia Server Operations ====================

    @classmethod
    def start_kopia_server(cls, gateway_id: str, port: int = 51515,
                           tls: bool = True, password: str = None) -> str:
        """
        Send start Kopia server command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            port: Port to run the server on
            tls: Whether to enable TLS
            password: Server password (auto-generated if not provided)
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'server_start',
            'port': port,
            'tls': tls,
            'password': password
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_gateway_server_start(gateway_id, port)
        
        return task_id

    @classmethod
    def stop_kopia_server(cls, gateway_id: str) -> str:
        """
        Send stop Kopia server command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'server_stop'
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_gateway_server_stop(gateway_id)
        
        return task_id

    @classmethod
    def get_server_status(cls, gateway_id: str) -> str:
        """
        Request Kopia server status from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'server_status'
        }
        
        return cls.send_command(gateway_id, command)

    # ==================== Kopia Commands ====================

    @classmethod
    def execute_kopia_command(cls, gateway_id: str, repository_id: str,
                               command: str, args: list = None) -> str:
        """
        Send Kopia command execution request to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            command: Kopia command to execute (e.g., 'snapshot list')
            args: Additional command arguments
            
        Returns:
            task_id: UUID of the task for tracking
        """
        cmd = {
            'type': 'kopia_command',
            'repository_id': repository_id,
            'command': command,
            'args': args or []
        }
        
        task_id = cls.send_command(gateway_id, cmd)
        
        # Audit log
        AuditService.log_gateway_kopia_command(gateway_id, command)
        
        return task_id

    @classmethod
    def list_snapshots(cls, gateway_id: str, repository_id: str) -> str:
        """
        Request snapshot list from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            
        Returns:
            task_id: UUID of the task for tracking
        """
        return cls.execute_kopia_command(gateway_id, repository_id, 'snapshot list')

    @classmethod
    def get_repository_stats(cls, gateway_id: str, repository_id: str) -> str:
        """
        Request repository statistics from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            
        Returns:
            task_id: UUID of the task for tracking
        """
        return cls.execute_kopia_command(gateway_id, repository_id, 'repository stats')

    @classmethod
    def get_snapshot_verify(cls, gateway_id: str, repository_id: str,
                            snapshot_id: str = None) -> str:
        """
        Request snapshot verification from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            snapshot_id: Optional specific snapshot to verify
            
        Returns:
            task_id: UUID of the task for tracking
        """
        args = ['--verify-files-percent=5']
        if snapshot_id:
            args.append(f'--snapshot-id={snapshot_id}')
            
        return cls.execute_kopia_command(gateway_id, repository_id, 'snapshot verify', args)

    # ==================== Repository Initialization ====================

    @classmethod
    def init_repository(cls, gateway_id: str, repository_id: str,
                        storage_path: str, password: str) -> str:
        """
        Send repository initialization command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            storage_path: Path to storage location
            password: Repository password
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'init_repository',
            'repository_id': repository_id,
            'storage_path': storage_path,
            'password': password
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_repository_initialize(repository_id, gateway_id)
        
        return task_id

    @classmethod
    def connect_repository(cls, gateway_id: str, repository_id: str,
                           storage_path: str, password: str) -> str:
        """
        Send repository connection command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            storage_path: Path to storage location
            password: Repository password
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'connect_repository',
            'repository_id': repository_id,
            'storage_path': storage_path,
            'password': password
        }
        
        return cls.send_command(gateway_id, command)

    # ==================== Indexing Operations ====================

    @classmethod
    def start_indexing(cls, gateway_id: str, repository_id: str,
                       paths: list = None) -> str:
        """
        Send start indexing command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            repository_id: UUID of the repository
            paths: Optional list of paths to index
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'index_start',
            'repository_id': repository_id,
            'paths': paths
        }
        
        return cls.send_command(gateway_id, command)

    @classmethod
    def index_snapshot(
        cls,
        gateway_id: str,
        job_id: str,
        snapshot_id: str,
        kopia_snapshot_id: str,
        object_id: str,
        repository_config: dict,
        password: str,
    ) -> str:
        """Send snapshot indexing command to gateway."""
        command = {
            'type': 'index_snapshot',
            'job_id': job_id,
            'snapshot_id': snapshot_id,
            'kopia_snapshot_id': kopia_snapshot_id,
            'object_id': object_id,
            'repository': repository_config,
            'password': password,
        }
        return cls.send_command(gateway_id, command)

    @classmethod
    def stop_indexing(cls, gateway_id: str) -> str:
        """
        Send stop indexing command to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'index_stop'
        }
        
        return cls.send_command(gateway_id, command)

    @classmethod
    def get_index_status(cls, gateway_id: str) -> str:
        """
        Request indexing status from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'index_status'
        }
        
        return cls.send_command(gateway_id, command)

    # ==================== AI Query Operations ====================

    @classmethod
    def ai_query(
        cls,
        gateway_id: str,
        query: str,
        query_id: str = None,
        context: dict = None,
        repository_ids: list = None,
        repository_config: dict = None,
        repository_password: str = '',
        ai_provider_config: dict = None,
    ) -> str:
        """
        Send AI query to gateway.
        
        Args:
            gateway_id: UUID of the gateway
            query: Query string
            context: Optional context for the query
            repository_ids: Optional list of repositories to search
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'ai_query',
            'query_id': query_id,
            'query': query,
            'context': context,
            'repository_ids': repository_ids,
            'repository': repository_config or {},
            'password': repository_password or '',
            'ai_provider_config': ai_provider_config or {},
        }
        
        task_id = cls.send_command(gateway_id, command)
        
        # Audit log
        AuditService.log_gateway_ai_query(gateway_id, query)
        
        return task_id

    @classmethod
    def ai_summarize_snapshot(
        cls,
        gateway_id: str,
        job_id: str,
        snapshot_id: str,
        snapshot_context: dict,
        language: str = 'zh-CN',
        ai_provider_config: dict = None,
        repository_config: dict = None,
        repository_password: str = '',
    ) -> str:
        """Send snapshot AI summary command to gateway."""
        command = {
            'type': 'ai_summarize_snapshot',
            'job_id': job_id,
            'snapshot_id': snapshot_id,
            'snapshot_context': snapshot_context,
            'language': language,
            'ai_provider_config': ai_provider_config or {},
            'repository': repository_config or {},
            'password': repository_password or '',
        }
        return cls.send_command(gateway_id, command)

    # ==================== System Operations ====================

    @classmethod
    def get_system_info(cls, gateway_id: str) -> str:
        """
        Request system info from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'system_info'
        }
        
        return cls.send_command(gateway_id, command)

    @classmethod
    def get_stats(cls, gateway_id: str) -> str:
        """
        Request statistics report from gateway.
        
        Args:
            gateway_id: UUID of the gateway
            
        Returns:
            task_id: UUID of the task for tracking
        """
        command = {
            'type': 'get_stats'
        }
        
        return cls.send_command(gateway_id, command)
