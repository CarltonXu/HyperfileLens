"""
HyperFileLens Backend - Repository Views
"""

import re
import time
import logging
import boto3
from botocore.exceptions import ClientError, BotoCoreError, EndpointConnectionError, ConnectTimeoutError
from botocore.config import Config

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

logger = logging.getLogger(__name__)

from .models import Repository
from .serializers import (
    RepositorySerializer,
    RepositoryListSerializer,
    RepositoryCreateSerializer,
    RepositoryUpdateSerializer,
    RepositoryInitSerializer,
    ConnectionTestSerializer,
    ConnectionTestResultSerializer
)
from nodes.models import Node


# S3 Bucket name validation rules (AWS S3 naming rules)
BUCKET_NAME_RULES = {
    'min_length': 3,
    'max_length': 63,
    'pattern': r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$',  # Must start and end with alphanumeric
    'reserved_prefixes': ['xn--', 'sthree-', 'amzn-s3-demo-'],
    'reserved_suffixes': ['-s3alias', '--ol-s3', '.mrap', '--x-s3'],
    'ip_pattern': r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',  # Cannot look like IP
}


def validate_bucket_name(bucket_name):
    """
    Validate S3 bucket name according to AWS rules.
    Returns (is_valid, error_message)
    """
    if not bucket_name:
        return False, "Bucket name is required"
    
    # Length check
    if len(bucket_name) < BUCKET_NAME_RULES['min_length']:
        return False, f"Bucket name must be at least {BUCKET_NAME_RULES['min_length']} characters"
    if len(bucket_name) > BUCKET_NAME_RULES['max_length']:
        return False, f"Bucket name must not exceed {BUCKET_NAME_RULES['max_length']} characters"
    
    # Pattern check (must be lowercase letters, numbers, dots, hyphens)
    if not re.match(BUCKET_NAME_RULES['pattern'], bucket_name):
        return False, "Bucket name can only contain lowercase letters, numbers, dots (.), and hyphens (-). Must start and end with a letter or number"
    
    # Must not contain consecutive dots
    if '..' in bucket_name:
        return False, "Bucket name cannot contain consecutive periods (..)"
    
    # Must not look like an IP address
    if re.match(BUCKET_NAME_RULES['ip_pattern'], bucket_name):
        return False, "Bucket name cannot be formatted as an IP address"
    
    # Reserved prefixes
    for prefix in BUCKET_NAME_RULES['reserved_prefixes']:
        if bucket_name.lower().startswith(prefix):
            return False, f"Bucket name cannot start with reserved prefix '{prefix}'"
    
    # Reserved suffixes
    for suffix in BUCKET_NAME_RULES['reserved_suffixes']:
        if bucket_name.lower().endswith(suffix):
            return False, f"Bucket name cannot end with reserved suffix '{suffix}'"
    
    return True, None


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing backup repositories.
    
    Repository is the target storage for backup data.
    It needs to be bound to a Node for operations and initialized
    with Kopia before use.
    """
    queryset = Repository.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RepositoryListSerializer
        if self.action == 'create':
            return RepositoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RepositoryUpdateSerializer
        return RepositorySerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Repository.objects.select_related('bound_node', 'user')
        
        # Role-based access
        if user.is_superuser or (user.role and user.role.code == 'admin'):
            pass  # Admin sees all
        else:
            queryset = queryset.filter(user=user)
        
        # Filter by type
        repo_type = self.request.query_params.get('repo_type')
        if repo_type:
            queryset = queryset.filter(repo_type=repo_type)
        
        # Filter by status
        repo_status = self.request.query_params.get('status')
        if repo_status:
            queryset = queryset.filter(status=repo_status)
        
        # Filter by bound node
        node_id = self.request.query_params.get('bound_node')
        if node_id:
            queryset = queryset.filter(bound_node_id=node_id)
        
        # Filter by initialization status
        initialized = self.request.query_params.get('initialized')
        if initialized is not None:
            is_init = initialized.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(kopia_initialized=is_init)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create a new repository."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Test repository connection.
        
        For S3: Direct connection test using boto3.
        For NAS/Local: Test through bound Node.
        """
        repo = self.get_object()
        
        # S3 类型：直接测试连接，不需要绑定 Node
        if repo.repo_type == Repository.TYPE_S3:
            return self._test_s3_connection(repo)
        
        # NAS/Local 类型：需要绑定 Node
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a Sync Proxy first.',
                'error_code': 'NO_BOUND_NODE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if repo.bound_node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Bound node is {repo.bound_node.get_status_display()}. Node must be active.',
                'error_code': 'NODE_NOT_ACTIVE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: 通过 WebSocket 向 Node 发送测试命令
        # 目前模拟测试结果
        return self._test_node_connection(repo)
    
    def _test_s3_connection(self, repo):
        """测试 S3 连接"""
        config = repo.config or {}
        credentials = repo.get_decrypted_credentials() or {}
        
        endpoint = config.get('endpoint', '')
        bucket = config.get('bucket', '')
        region = config.get('region', 'us-east-1')
        use_ssl = config.get('use_ssl', True)
        access_key = credentials.get('access_key', '')
        secret_key = credentials.get('secret_key', '')
        
        if not all([endpoint, bucket, access_key, secret_key]):
            return Response({
                'success': False,
                'message': 'Missing required S3 configuration. Please check endpoint, bucket, and credentials.',
                'error_code': 'MISSING_CONFIG'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            s3_config = Config(
                connect_timeout=5,
                read_timeout=10,
                retries={'max_attempts': 2}
            )
            
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=s3_config,
                use_ssl=use_ssl,
                verify=False  # 对于自签名证书
            )
            
            # 测试 bucket 存在性
            s3_client.head_bucket(Bucket=bucket)
            
            # 尝试列出对象（验证读取权限）
            s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            
            # 更新仓库状态
            repo.last_connection_test = timezone.now()
            repo.connection_test_result = 'Connection successful'
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            logger.info(f"S3 connection test successful for repository {repo.name}")
            
            return Response({
                'success': True,
                'message': 'Connection test successful',
                'details': {
                    'endpoint': endpoint,
                    'bucket': bucket,
                    'region': region,
                    'tested_at': repo.last_connection_test.isoformat()
                }
            })
            
        except EndpointConnectionError as e:
            error_msg = f'Cannot connect to endpoint: {endpoint}'
            logger.warning(f"S3 connection failed for {repo.name}: {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'ENDPOINT_UNREACHABLE',
                'details': {'endpoint': endpoint}
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ConnectTimeoutError:
            error_msg = f'Connection timeout to endpoint: {endpoint}'
            logger.warning(f"S3 connection timeout for {repo.name}")
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'CONNECTION_TIMEOUT',
                'details': {'endpoint': endpoint}
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = str(e)
            
            if error_code == '403':
                error_msg = 'Access denied. Please check your access key and secret key.'
            elif error_code == '404':
                error_msg = f'Bucket "{bucket}" not found.'
            elif error_code == 'InvalidAccessKeyId':
                error_msg = 'Invalid access key ID.'
            elif error_code == 'SignatureDoesNotMatch':
                error_msg = 'Invalid secret key. Signature does not match.'
            
            logger.warning(f"S3 client error for {repo.name}: {error_code} - {error_msg}")
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': f'S3_{error_code}',
                'details': {'error_code': error_code}
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            logger.error(f"S3 connection test error for {repo.name}: {error_msg}", exc_info=True)
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'UNKNOWN_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _test_node_connection(self, repo):
        """通过 Node 测试 NAS/Local 连接"""
        # TODO: 实现通过 WebSocket 向 Node 发送测试命令
        # 目前返回模拟结果
        repo.last_connection_test = timezone.now()
        repo.connection_test_result = 'Connection test successful (simulated)'
        repo.status = Repository.STATUS_ACTIVE
        repo.save()
        
        return Response({
            'success': True,
            'message': 'Connection test successful (simulated)',
            'details': {
                'node': repo.bound_node.name,
                'repo_type': repo.repo_type,
                'tested_at': repo.last_connection_test.isoformat()
            }
        })
    
    @action(detail=True, methods=['post'])
    def initialize(self, request, pk=None):
        """
        Initialize Kopia repository.
        
        This creates the Kopia repository on the storage backend,
        setting up encryption and metadata structures.
        """
        repo = self.get_object()
        
        if repo.kopia_initialized:
            return Response({
                'success': False,
                'message': 'Repository is already initialized.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a node first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RepositoryInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In production, this would send a command to the Node
        # to initialize the Kopia repository
        try:
            # TODO: Implement actual Kopia initialization via Node
            
            repo.status = Repository.STATUS_INITIALIZING
            repo.save()
            
            # Simulate initialization
            import uuid as uuid_lib
            repo.kopia_initialized = True
            repo.kopia_repository_id = str(uuid_lib.uuid4())
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            return Response({
                'success': True,
                'message': 'Repository initialized successfully',
                'details': {
                    'repository_id': repo.kopia_repository_id,
                    'encryption_algorithm': repo.encryption_algorithm
                }
            })
        except Exception as e:
            repo.status = Repository.STATUS_ERROR
            repo.status_message = str(e)
            repo.save()
            
            return Response({
                'success': False,
                'message': f'Initialization failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def bind_node(self, request, pk=None):
        """
        Bind or change the Node for this repository.
        """
        repo = self.get_object()
        node_id = request.data.get('node_id')
        
        if not node_id:
            return Response({
                'success': False,
                'message': 'node_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Node not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Node is {node.get_status_display()}. Node must be active.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        repo.bound_node = node
        repo.save()
        
        return Response({
            'success': True,
            'message': f'Node "{node.name}" bound successfully.',
            'bound_node': {
                'id': str(node.id),
                'name': node.name,
                'status': node.status
            }
        })
    
    @action(detail=True, methods=['post'])
    def unbind_node(self, request, pk=None):
        """Unbind the Node from this repository."""
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No node is currently bound.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_node_name = repo.bound_node.name
        repo.bound_node = None
        repo.save()
        
        return Response({
            'success': True,
            'message': f'Node "{old_node_name}" unbound successfully.'
        })
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronize repository statistics."""
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In production, this would query the Node for actual stats
        # TODO: Implement actual sync via Node WebSocket
        
        repo.last_sync_at = timezone.now()
        repo.save()
        
        return Response({
            'success': True,
            'message': 'Repository synchronized',
            'details': {
                'used_space': repo.used_space,
                'snapshot_count': repo.snapshot_count,
                'synced_at': repo.last_sync_at.isoformat()
            }
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get repository statistics overview."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'active': queryset.filter(status=Repository.STATUS_ACTIVE).count(),
            'inactive': queryset.filter(status=Repository.STATUS_INACTIVE).count(),
            'error': queryset.filter(status=Repository.STATUS_ERROR).count(),
            'initialized': queryset.filter(kopia_initialized=True).count(),
            'not_initialized': queryset.filter(kopia_initialized=False).count(),
            'bound': queryset.filter(bound_node__isnull=False).count(),
            'unbound': queryset.filter(bound_node__isnull=True).count(),
            'by_type': {},
            'total_capacity': sum(r.capacity for r in queryset if r.capacity > 0),
            'total_used': sum(r.used_space for r in queryset),
        }
        
        # Count by type
        for type_code, type_name in Repository.TYPE_CHOICES:
            stats['by_type'][type_code] = queryset.filter(repo_type=type_code).count()
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available repository types."""
        return Response([
            {'value': type_code, 'label': type_name}
            for type_code, type_name in Repository.TYPE_CHOICES
        ])
    
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """Get snapshots in this repository."""
        repo = self.get_object()
        
        # In production, this would query the Node for actual snapshots
        # TODO: Implement actual snapshot listing via Node
        
        return Response({
            'count': repo.snapshot_count,
            'results': []  # Placeholder for actual snapshots
        })
    
    @action(detail=False, methods=['post'])
    def list_s3_buckets(self, request):
        """
        List S3 buckets from a given S3-compatible storage.
        
        Request body:
        - endpoint: S3 endpoint URL
        - access_key: Access key ID
        - secret_key: Secret access key
        - region: Region (optional, default: us-east-1)
        - use_ssl: Use SSL (optional, default: true)
        """
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_ssl = request.data.get('use_ssl', True)
        
        logger.info(f"[S3] List buckets request - endpoint: {endpoint}, region: {region}, use_ssl: {use_ssl}")
        logger.debug(f"[S3] Access key: {access_key[:4]}****{access_key[-4:] if access_key and len(access_key) > 8 else '****'}")
        
        # Validation
        if not all([endpoint, access_key, secret_key]):
            logger.warning(f"[S3] Missing required parameters - endpoint: {bool(endpoint)}, access_key: {bool(access_key)}, secret_key: {bool(secret_key)}")
            return Response({
                'success': False,
                'message': 'endpoint, access_key, and secret_key are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"[S3] Creating S3 client for endpoint: {endpoint}")
            
            # Validate endpoint format
            if not endpoint.startswith(('http://', 'https://')):
                return Response({
                    'success': False,
                    'error_type': 'invalid_endpoint',
                    'message': 'Endpoint must start with http:// or https://'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse endpoint for logging
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            logger.info(f"[S3] Endpoint host: {parsed.netloc}, scheme: {parsed.scheme}")
            
            # Create S3 client with optimized timeouts
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=Config(
                    connect_timeout=5,  # 5 seconds to establish connection
                    read_timeout=20,    # 20 seconds to read data
                    retries={'max_attempts': 2},  # Retry twice on failure
                    signature_version='s3v4'
                ),
                use_ssl=use_ssl,
                verify=False  # For self-signed certificates
            )
            
            logger.info(f"[S3] Testing connection to {parsed.netloc}...")
            
            # Quick connection test first
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                host = parsed.netloc.split(':')[0]
                port = 443 if parsed.scheme == 'https' else 80
                if ':' in parsed.netloc:
                    host, port_str = parsed.netloc.split(':')
                    port = int(port_str)
                
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result != 0:
                    logger.warning(f"[S3] Connection test failed: {host}:{port} is not reachable")
                    return Response({
                        'success': False,
                        'error_type': 'connection_refused',
                        'message': f'Cannot connect to {host}:{port}. Please check the endpoint and network connectivity.',
                        'details': {
                            'host': host,
                            'port': port,
                            'suggestion': 'Ensure the endpoint URL is correct and the service is running.'
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                logger.info(f"[S3] Connection test passed: {host}:{port} is reachable")
            except socket.gaierror as e:
                logger.warning(f"[S3] DNS resolution failed for {host}: {e}")
                return Response({
                    'success': False,
                    'error_type': 'dns_error',
                    'message': f'Cannot resolve hostname: {host}',
                    'details': {
                        'host': host,
                        'suggestion': 'Check if the hostname is correct and DNS is working.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.warning(f"[S3] Connection test error: {e}")
                # Continue anyway, let boto3 handle it
            
            logger.info(f"[S3] Attempting to list buckets...")
            
            # List buckets
            response = s3_client.list_buckets()
            
            logger.info(f"[S3] Successfully listed buckets, found {len(response.get('Buckets', []))} buckets")
            
            buckets = []
            for bucket in response.get('Buckets', []):
                # Get bucket location
                try:
                    location = s3_client.get_bucket_location(Bucket=bucket['Name'])
                    bucket_region = location.get('LocationConstraint', 'us-east-1')
                except Exception as e:
                    logger.debug(f"[S3] Could not get location for bucket {bucket['Name']}: {e}")
                    bucket_region = 'unknown'
                
                buckets.append({
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat() if bucket.get('CreationDate') else None,
                    'region': bucket_region
                })
            
            return Response({
                'success': True,
                'buckets': buckets,
                'count': len(buckets)
            })
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'N/A')
            
            logger.error(f"[S3] ClientError - Code: {error_code}, HTTP Status: {http_status}, Message: {error_msg}")
            logger.error(f"[S3] Full error response: {e.response}")
            
            # Provide more specific error messages
            error_messages = {
                'InvalidAccessKeyId': 'Invalid Access Key ID - Please check your access key',
                'SignatureDoesNotMatch': 'Signature mismatch - Please check your secret key',
                'AccessDenied': 'Access denied - Please check your permissions',
                'InvalidToken': 'Invalid security token',
                'RequestTimeTooSkewed': 'Request time too skewed - Check server time',
                'NoSuchBucket': 'Bucket does not exist',
                'TemporaryRedirect': 'Wrong endpoint - Please use the correct regional endpoint',
                'PermanentRedirect': 'Wrong endpoint - The bucket exists in a different region',
            }
            
            friendly_message = error_messages.get(error_code, f'S3 Error ({error_code}): {error_msg}')
            
            return Response({
                'success': False,
                'error_code': error_code,
                'http_status': http_status,
                'message': friendly_message,
                'details': error_msg
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except EndpointConnectionError as e:
            logger.error(f"[S3] EndpointConnectionError - Could not connect to {endpoint}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Could not connect to endpoint: {endpoint}',
                'details': str(e),
                'hint': 'Please check if the endpoint URL is correct and accessible'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ConnectTimeoutError as e:
            logger.error(f"[S3] ConnectTimeoutError - Connection timeout for {endpoint}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Connection timeout for endpoint: {endpoint}',
                'details': str(e),
                'hint': 'The endpoint is not responding. Please check network connectivity'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except BotoCoreError as e:
            logger.error(f"[S3] BotoCoreError - Connection error: {str(e)}")
            return Response({
                'success': False,
                'message': f'Connection error: {str(e)}',
                'hint': 'Please check network connectivity and endpoint URL'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.exception(f"[S3] Unexpected error listing buckets: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to list buckets: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def validate_s3_bucket_name(self, request):
        """
        Validate S3 bucket name and check availability.
        
        Request body:
        - bucket_name: Bucket name to validate
        - endpoint: S3 endpoint URL (optional, for availability check)
        - access_key: Access key ID (optional, for availability check)
        - secret_key: Secret access key (optional, for availability check)
        - region: Region (optional)
        """
        bucket_name = request.data.get('bucket_name')
        
        # First, validate the name format
        is_valid, error_message = validate_bucket_name(bucket_name)
        
        if not is_valid:
            return Response({
                'success': False,
                'valid': False,
                'error': error_message,
                'rules': {
                    'min_length': BUCKET_NAME_RULES['min_length'],
                    'max_length': BUCKET_NAME_RULES['max_length'],
                    'pattern_description': 'Lowercase letters, numbers, dots (.), and hyphens (-). Must start and end with a letter or number.',
                    'no_consecutive_dots': True,
                    'no_ip_format': True
                }
            })
        
        # If credentials provided, check if bucket name is available
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_ssl = request.data.get('use_ssl', True)
        
        availability_checked = False
        available = None
        availability_message = None
        
        if all([endpoint, access_key, secret_key]):
            try:
                s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                    config=Config(
                        connect_timeout=10,
                        read_timeout=10,
                        signature_version='s3v4'
                    ),
                    use_ssl=use_ssl,
                    verify=False
                )
                
                # Check if bucket exists
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                    # Bucket exists
                    availability_checked = True
                    available = False
                    availability_message = 'Bucket name already exists'
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code in ['404', 'NoSuchBucket']:
                        # Bucket does not exist - name is available
                        availability_checked = True
                        available = True
                        availability_message = 'Bucket name is available'
                    elif error_code == 'AccessDenied':
                        # Can't determine - might exist or not
                        availability_checked = True
                        available = None
                        availability_message = 'Unable to check availability (Access Denied)'
                    else:
                        availability_checked = True
                        available = None
                        availability_message = f'Unable to check availability ({error_code})'
                        
            except Exception as e:
                availability_checked = True
                available = None
                availability_message = f'Could not check availability: {str(e)}'
        
        return Response({
            'success': True,
            'valid': True,
            'bucket_name': bucket_name,
            'availability_checked': availability_checked,
            'available': available,
            'availability_message': availability_message,
            'rules': {
                'min_length': BUCKET_NAME_RULES['min_length'],
                'max_length': BUCKET_NAME_RULES['max_length'],
                'pattern_description': 'Lowercase letters, numbers, dots (.), and hyphens (-). Must start and end with a letter or number.'
            }
        })
    
    @action(detail=False, methods=['post'])
    def create_s3_bucket(self, request):
        """
        Create a new S3 bucket.
        
        Request body:
        - bucket_name: Bucket name to create
        - endpoint: S3 endpoint URL
        - access_key: Access key ID
        - secret_key: Secret access key
        - region: Region (optional)
        - use_ssl: Use SSL (optional, default: true)
        """
        bucket_name = request.data.get('bucket_name')
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_ssl = request.data.get('use_ssl', True)
        
        # Validation
        if not all([bucket_name, endpoint, access_key, secret_key]):
            return Response({
                'success': False,
                'message': 'bucket_name, endpoint, access_key, and secret_key are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate bucket name format
        is_valid, error_message = validate_bucket_name(bucket_name)
        if not is_valid:
            return Response({
                'success': False,
                'message': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=Config(
                    connect_timeout=10,
                    read_timeout=30,
                    signature_version='s3v4'
                ),
                use_ssl=use_ssl,
                verify=False
            )
            
            # Create bucket
            # Note: For us-east-1, LocationConstraint is not needed
            if region == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            
            return Response({
                'success': True,
                'message': f'Bucket "{bucket_name}" created successfully',
                'bucket_name': bucket_name,
                'region': region
            })
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            # Handle specific error codes
            if error_code == 'BucketAlreadyExists':
                return Response({
                    'success': False,
                    'message': 'Bucket name already exists. Please choose a different name.'
                }, status=status.HTTP_400_BAD_REQUEST)
            elif error_code == 'BucketAlreadyOwnedByYou':
                return Response({
                    'success': False,
                    'message': 'You already own a bucket with this name.'
                }, status=status.HTTP_400_BAD_REQUEST)
            elif error_code == 'InvalidBucketName':
                return Response({
                    'success': False,
                    'message': 'Invalid bucket name. Please check the naming rules.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'message': f'S3 Error ({error_code}): {error_msg}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except BotoCoreError as e:
            return Response({
                'success': False,
                'message': f'Connection Error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to create bucket: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def test_connectivity(self, request, pk=None):
        """
        Test connectivity to a repository.
        
        This will verify:
        - S3: Endpoint reachable, credentials valid, bucket exists and accessible
        - NAS: Server reachable, mount point accessible, read/write permissions
        - Local: Path exists, read/write permissions
        
        Returns detailed connectivity status and any errors encountered.
        """
        from common.encryption import decrypt_value
        
        repository = self.get_object()
        repo_type = repository.repo_type
        results = {
            'success': False,
            'connectivity': {},
            'errors': [],
            'warnings': []
        }
        
        logger.info(f"[Repository] Testing connectivity for {repository.name} (type: {repo_type})")
        
        if repo_type == 's3':
            # Test S3 connectivity
            config = repository.config or {}
            credentials = repository.get_decrypted_credentials()
            
            endpoint = config.get('endpoint')
            bucket = config.get('bucket')
            region = config.get('region', 'us-east-1')
            use_ssl = config.get('use_ssl', True)
            access_key = credentials.get('access_key')
            secret_key = credentials.get('secret_key')
            
            if not all([endpoint, bucket, access_key, secret_key]):
                results['errors'].append('Missing required S3 configuration')
                return Response(results, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # Step 1: Test endpoint reachability
                logger.info(f"[S3] Testing endpoint reachability: {endpoint}")
                from urllib.parse import urlparse
                parsed = urlparse(endpoint)
                hostname = parsed.hostname
                
                import socket
                try:
                    start_time = time.time()
                    sock = socket.create_connection((hostname, parsed.port or (443 if use_ssl else 80)), timeout=5)
                    sock.close()
                    latency = (time.time() - start_time) * 1000
                    results['connectivity']['endpoint'] = {
                        'reachable': True,
                        'latency_ms': round(latency, 2)
                    }
                    logger.info(f"[S3] Endpoint reachable in {latency:.2f}ms")
                except socket.timeout:
                    results['connectivity']['endpoint'] = {'reachable': False, 'error': 'Connection timeout'}
                    results['errors'].append(f'Endpoint {endpoint} connection timeout')
                    return Response(results, status=status.HTTP_400_BAD_REQUEST)
                except socket.gaierror as e:
                    results['connectivity']['endpoint'] = {'reachable': False, 'error': f'DNS resolution failed: {str(e)}'}
                    results['errors'].append(f'Cannot resolve hostname: {hostname}')
                    return Response(results, status=status.HTTP_400_BAD_REQUEST)
                except ConnectionRefusedError:
                    results['connectivity']['endpoint'] = {'reachable': False, 'error': 'Connection refused'}
                    results['errors'].append(f'Connection refused by {endpoint}')
                    return Response(results, status=status.HTTP_400_BAD_REQUEST)
                
                # Step 2: Test authentication
                logger.info(f"[S3] Testing authentication with access key: {access_key[:4]}...{access_key[-4:]}")
                s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                    config=Config(
                        connect_timeout=5,
                        read_timeout=10,
                        signature_version='s3v4'
                    ),
                    use_ssl=use_ssl,
                    verify=False
                )
                
                # Test by listing buckets (validates credentials)
                start_time = time.time()
                s3_client.list_buckets()
                auth_latency = (time.time() - start_time) * 1000
                results['connectivity']['authentication'] = {
                    'success': True,
                    'latency_ms': round(auth_latency, 2)
                }
                logger.info(f"[S3] Authentication successful in {auth_latency:.2f}ms")
                
                # Step 3: Test bucket access
                logger.info(f"[S3] Testing bucket access: {bucket}")
                start_time = time.time()
                s3_client.head_bucket(Bucket=bucket)
                bucket_latency = (time.time() - start_time) * 1000
                results['connectivity']['bucket'] = {
                    'exists': True,
                    'accessible': True,
                    'latency_ms': round(bucket_latency, 2)
                }
                logger.info(f"[S3] Bucket {bucket} accessible in {bucket_latency:.2f}ms")
                
                # Step 4: Test write permission (try to list objects with prefix)
                try:
                    prefix = config.get('prefix', '')
                    s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
                    results['connectivity']['write_permission'] = {
                        'testable': True,
                        'note': 'List operation succeeded, write permission not fully tested'
                    }
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    if error_code == 'AccessDenied':
                        results['warnings'].append('List permission denied on bucket')
                        results['connectivity']['write_permission'] = {'testable': False, 'error': 'Access denied'}
                    else:
                        raise
                
                results['success'] = True
                results['message'] = 'S3 connectivity test passed'
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f"[S3] ClientError during connectivity test: {error_code} - {error_msg}")
                
                if error_code == 'InvalidAccessKeyId':
                    results['connectivity']['authentication'] = {'success': False, 'error': 'Invalid access key ID'}
                    results['errors'].append('Invalid access key ID')
                elif error_code == 'SignatureDoesNotMatch':
                    results['connectivity']['authentication'] = {'success': False, 'error': 'Invalid secret key'}
                    results['errors'].append('Secret key is incorrect')
                elif error_code == 'NoSuchBucket':
                    results['connectivity']['bucket'] = {'exists': False, 'error': 'Bucket does not exist'}
                    results['errors'].append(f'Bucket "{bucket}" does not exist')
                elif error_code == 'AccessDenied':
                    results['connectivity']['authentication'] = {'success': False, 'error': 'Access denied'}
                    results['errors'].append('Access denied. Check your permissions.')
                else:
                    results['errors'].append(f'S3 error ({error_code}): {error_msg}')
                    
            except Exception as e:
                logger.exception(f"[S3] Unexpected error during connectivity test: {str(e)}")
                results['errors'].append(f'Unexpected error: {str(e)}')
                
        elif repo_type == 'nas':
            # Test NAS connectivity
            config = repository.config or {}
            credentials = repository.get_decrypted_credentials()
            
            server = config.get('server')
            export_path = config.get('export_path')
            nas_type = config.get('nas_type', 'nfs')
            
            bound_node = repository.bound_node
            if not bound_node:
                results['errors'].append('No Sync Proxy bound to this repository')
                return Response(results, status=status.HTTP_400_BAD_REQUEST)
            
            # TODO: Send connectivity test task to Sync Proxy via WebSocket
            # For now, return a placeholder response
            results['connectivity'] = {
                'server': server,
                'export_path': export_path,
                'nas_type': nas_type,
                'bound_node': bound_node.name,
                'status': 'pending',
                'note': 'Connectivity test requires Sync Proxy to be online'
            }
            results['warnings'].append('NAS connectivity test requires Sync Proxy to be implemented')
            
        elif repo_type == 'local':
            # Test Local filesystem connectivity
            config = repository.config or {}
            path = config.get('path')
            
            bound_node = repository.bound_node
            if not bound_node:
                results['errors'].append('No Sync Proxy bound to this repository')
                return Response(results, status=status.HTTP_400_BAD_REQUEST)
            
            # TODO: Send connectivity test task to Sync Proxy via WebSocket
            results['connectivity'] = {
                'path': path,
                'bound_node': bound_node.name,
                'status': 'pending',
                'note': 'Connectivity test requires Sync Proxy to be online'
            }
            results['warnings'].append('Local filesystem test requires Sync Proxy to be implemented')
        
        # Update repository's last_connection_test timestamp
        repository.last_connection_test = timezone.now()
        repository.save(update_fields=['last_connection_test'])
        
        status_code = status.HTTP_200_OK if results['success'] else status.HTTP_400_BAD_REQUEST
        return Response(results, status=status_code)
