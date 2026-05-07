"""
Gateway Models for HyperFileLens

Gateway nodes are independent installation nodes that:
1. Use Kopia to mount backup data
2. Provide AI Insights capabilities for data analysis
3. Run on Ubuntu 22.04
"""

from django.db import models
from django.utils import timezone
from accounts.models import User
import uuid
import secrets


class Gateway(models.Model):
    """
    Gateway Node model for mounting backup data and providing AI analysis.
    
    Gateways are independent nodes that:
    - Mount backup repositories via Kopia
    - Provide data access for AI Insights
    - Run exclusively on Ubuntu 22.04
    """

    class GatewayStatus(models.TextChoices):
        """Gateway status enumeration."""
        PENDING = 'pending', 'Pending Installation'
        INSTALLING = 'installing', 'Installing'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        OFFLINE = 'offline', 'Offline'
        ERROR = 'error', 'Error'
        MAINTENANCE = 'maintenance', 'Maintenance'

    # === Basic Information ===
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique identifier for the gateway'
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Display name for the gateway'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of the gateway'
    )

    # === Connection Information ===
    hostname = models.CharField(
        max_length=255,
        blank=True,
        help_text='Hostname or IP address of the gateway'
    )
    internal_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Internal IP address of the gateway'
    )
    ssh_port = models.IntegerField(
        default=22,
        help_text='SSH port for remote access'
    )

    # === Authentication ===
    api_token = models.CharField(
        max_length=64,
        unique=True,
        help_text='API token for gateway authentication'
    )

    # === System Information (reported by gateway) ===
    os_version = models.CharField(
        max_length=100,
        blank=True,
        default='Ubuntu 22.04',
        help_text='OS version (always Ubuntu 22.04 for gateways)'
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text='Gateway software version'
    )
    kopia_version = models.CharField(
        max_length=50,
        blank=True,
        help_text='Kopia version installed on gateway'
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
        choices=GatewayStatus.choices,
        default=GatewayStatus.PENDING,
        help_text='Current status of the gateway'
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last heartbeat timestamp from the gateway'
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
    active_mounts = models.IntegerField(
        default=0,
        help_text='Number of active Kopia mounts'
    )

    # === Mount Configuration ===
    mount_base_path = models.CharField(
        max_length=255,
        default='/mnt/kopia',
        help_text='Base path for Kopia mounts'
    )
    max_concurrent_mounts = models.IntegerField(
        default=10,
        help_text='Maximum concurrent mounts allowed'
    )

    # === Capabilities ===
    capabilities = models.JSONField(
        default=dict,
        help_text='Gateway capabilities'
    )

    # === AI Insights Configuration ===
    ai_enabled = models.BooleanField(
        default=True,
        help_text='Whether AI Insights is enabled on this gateway'
    )
    indexer_status = models.CharField(
        max_length=20,
        blank=True,
        help_text='Status of the indexer service'
    )
    last_index_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time data was indexed'
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
        help_text='Additional gateway metadata'
    )

    # Network info
    network_interfaces = models.JSONField(
        default=list,
        blank=True,
        help_text='Network interface information'
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
    install_command = models.TextField(
        blank=True,
        help_text='Generated installation command'
    )
    installed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the gateway was installed'
    )
    installed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installed_gateways',
        help_text='User who initiated the installation'
    )

    # === Timestamps ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the gateway first connected'
    )

    # === Ownership ===
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_gateways',
        help_text='User who owns this gateway'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='gateways',
        help_text='Tenant this gateway belongs to'
    )

    class Meta:
        db_table = 'gateways_gateway'
        verbose_name = 'Gateway'
        verbose_name_plural = 'Gateways'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'{self.name}'

    def is_online(self) -> bool:
        """Check if the gateway is currently online based on heartbeat."""
        if not self.last_heartbeat:
            return False
        elapsed = (timezone.now() - self.last_heartbeat).total_seconds()
        return elapsed <= (self.heartbeat_interval * 3)

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
        if data:
            self.hostname = data.get('hostname', self.hostname)
            self.internal_ip = data.get('internal_ip', self.internal_ip)
            self.version = data.get('version', self.version)
            self.kopia_version = data.get('kopia_version', self.kopia_version)
            self.cpu_cores = data.get('cpu_cores', self.cpu_cores)
            self.memory_total = data.get('memory_total', self.memory_total)
            self.disk_total = data.get('disk_total', self.disk_total)
            self.cpu_usage = data.get('cpu_usage', self.cpu_usage)
            self.memory_usage = data.get('memory_usage', self.memory_usage)
            self.disk_usage = data.get('disk_usage', self.disk_usage)
            self.active_mounts = data.get('active_mounts', self.active_mounts)
            self.network_interfaces = data.get('network_interfaces', self.network_interfaces)
            self.network_bytes_sent = data.get('network_bytes_sent', self.network_bytes_sent)
            self.network_bytes_recv = data.get('network_bytes_recv', self.network_bytes_recv)
            self.capabilities = data.get('capabilities', self.capabilities)
        self.save()

    def get_install_command(self) -> str:
        """Generate installation command for the gateway."""
        if not self.install_token:
            self.generate_install_token()
        
        # Get server URL from settings
        from django.conf import settings
        server_url = getattr(settings, 'GATEWAY_SERVER_URL', 'http://localhost:8000')
        
        return f'''# Gateway Installation Script for Ubuntu 22.04
# Run this script on your Ubuntu 22.04 server

# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y curl wget unzip

# 3. Download and install the Gateway agent
curl -sSL https://get.hyperfilelens.com/install-gateway.sh | bash -s -- \\
  --server {server_url} \\
  --token {self.install_token} \\
  --name "{self.name}"

# After installation, the gateway will automatically register with the control plane.
# You can check the status with:
# systemctl status hyperfilelens-gateway
'''

    def to_dict(self):
        """Convert gateway to dictionary representation."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'hostname': self.hostname,
            'internal_ip': self.internal_ip,
            'ssh_port': self.ssh_port,
            'status': self.status,
            'os_version': self.os_version,
            'version': self.version,
            'kopia_version': self.kopia_version,
            'cpu_cores': self.cpu_cores,
            'memory_total': self.memory_total,
            'disk_total': self.disk_total,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'active_mounts': self.active_mounts,
            'mount_base_path': self.mount_base_path,
            'max_concurrent_mounts': self.max_concurrent_mounts,
            'ai_enabled': self.ai_enabled,
            'indexer_status': self.indexer_status,
            'last_index_time': self.last_index_time.isoformat() if self.last_index_time else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'is_online': self.is_online(),
            'tags': self.tags,
            'labels': self.labels,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
        }


class GatewayHeartbeat(models.Model):
    """
    Gateway Heartbeat history for monitoring and analytics.
    Stores periodic metrics from gateway nodes.
    """

    gateway = models.ForeignKey(
        Gateway,
        on_delete=models.CASCADE,
        related_name='heartbeats',
        help_text='Gateway this heartbeat belongs to'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When this heartbeat was received'
    )

    # System metrics
    cpu_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='CPU usage percentage at this heartbeat'
    )
    memory_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Memory usage percentage at this heartbeat'
    )
    disk_usage = models.FloatField(
        null=True,
        blank=True,
        help_text='Disk usage percentage at this heartbeat'
    )

    # Mount info
    active_mounts = models.IntegerField(
        default=0,
        help_text='Number of active mounts at this heartbeat'
    )

    # Network metrics
    network_bytes_sent = models.BigIntegerField(
        default=0,
        help_text='Network bytes sent since last heartbeat'
    )
    network_bytes_recv = models.BigIntegerField(
        default=0,
        help_text='Network bytes received since last heartbeat'
    )

    # Additional metrics
    load_average = models.JSONField(
        null=True,
        blank=True,
        help_text='System load average (1, 5, 15 min)'
    )
    process_count = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of running processes'
    )

    class Meta:
        db_table = 'gateways_heartbeat'
        verbose_name = 'Gateway Heartbeat'
        verbose_name_plural = 'Gateway Heartbeats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['gateway', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.gateway.name} - {self.timestamp}'
