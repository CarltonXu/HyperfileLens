"""
Node Models for HyperFileLens

This module defines models for source proxy nodes and target gateway nodes,
including connection management and health monitoring.
"""

from django.db import models
from django.utils import timezone
from accounts.models import User
import uuid


class Node(models.Model):
    """
    Base model for all nodes (source proxies and target gateways).

    This model stores common node information and status.
    """

    class NodeType(models.TextChoices):
        """Node type enumeration."""
        SOURCE_PROXY = 'source_proxy', 'Source Proxy'
        TARGET_GATEWAY = 'target_gateway', 'Target Gateway'

    class NodeStatus(models.TextChoices):
        """Node status enumeration."""
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        ERROR = 'error', 'Error'
        MAINTENANCE = 'maintenance', 'Maintenance'

    class OperatingSystem(models.TextChoices):
        """Supported operating systems."""
        WINDOWS = 'windows', 'Windows'
        LINUX = 'linux', 'Linux'
        MACOS = 'macos', 'macOS'

    # Basic information
    node_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Unique identifier for the node'
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Display name for the node'
    )
    node_type = models.CharField(
        max_length=20,
        choices=NodeType.choices,
        help_text='Type of node (source proxy or target gateway)'
    )

    # Connection information
    hostname = models.CharField(
        max_length=255,
        help_text='Hostname or IP address of the node'
    )
    port = models.IntegerField(
        default=8080,
        help_text='Port number for node communication'
    )
    protocol = models.CharField(
        max_length=10,
        default='https',
        help_text='Protocol for node communication (http/https)'
    )

    # Authentication
    api_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='API key for node authentication'
    )
    api_secret = models.CharField(
        max_length=128,
        blank=True,
        help_text='API secret for node authentication (encrypted)'
    )

    # System information
    operating_system = models.CharField(
        max_length=20,
        choices=OperatingSystem.choices,
        help_text='Operating system of the node'
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text='Node software version'
    )
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

    # Status and monitoring
    status = models.CharField(
        max_length=20,
        choices=NodeStatus.choices,
        default=NodeStatus.PENDING,
        help_text='Current status of the node'
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last heartbeat timestamp from the node'
    )
    heartbeat_interval = models.IntegerField(
        default=30,
        help_text='Expected heartbeat interval in seconds'
    )

    # Capabilities
    capabilities = models.JSONField(
        default=dict,
        help_text='Node capabilities and supported features'
    )

    # Tags and metadata
    tags = models.JSONField(
        default=dict,
        help_text='Custom tags for organization'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Additional node metadata'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the node was registered and activated'
    )

    # Ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_nodes',
        help_text='User who owns this node'
    )

    class Meta:
        db_table = 'nodes_node'
        verbose_name = 'Node'
        verbose_name_plural = 'Nodes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['node_id']),
            models.Index(fields=['name']),
            models.Index(fields=['node_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.name} ({self.node_type})'

    def is_online(self) -> bool:
        """
        Check if the node is currently online based on heartbeat.

        Returns:
            True if last heartbeat was within the expected interval, False otherwise
        """
        if not self.last_heartbeat:
            return False
        elapsed = (timezone.now() - self.last_heartbeat).total_seconds()
        return elapsed <= (self.heartbeat_interval * 3)

    def update_heartbeat(self) -> None:
        """
        Update the last heartbeat timestamp to the current time.
        """
        self.last_heartbeat = timezone.now()
        if self.status == NodeStatus.PENDING:
            self.status = NodeStatus.ACTIVE
            self.registered_at = timezone.now()
        self.save(update_fields=['last_heartbeat', 'status', 'updated_at'])

    def update_status(self, status: str) -> None:
        """
        Update the node status.

        Args:
            status: New status value
        """
        self.status = status
        self.save(update_fields=['status', 'updated_at'])

    def get_connection_url(self) -> str:
        """
        Get the full connection URL for the node.

        Returns:
            Full URL for node communication
        """
        return f'{self.protocol}://{self.hostname}:{self.port}'


class SourceProxyNode(Node):
    """
    Source proxy node model.

    Represents a node that runs on production systems to
    scan files and execute backup/recovery tasks.
    """

    class Meta:
        proxy = True
        verbose_name = 'Source Proxy Node'
        verbose_name_plural = 'Source Proxy Nodes'

    def __str__(self):
        return f'Source Proxy: {self.name}'

    def save(self, *args, **kwargs):
        """
        Ensure node_type is set to source_proxy.
        """
        self.node_type = Node.NodeType.SOURCE_PROXY
        super().save(*args, **kwargs)


class TargetGatewayNode(Node):
    """
    Target gateway node model.

    Represents a node that runs on the DR/backup side to
    receive backup data and execute recovery tasks.
    """

    class Meta:
        proxy = True
        verbose_name = 'Target Gateway Node'
        verbose_name_plural = 'Target Gateway Nodes'

    def __str__(self):
        return f'Target Gateway: {self.name}'

    def save(self, *args, **kwargs):
        """
        Ensure node_type is set to target_gateway.
        """
        self.node_type = Node.NodeType.TARGET_GATEWAY
        super().save(*args, **kwargs)


class NodeHeartbeat(models.Model):
    """
    Node heartbeat log for tracking node health over time.
    """

    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='heartbeats',
        help_text='Node that sent this heartbeat'
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
        help_text='Number of active tasks on the node'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Additional heartbeat metadata'
    )

    class Meta:
        db_table = 'nodes_heartbeat'
        verbose_name = 'Node Heartbeat'
        verbose_name_plural = 'Node Heartbeats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['node', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.node.name} @ {self.timestamp}'


class NodeConnection(models.Model):
    """
    WebSocket connection record for tracking active connections.
    """

    class ConnectionStatus(models.TextChoices):
        """Connection status enumeration."""
        CONNECTED = 'connected', 'Connected'
        DISCONNECTED = 'disconnected', 'Disconnected'
        ERROR = 'error', 'Error'

    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='connections',
        help_text='Connected node'
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
        verbose_name = 'Node Connection'
        verbose_name_plural = 'Node Connections'
        ordering = ['-connected_at']
        indexes = [
            models.Index(fields=['node', 'status']),
            models.Index(fields=['connection_id']),
        ]

    def __str__(self):
        return f'{self.node.name} - {self.connection_id}'

    def disconnect(self) -> None:
        """
        Mark the connection as disconnected.
        """
        self.status = self.ConnectionStatus.DISCONNECTED
        self.disconnected_at = timezone.now()
        self.save()


class NodeTaskAssignment(models.Model):
    """
    Model for tracking task assignments to nodes.

    Records which node is assigned to execute a specific task.
    """

    class AssignmentStatus(models.TextChoices):
        """Assignment status enumeration."""
        PENDING = 'pending', 'Pending'
        ASSIGNED = 'assigned', 'Assigned'
        ACCEPTED = 'accepted', 'Accepted'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    task_id = models.UUIDField(
        help_text='Unique identifier of the assigned task'
    )
    task_type = models.CharField(
        max_length=50,
        help_text='Type of task (backup, recovery, etc.)'
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name='task_assignments',
        help_text='Node assigned to execute the task'
    )
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
        help_text='Assignment status'
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the task was assigned'
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the node accepted the task'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the task execution started'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the task completed'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Task progress percentage (0-100)'
    )
    result = models.JSONField(
        default=dict,
        blank=True,
        help_text='Task execution result'
    )
    error = models.TextField(
        blank=True,
        help_text='Error message if task failed'
    )

    class Meta:
        db_table = 'nodes_task_assignment'
        verbose_name = 'Node Task Assignment'
        verbose_name_plural = 'Node Task Assignments'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['node', 'status']),
        ]

    def __str__(self):
        return f'{self.task_type} - {self.node.name} ({self.status})'
