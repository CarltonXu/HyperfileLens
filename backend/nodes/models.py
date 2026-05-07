"""
Proxy Node Models for HyperFileLens

This module defines models for Proxy nodes with dual roles (agent/sync),
including connection management, health monitoring, and installation tracking.
"""

from django.db import models
from django.utils import timezone
from accounts.models import User
import uuid
import secrets


class ProxyNode(models.Model):
    """
    Proxy Node model with dual roles: agent and sync.

    Agent Proxy: Runs on production systems, reads local filesystem,
                 executes backup tasks, reports status.
    Sync Proxy:  Runs on standalone nodes/jump hosts, mounts NAS,
                 provides unified data access point, executes backup tasks.
    """

    class Role(models.TextChoices):
        """Proxy role enumeration."""
        AGENT = 'agent', 'Agent Proxy'
        SYNC = 'sync', 'Sync Proxy'

    class NodeStatus(models.TextChoices):
        """Node status enumeration."""
        PENDING = 'pending', 'Pending Installation'
        INSTALLING = 'installing', 'Installing'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        OFFLINE = 'offline', 'Offline'
        ERROR = 'error', 'Error'
        MAINTENANCE = 'maintenance', 'Maintenance'

    class OperatingSystem(models.TextChoices):
        """Supported operating systems."""
        WINDOWS = 'windows', 'Windows'
        LINUX = 'linux', 'Linux'
        MACOS = 'macos', 'macOS'

    # === Basic Information ===
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique identifier for the proxy'
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Display name for the proxy'
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.AGENT,
        help_text='Proxy role: agent (source-side) or sync (collector)'
    )

    # === Connection Information ===
    hostname = models.CharField(
        max_length=255,
        blank=True,
        help_text='Hostname or IP address of the proxy'
    )
    internal_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Internal IP address of the proxy'
    )

    # === Authentication ===
    api_token = models.CharField(
        max_length=64,
        unique=True,
        help_text='API token for proxy authentication'
    )

    # === System Information (reported by proxy) ===
    operating_system = models.CharField(
        max_length=20,
        choices=OperatingSystem.choices,
        blank=True,
        help_text='Operating system of the proxy'
    )
    os_version = models.CharField(
        max_length=100,
        blank=True,
        help_text='OS version details'
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text='Proxy software version'
    )
    kopia_version = models.CharField(
        max_length=50,
        blank=True,
        help_text='Kopia version installed on proxy'
    )

    # Hardware info
    cpu_cores = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of CPU cores'
    )
    memory_total = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Total memory in bytes'
    )
    disk_total = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Total disk space in bytes'
    )

    # === Status and Monitoring ===
    status = models.CharField(
        max_length=20,
        choices=NodeStatus.choices,
        default=NodeStatus.PENDING,
        help_text='Current status of the proxy'
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last heartbeat timestamp from the proxy'
    )
    heartbeat_interval = models.IntegerField(
        default=10,
        help_text='Expected heartbeat interval in seconds'
    )

    # Current metrics (updated via heartbeat)
    cpu_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Current CPU usage percentage'
    )
    memory_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Current memory usage percentage'
    )
    disk_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Current disk usage percentage'
    )
    active_tasks = models.IntegerField(
        default=0,
        help_text='Number of active tasks'
    )

    # === Capabilities ===
    capabilities = models.JSONField(
        default=dict,
        help_text='Proxy capabilities (mount_types, backup_types, etc.)'
    )

    # For Sync Proxy: mount capabilities
    mount_types = models.JSONField(
        default=list,
        blank=True,
        help_text='Supported mount types for Sync Proxy (nfs, smb, etc.)'
    )

    # === Tags and Metadata ===
    tags = models.JSONField(
        default=dict,
        help_text='Custom tags for organization'
    )
    labels = models.JSONField(
        default=list,
        blank=True,
        help_text='Labels for categorization'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Additional proxy metadata'
    )
    network_interfaces = models.JSONField(
        default=list,
        blank=True,
        help_text='Network interface information (name, IP, MAC, bytes in/out)'
    )
    network_bytes_sent = models.BigIntegerField(
        default=0,
        help_text='Total network bytes sent'
    )
    network_bytes_recv = models.BigIntegerField(
        default=0,
        help_text='Total network bytes received'
    )

    # === Installation Info ===
    install_token = models.CharField(
        max_length=64,
        blank=True,
        help_text='One-time installation token'
    )
    install_token_used = models.BooleanField(
        default=False,
        help_text='Whether the install token has been used'
    )
    target_os = models.CharField(
        max_length=20,
        choices=OperatingSystem.choices,
        default=OperatingSystem.LINUX,
        help_text='Target operating system for installation'
    )
    install_command = models.TextField(
        blank=True,
        help_text='Generated installation command'
    )
    installed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the proxy was installed'
    )
    installed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installed_proxies',
        help_text='User who initiated the installation'
    )

    # === Timestamps ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the proxy first connected'
    )

    # === Ownership ===
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_proxies',
        help_text='User who owns this proxy'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='proxies',
        help_text='Tenant this proxy belongs to'
    )

    class Meta:
        db_table = 'nodes_proxy'
        verbose_name = 'Proxy'
        verbose_name_plural = 'Proxies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'{self.name} ({self.role})'

    def is_online(self) -> bool:
        """Check if the proxy is currently online based on heartbeat."""
        if not self.last_heartbeat:
            return False
        elapsed = (timezone.now() - self.last_heartbeat).total_seconds()
        return elapsed <= (self.heartbeat_interval * 3)

    def update_status_based_on_heartbeat(self) -> bool:
        """
        Update proxy status based on heartbeat timeout.
        
        Returns True if status was changed, False otherwise.
        """
        # Don't auto-update pending, installing, maintenance, or error status
        if self.status in [
            self.NodeStatus.PENDING,
            self.NodeStatus.INSTALLING,
            self.NodeStatus.MAINTENANCE,
            self.NodeStatus.ERROR,
        ]:
            return False
        
        is_currently_online = self.is_online()
        
        # If offline but status is active/inactive, update to offline
        if not is_currently_online and self.status in [
            self.NodeStatus.ACTIVE,
            self.NodeStatus.INACTIVE,
        ]:
            self.status = self.NodeStatus.OFFLINE
            self.save(update_fields=['status', 'updated_at'])
            return True
        
        # If online but status is offline, update to active
        if is_currently_online and self.status == self.NodeStatus.OFFLINE:
            self.status = self.NodeStatus.ACTIVE
            self.save(update_fields=['status', 'updated_at'])
            return True
        
        return False

    def generate_install_token(self) -> str:
        """Generate a one-time installation token."""
        self.install_token = secrets.token_urlsafe(32)
        self.save(update_fields=['install_token', 'updated_at'])
        return self.install_token

    def generate_api_token(self) -> str:
        """Generate API token for authentication."""
        self.api_token = secrets.token_urlsafe(32)
        self.save(update_fields=['api_token', 'updated_at'])
        return self.api_token

    def update_heartbeat(self, data: dict = None) -> None:
        """Update heartbeat timestamp and metrics."""
        self.last_heartbeat = timezone.now()

        if self.status == self.NodeStatus.PENDING:
            self.status = self.NodeStatus.ACTIVE
            if not self.registered_at:
                self.registered_at = timezone.now()
            if not self.installed_at:
                self.installed_at = timezone.now()

        if data:
            # Only update fields that have non-None values
            if data.get('version') is not None:
                self.version = data['version']
            if data.get('kopia_version') is not None:
                self.kopia_version = data['kopia_version']
            if data.get('hostname') is not None:
                self.hostname = data['hostname']
            if data.get('internal_ip') is not None:
                self.internal_ip = data['internal_ip']
            if data.get('os') is not None:
                self.operating_system = data['os']
            if data.get('os_version') is not None:
                self.os_version = data['os_version']
            if data.get('cpu_cores') is not None:
                self.cpu_cores = data['cpu_cores']
            if data.get('memory_total') is not None:
                self.memory_total = data['memory_total']
            if data.get('disk_total') is not None:
                self.disk_total = data['disk_total']
            if data.get('cpu_usage') is not None:
                self.cpu_usage = data['cpu_usage']
            if data.get('memory_usage') is not None:
                self.memory_usage = data['memory_usage']
            if data.get('disk_usage') is not None:
                self.disk_usage = data['disk_usage']
            if data.get('active_tasks') is not None:
                self.active_tasks = data['active_tasks']
            if data.get('capabilities') is not None:
                self.capabilities = data['capabilities']
            if data.get('network_interfaces') is not None:
                self.network_interfaces = data['network_interfaces']
            if data.get('network_bytes_sent') is not None:
                self.network_bytes_sent = data['network_bytes_sent']
            if data.get('network_bytes_recv') is not None:
                self.network_bytes_recv = data['network_bytes_recv']

        self.save()

    def get_capabilities_display(self) -> dict:
        """Get capabilities with role-specific defaults."""
        defaults = {
            'backup': True,
            'restore': True,
            'snapshot_list': True,
        }

        if self.role == self.Role.SYNC:
            defaults.update({
                'mount_nfs': True,
                'mount_smb': True,
                'mount_s3': False,  # S3 uses native API, not mount
            })

        return {**defaults, **self.capabilities}


class ProxyHeartbeat(models.Model):
    """
    Proxy heartbeat log for tracking health over time.
    """

    proxy = models.ForeignKey(
        ProxyNode,
        on_delete=models.CASCADE,
        related_name='heartbeats',
        help_text='Proxy that sent this heartbeat'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text='Heartbeat timestamp'
    )
    cpu_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='CPU usage percentage'
    )
    memory_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Memory usage percentage'
    )
    disk_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Disk usage percentage'
    )
    network_in = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Network bytes received'
    )
    network_out = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Network bytes sent'
    )
    active_tasks = models.IntegerField(
        default=0,
        help_text='Number of active tasks'
    )
    completed_tasks = models.IntegerField(
        default=0,
        help_text='Number of completed tasks since last heartbeat'
    )
    failed_tasks = models.IntegerField(
        default=0,
        help_text='Number of failed tasks since last heartbeat'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Additional heartbeat metadata'
    )

    class Meta:
        db_table = 'nodes_proxy_heartbeat'
        verbose_name = 'Proxy Heartbeat'
        verbose_name_plural = 'Proxy Heartbeats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['proxy', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.proxy.name} @ {self.timestamp}'


class ProxyTask(models.Model):
    """
    Task assigned to a proxy for execution.
    """

    class TaskType(models.TextChoices):
        BACKUP = 'backup', 'Backup'
        RESTORE = 'restore', 'Restore'
        MOUNT = 'mount', 'Mount'
        UNMOUNT = 'unmount', 'Unmount'
        SNAPSHOT_LIST = 'snapshot_list', 'Snapshot List'
        VERIFY = 'verify', 'Verify'
        TEST_STORAGE = 'test_storage', 'Test Storage'
        INIT_REPOSITORY = 'init_repository', 'Init Repository'

    class TaskStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DISPATCHED = 'dispatched', 'Dispatched'
        ACCEPTED = 'accepted', 'Accepted'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        TIMEOUT = 'timeout', 'Timeout'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    proxy = models.ForeignKey(
        ProxyNode,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text='Proxy assigned to execute the task'
    )
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        help_text='Type of task'
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        help_text='Task status'
    )

    # Task parameters
    parameters = models.JSONField(
        default=dict,
        help_text='Task parameters'
    )

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When task was dispatched to proxy'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When task execution started'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When task completed'
    )
    timeout_seconds = models.IntegerField(
        default=3600,
        help_text='Task timeout in seconds'
    )

    # Progress and results
    progress = models.IntegerField(
        default=0,
        help_text='Task progress percentage (0-100)'
    )
    progress_message = models.TextField(
        blank=True,
        help_text='Progress status message'
    )
    result = models.JSONField(
        default=dict,
        blank=True,
        help_text='Task execution result'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Error message if task failed'
    )

    # Related objects
    repository_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='Related repository ID'
    )
    source_resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='Related source resource ID'
    )

    class Meta:
        db_table = 'nodes_proxy_task'
        verbose_name = 'Proxy Task'
        verbose_name_plural = 'Proxy Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['proxy', 'status']),
            models.Index(fields=['task_type', 'status']),
        ]

    def __str__(self):
        return f'{self.task_type} - {self.proxy.name} ({self.status})'

    def dispatch(self) -> None:
        """Mark task as dispatched."""
        self.status = self.TaskStatus.DISPATCHED
        self.dispatched_at = timezone.now()
        self.save()

    def accept(self) -> None:
        """Mark task as accepted by proxy."""
        self.status = self.TaskStatus.ACCEPTED
        self.started_at = timezone.now()
        self.save()

    def start(self) -> None:
        """Mark task as running."""
        self.status = self.TaskStatus.RUNNING
        self.started_at = timezone.now()
        self.save()

    def complete(self, result: dict = None) -> None:
        """Mark task as completed."""
        self.status = self.TaskStatus.COMPLETED
        self.completed_at = timezone.now()
        self.progress = 100
        if result:
            self.result = result
        self.save()

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = self.TaskStatus.FAILED
        self.completed_at = timezone.now()
        self.error_message = error
        self.save()

    def cancel(self) -> None:
        """Cancel the task."""
        self.status = self.TaskStatus.CANCELLED
        self.completed_at = timezone.now()
        self.save()


# Keep old Node model for backwards compatibility during migration
class Node(ProxyNode):
    """Alias for backwards compatibility."""

    class Meta:
        proxy = True
        verbose_name = 'Node (Legacy)'
        verbose_name_plural = 'Nodes (Legacy)'


class NodeHeartbeat(ProxyHeartbeat):
    """Alias for backwards compatibility."""

    class Meta:
        proxy = True
        verbose_name = 'Node Heartbeat (Legacy)'
        verbose_name_plural = 'Node Heartbeats (Legacy)'


class NodeConnection(models.Model):
    """
    WebSocket connection record for tracking active connections.
    """

    class ConnectionStatus(models.TextChoices):
        CONNECTED = 'connected', 'Connected'
        DISCONNECTED = 'disconnected', 'Disconnected'
        ERROR = 'error', 'Error'

    proxy = models.ForeignKey(
        ProxyNode,
        on_delete=models.CASCADE,
        related_name='connections',
        help_text='Connected proxy'
    )
    connection_id = models.UUIDField(
        default=uuid.uuid4,
        help_text='Unique connection identifier'
    )
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.CONNECTED,
        help_text='Connection status'
    )
    remote_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Remote client IP address'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Client user agent'
    )
    connected_at = models.DateTimeField(
        default=timezone.now,
        help_text='Connection start time'
    )
    disconnected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Connection end time'
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last message received/sent time'
    )
    message_count = models.BigIntegerField(
        default=0,
        help_text='Total messages exchanged'
    )

    class Meta:
        db_table = 'nodes_connection'
        verbose_name = 'Proxy Connection'
        verbose_name_plural = 'Proxy Connections'
        ordering = ['-connected_at']
        indexes = [
            models.Index(fields=['proxy', 'status']),
            models.Index(fields=['connection_id']),
        ]

    def __str__(self):
        return f'{self.proxy.name} - {self.connection_id}'

    def disconnect(self) -> None:
        """Mark the connection as disconnected."""
        self.status = self.ConnectionStatus.DISCONNECTED
        self.disconnected_at = timezone.now()
        self.save()
