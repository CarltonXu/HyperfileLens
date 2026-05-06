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
            task_data: Task payload
            
        Returns:
            ProxyTask: Created task instance
        """
        from .models import ProxyTask
        
        task = ProxyTask.objects.create(
            id=task_data.get('task_id', str(uuid.uuid4())),
            proxy_id=proxy_id,
            task_type=task_type,
            payload=task_data,
            status=ProxyTask.TaskStatus.PENDING,
        )
        
        logger.info(f"[ProxyService] Created proxy task: {task.id} (type={task_type})")
        
        return task
