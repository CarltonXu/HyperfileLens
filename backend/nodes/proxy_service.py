"""
HyperFileLens Backend - Proxy Service

Service layer for sending commands to proxy nodes via WebSocket.
Provides async methods for:
- Testing storage connectivity
- Initializing Kopia repository
- Sending backup/restore tasks
"""

import json
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class ProxyService:
    """
    Service for communicating with proxy nodes via WebSocket.
    
    Uses Django Channels layer to send messages to connected proxies.
    """
    
    @staticmethod
    def get_channel_layer():
        """Get the channel layer instance."""
        return get_channel_layer()
    
    @staticmethod
    def is_proxy_online(proxy_id: str) -> bool:
        """
        Check if a proxy is currently online.
        
        This checks the database status field, which is automatically updated
        based on heartbeat timeout.
        
        Args:
            proxy_id: UUID of the proxy node
            
        Returns:
            bool: True if proxy status is ONLINE
        """
        from .models import ProxyNode
        
        try:
            proxy = ProxyNode.objects.get(id=proxy_id)
            
            # Update status based on heartbeat (may change to OFFLINE if timeout)
            proxy.update_status_based_on_heartbeat()
            
            # Refresh from database if status was updated
            proxy.refresh_from_db()
            
            # Check if status is ONLINE
            return proxy.status == ProxyNode.NodeStatus.ONLINE
            
        except ProxyNode.DoesNotExist:
            logger.warning(f"[ProxyService] Proxy {proxy_id} not found")
            return False
    
    @staticmethod
    def check_proxy_connectivity(proxy_id: str, raise_exception: bool = False) -> tuple[bool, str]:
        """
        Check if a proxy is reachable and can receive commands.
        Also updates the proxy status if heartbeat timeout is detected.
        
        Args:
            proxy_id: UUID of the proxy node
            raise_exception: If True, raise an exception instead of returning False
            
        Returns:
            tuple: (is_online: bool, error_message: str)
            
        Raises:
            ValueError: If proxy is offline and raise_exception is True
        """
        from .models import ProxyNode
        
        try:
            proxy = ProxyNode.objects.get(id=proxy_id)
        except ProxyNode.DoesNotExist:
            error_msg = f"Proxy {proxy_id} does not exist"
            if raise_exception:
                raise ValueError(error_msg)
            return False, error_msg
        
        # Update status based on heartbeat (may change to OFFLINE if timeout)
        proxy.update_status_based_on_heartbeat()
        proxy.refresh_from_db()
        
        # Check if status is ONLINE
        if proxy.status != ProxyNode.NodeStatus.ONLINE:
            error_msg = f"Proxy '{proxy.name}' is not online (status: {proxy.get_status_display()})"
            if raise_exception:
                raise ValueError(error_msg)
            return False, error_msg
        
        logger.info(f"[ProxyService] Proxy {proxy_id} ({proxy.name}) connectivity check passed")
        return True, ""
    
    @staticmethod
    def send_to_proxy(proxy_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific proxy via WebSocket.
        
        Args:
            proxy_id: UUID of the proxy node
            message: Message dictionary to send
            
        Returns:
            bool: True if message was sent successfully
        """
        channel_layer = ProxyService.get_channel_layer()
        if not channel_layer:
            logger.error("[ProxyService] Channel layer not available")
            return False
        
        group_name = f'proxy_{proxy_id}'
        
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'command_message',
                    'data': message
                }
            )
            logger.info(f"[ProxyService] Sent message to proxy {proxy_id}: type={message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"[ProxyService] Failed to send message to proxy {proxy_id}: {e}")
            return False
    
    @staticmethod
    def send_test_storage_command(
        proxy_id: str,
        repository_id: str,
        storage_type: str,
        storage_config: Dict[str, Any],
        test_write: bool = True,
        task_id: Optional[str] = None
    ) -> str:
        """
        Send a storage test command to a Sync Proxy.
        
        Args:
            proxy_id: UUID of the Sync Proxy
            repository_id: UUID of the repository
            storage_type: Type of storage ('nas', 'nfs', 'smb', 's3', 'local')
            storage_config: Configuration for the storage
            test_write: Whether to test write operations
            task_id: Optional task ID (auto-generated if not provided)
            
        Returns:
            str: Task ID for tracking the operation
        """
        task_id = task_id or str(uuid.uuid4())
        
        message = {
            'type': 'test_storage',
            'id': str(uuid.uuid4()),
            'task_id': task_id,
            'repository_id': repository_id,
            'storage_type': storage_type,
            'test_write': test_write,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Add storage-specific configuration
        if storage_type in ('nas', 'nfs'):
            message.update({
                'server': storage_config.get('server', ''),
                'path': storage_config.get('path', ''),
                'mount_type': storage_config.get('mount_type', 'nfs'),
                'mount_path': storage_config.get('mount_path', ''),
            })
        elif storage_type == 'smb':
            message.update({
                'server': storage_config.get('server', ''),
                'share': storage_config.get('share', ''),
                'username': storage_config.get('username', ''),
                'password': storage_config.get('password', ''),
                'mount_path': storage_config.get('mount_path', ''),
            })
        elif storage_type == 'local':
            message.update({
                'path': storage_config.get('path', ''),
            })
        elif storage_type == 's3':
            message.update({
                'endpoint': storage_config.get('endpoint', ''),
                'bucket': storage_config.get('bucket', ''),
                'region': storage_config.get('region', 'us-east-1'),
                'access_key': storage_config.get('access_key', ''),
                'secret_key': storage_config.get('secret_key', ''),
            })
        
        ProxyService.send_to_proxy(proxy_id, message)
        
        logger.info(
            f"[ProxyService] Sent test_storage command to proxy {proxy_id}: "
            f"repository={repository_id}, type={storage_type}, task_id={task_id}"
        )
        
        return task_id
    
    @staticmethod
    def send_init_repository_command(
        proxy_id: str,
        repository_id: str,
        repository_config: Dict[str, Any],
        password: str,
        task_id: Optional[str] = None
    ) -> str:
        """
        Send a repository initialization command to a Sync Proxy.
        
        Args:
            proxy_id: UUID of the Sync Proxy
            repository_id: UUID of the repository
            repository_config: Repository configuration (type, path, etc.)
            password: Repository encryption password
            task_id: Optional task ID (auto-generated if not provided)
            
        Returns:
            str: Task ID for tracking the operation
        """
        task_id = task_id or str(uuid.uuid4())
        
        message = {
            'type': 'init_repository',
            'id': str(uuid.uuid4()),
            'task_id': task_id,
            'repository_id': repository_id,
            'repository': repository_config,
            'password': password,
            'timestamp': timezone.now().isoformat(),
        }
        
        ProxyService.send_to_proxy(proxy_id, message)
        
        logger.info(
            f"[ProxyService] Sent init_repository command to proxy {proxy_id}: "
            f"repository={repository_id}, task_id={task_id}"
        )
        
        return task_id
    
    @staticmethod
    def send_mount_command(
        proxy_id: str,
        mount_type: str,
        mount_config: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> str:
        """
        Send a mount command to a Sync Proxy.
        
        Args:
            proxy_id: UUID of the Sync Proxy
            mount_type: Type of mount ('nfs', 'smb')
            mount_config: Mount configuration
            task_id: Optional task ID (auto-generated if not provided)
            
        Returns:
            str: Task ID for tracking the operation
        """
        task_id = task_id or str(uuid.uuid4())
        
        message = {
            'type': 'mount',
            'id': str(uuid.uuid4()),
            'task_id': task_id,
            'mount_type': mount_type,
            'timestamp': timezone.now().isoformat(),
        }
        
        if mount_type == 'nfs':
            message.update({
                'server': mount_config.get('server', ''),
                'path': mount_config.get('path', ''),
                'target': mount_config.get('target', ''),
            })
        elif mount_type == 'smb':
            message.update({
                'server': mount_config.get('server', ''),
                'share': mount_config.get('share', ''),
                'target': mount_config.get('target', ''),
                'username': mount_config.get('username', ''),
                'password': mount_config.get('password', ''),
            })
        
        ProxyService.send_to_proxy(proxy_id, message)
        
        logger.info(
            f"[ProxyService] Sent mount command to proxy {proxy_id}: "
            f"type={mount_type}, task_id={task_id}"
        )
        
        return task_id
    
    @staticmethod
    def create_proxy_task(proxy_id: str, task_type: str, task_data: Dict[str, Any]) -> 'ProxyTask':
        """
        Create a ProxyTask record for tracking.
        
        Args:
            proxy_id: UUID of the proxy
            task_type: Type of task
            task_data: Task payload (will be stored as parameters)
            
        Returns:
            ProxyTask: Created task instance
        """
        from .models import ProxyTask
        
        task_id = task_data.get('task_id') or str(uuid.uuid4())
        
        task = ProxyTask.objects.create(
            id=task_id,
            proxy_id=proxy_id,
            task_type=task_type,
            parameters=task_data,
            status=ProxyTask.TaskStatus.PENDING,
        )
        
        logger.info(f"[ProxyService] Created proxy task: {task.id} (type={task_type})")
        
        return task
    
    @staticmethod
    def send_task_to_proxy(
        proxy_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        check_online: bool = True
    ) -> tuple[Optional['ProxyTask'], str]:
        """
        Create a task and send it to the proxy via WebSocket.
        
        This is the recommended way to send commands to proxies.
        It creates a ProxyTask record first, then sends the command.
        
        Args:
            proxy_id: UUID of the proxy
            task_type: Type of task (e.g., 'test_storage', 'init_repository')
            task_data: Task parameters
            check_online: Whether to check proxy connectivity first
            
        Returns:
            tuple: (ProxyTask or None, error_message or "")
        """
        from .models import ProxyNode
        
        # Check proxy connectivity
        if check_online:
            is_online, error_msg = ProxyService.check_proxy_connectivity(proxy_id)
            if not is_online:
                return None, error_msg
        
        # Create task record
        task = ProxyService.create_proxy_task(proxy_id, task_type, task_data)
        
        # Send to proxy
        message = {
            'type': task_type,
            'task_id': str(task.id),
            'timestamp': timezone.now().isoformat(),
            **task_data
        }
        
        success = ProxyService.send_to_proxy(proxy_id, message)
        
        if success:
            logger.info(
                f"[ProxyService] Sent task {task.id} to proxy {proxy_id}: "
                f"type={task_type}"
            )
            return task, ""
        else:
            # Mark task as failed
            task.fail("Failed to send command to proxy")
            return task, "Failed to send command to proxy"
