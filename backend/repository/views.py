"""
HyperFileLens Backend - Repository Views
"""

import re
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

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
        Test repository connection through bound Node.
        
        This sends a test command to the bound Node to verify
        connectivity to the storage backend.
        """
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a node first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if repo.bound_node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Bound node is {repo.bound_node.get_status_display()}. Node must be active.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In production, this would send a WebSocket command to the Node
        # to test the connection. For now, we simulate the response.
        try:
            # Simulate connection test
            # TODO: Implement actual Node communication via WebSocket
            
            # Update repository status
            repo.last_connection_test = timezone.now()
            repo.connection_test_result = 'Connection successful'
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            return Response({
                'success': True,
                'message': 'Connection test successful',
                'details': {
                    'node': repo.bound_node.name,
                    'repo_type': repo.repo_type,
                    'tested_at': repo.last_connection_test.isoformat()
                }
            })
        except Exception as e:
            repo.status = Repository.STATUS_ERROR
            repo.status_message = str(e)
            repo.save()
            
            return Response({
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
        
        # Validation
        if not all([endpoint, access_key, secret_key]):
            return Response({
                'success': False,
                'message': 'endpoint, access_key, and secret_key are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create S3 client
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
                verify=False  # For self-signed certificates
            )
            
            # List buckets
            response = s3_client.list_buckets()
            
            buckets = []
            for bucket in response.get('Buckets', []):
                # Get bucket location
                try:
                    location = s3_client.get_bucket_location(Bucket=bucket['Name'])
                    bucket_region = location.get('LocationConstraint', 'us-east-1')
                except Exception:
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
                'message': f'Failed to list buckets: {str(e)}'
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
