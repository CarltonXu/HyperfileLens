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
        logger.info(
            f"[Connection Test] Starting connection test for repository '{repo.name}' "
            f"(ID: {repo.id}, Type: {repo.repo_type})"
        )
        
        # S3 类型：直接测试连接，不需要绑定 Node
        if repo.repo_type == Repository.TYPE_S3:
            return self._test_s3_connection(repo)
        
        # NAS/Local 类型：需要绑定 Node
        if not repo.bound_node:
            logger.warning(
                f"[Connection Test] FAILED for '{repo.name}': No bound node configured for NAS/Local repository"
            )
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a Sync Proxy first.',
                'error_code': 'NO_BOUND_NODE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if repo.bound_node.status != Node.NodeStatus.ACTIVE:
            logger.warning(
                f"[Connection Test] FAILED for '{repo.name}': Bound node '{repo.bound_node.name}' "
                f"is not active (status: {repo.bound_node.get_status_display()})"
            )
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
        # URL Style: 'virtual' (Virtual Hosted Style) or 'path' (Path Style)
        # 默认使用 Virtual Hosted Style，兼容华为云 OBS、AWS S3 等
        url_style = config.get('url_style', 'virtual')
        use_tls = config.get('use_tls', True)
        access_key = credentials.get('access_key', '')
        secret_key = credentials.get('secret_key', '')
        
        # 记录测试开始（脱敏敏感信息）
        masked_key = access_key[:4] + '****' + access_key[-4:] if len(access_key) > 8 else '****'
        logger.info(
            f"[S3 Connection Test] Starting test for repository '{repo.name}' (ID: {repo.id}): "
            f"endpoint={endpoint}, bucket={bucket}, region={region}, "
            f"url_style={url_style}, use_tls={use_tls}, access_key={masked_key}"
        )
        
        if not all([endpoint, bucket, access_key, secret_key]):
            missing = []
            if not endpoint:
                missing.append('endpoint')
            if not bucket:
                missing.append('bucket')
            if not access_key:
                missing.append('access_key')
            if not secret_key:
                missing.append('secret_key')
            logger.warning(
                f"[S3 Connection Test] Missing required configuration for '{repo.name}': {', '.join(missing)}"
            )
            return Response({
                'success': False,
                'message': f'Missing required S3 configuration: {", ".join(missing)}',
                'error_code': 'MISSING_CONFIG',
                'details': {'missing_fields': missing}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"[S3 Connection Test] Creating S3 client for '{repo.name}'...")
            s3_config = Config(
                connect_timeout=5,
                read_timeout=10,
                retries={'max_attempts': 2},
                # URL Style: 'virtual' (Virtual Hosted Style) or 'path' (Path Style)
                # 用户可在前端配置，默认为 virtual
                s3={'addressing_style': url_style}
            )
            
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=s3_config,
                verify=False  # 对于自签名证书
            )
            
            # 测试 bucket 存在性
            logger.info(f"[S3 Connection Test] Testing bucket existence: '{bucket}'...")
            
            try:
                s3_client.head_bucket(Bucket=bucket)
                logger.info(f"[S3 Connection Test] Bucket '{bucket}' exists and is accessible")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                # 处理区域不匹配的情况
                # 404/NoSuchBucket: bucket 不存在于当前区域
                # 403/AccessDenied: 可能是权限问题，也可能是区域不匹配
                # PermanentRedirect/TemporaryRedirect: 明确的区域不匹配
                should_check_region = error_code in (
                    'PermanentRedirect', 'TemporaryRedirect', 
                    '404', 'NoSuchBucket',
                    '403', 'AccessDenied'
                )
                
                if should_check_region:
                    # 尝试获取 bucket 的真实区域
                    actual_region = self._get_bucket_actual_region(
                        endpoint, access_key, secret_key, bucket, use_tls, region, url_style
                    )
                    
                    if actual_region and actual_region != region:
                        logger.info(
                            f"[S3 Connection Test] Bucket '{bucket}' is in region '{actual_region}', "
                            f"but configured region is '{region}'. Attempting to connect with correct region..."
                        )
                        
                        # 使用正确的区域重新创建 client
                        actual_endpoint = self._build_regional_endpoint(endpoint, actual_region)
                        logger.info(f"[S3 Connection Test] Using regional endpoint: {actual_endpoint}")
                        
                        s3_client_regional = boto3.client(
                            's3',
                            endpoint_url=actual_endpoint,
                            region_name=actual_region,
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            config=Config(
                                connect_timeout=5,
                                read_timeout=10,
                                retries={'max_attempts': 2},
                                s3={'addressing_style': url_style}
                            ),
                            verify=False
                        )
                        
                        try:
                            s3_client_regional.head_bucket(Bucket=bucket)
                            logger.info(f"[S3 Connection Test] Bucket '{bucket}' accessible with correct region '{actual_region}'")
                            
                            # 更新 region 变量供后续使用
                            region = actual_region
                            endpoint = actual_endpoint
                            s3_client = s3_client_regional
                            
                        except ClientError as regional_error:
                            regional_code = regional_error.response.get('Error', {}).get('Code', 'Unknown')
                            if regional_code in ('AccessDenied', '403'):
                                return Response({
                                    'success': False,
                                    'message': f'Bucket "{bucket}" exists in region "{actual_region}", but access denied. Please check your permissions.',
                                    'error_code': 'REGION_MISMATCH_ACCESS_DENIED',
                                    'details': {
                                        'configured_region': config.get('region'),
                                        'actual_region': actual_region,
                                        'suggested_endpoint': actual_endpoint,
                                        'bucket': bucket
                                    }
                                }, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                raise regional_error
                    else:
                        # 无法获取真实区域，或区域相同但仍然失败
                        if error_code in ('PermanentRedirect', 'TemporaryRedirect'):
                            return Response({
                                'success': False,
                                'message': f'Bucket "{bucket}" exists in a different region. Please update your endpoint and region configuration.',
                                'error_code': 'REGION_MISMATCH',
                                'details': {
                                    'configured_region': region,
                                    'endpoint': endpoint,
                                    'bucket': bucket,
                                    'hint': 'Use the regional endpoint where the bucket is located'
                                }
                            }, status=status.HTTP_400_BAD_REQUEST)
                        # 对于 403，如果区域检测失败，提供更详细的错误信息
                        if error_code in ('403', 'AccessDenied'):
                            return Response({
                                'success': False,
                                'message': f'Access denied for bucket "{bucket}". This could be due to: 1) Insufficient permissions, 2) Wrong region/endpoint, 3) Bucket belongs to another account.',
                                'error_code': 'ACCESS_DENIED',
                                'details': {
                                    'configured_region': region,
                                    'endpoint': endpoint,
                                    'bucket': bucket,
                                    'hints': [
                                        'Check if the bucket exists in the configured region',
                                        'Verify your access key has the necessary permissions',
                                        'Ensure the bucket belongs to your account'
                                    ]
                                }
                            }, status=status.HTTP_400_BAD_REQUEST)
                        raise
                else:
                    raise
            
            # 尝试列出对象（验证读取权限）
            logger.info(f"[S3 Connection Test] Testing list objects permission on '{bucket}'...")
            s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            logger.info(f"[S3 Connection Test] List objects permission verified for '{bucket}'")
            
            # 更新仓库状态
            repo.last_connection_test = timezone.now()
            repo.connection_test_result = 'Connection successful'
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            logger.info(
                f"[S3 Connection Test] SUCCESS for repository '{repo.name}': "
                f"endpoint={endpoint}, bucket={bucket}"
            )
            
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
            logger.warning(
                f"[S3 Connection Test] FAILED for '{repo.name}': Endpoint unreachable - {endpoint}. "
                f"Error: {str(e)}"
            )
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'ENDPOINT_UNREACHABLE',
                'details': {'endpoint': endpoint, 'error': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ConnectTimeoutError as e:
            error_msg = f'Connection timeout to endpoint: {endpoint}'
            logger.warning(
                f"[S3 Connection Test] FAILED for '{repo.name}': Connection timeout - {endpoint}. "
                f"Timeout: 5s"
            )
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'CONNECTION_TIMEOUT',
                'details': {'endpoint': endpoint, 'timeout': '5s'}
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'Unknown')
            error_msg = str(e)
            
            if error_code == '403':
                error_msg = 'Access denied. Please check your access key and secret key.'
            elif error_code == '404':
                error_msg = f'Bucket "{bucket}" not found. Please verify the bucket name and ensure it exists in the specified region ({region}).'
            elif error_code == 'InvalidAccessKeyId':
                error_msg = 'Invalid access key ID. Please verify your access key.'
            elif error_code == 'SignatureDoesNotMatch':
                error_msg = 'Invalid secret key. Signature does not match. Please verify your secret key.'
            elif error_code == 'NoSuchBucket':
                error_msg = f'Bucket "{bucket}" does not exist in region "{region}".'
            
            logger.warning(
                f"[S3 Connection Test] FAILED for '{repo.name}': "
                f"Client error - code={error_code}, http_status={http_status}, "
                f"endpoint={endpoint}, bucket={bucket}, region={region}. "
                f"Message: {error_msg}"
            )
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': f'S3_{error_code}',
                'details': {
                    'error_code': error_code,
                    'http_status': http_status,
                    'endpoint': endpoint,
                    'bucket': bucket,
                    'region': region
                }
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            logger.error(
                f"[S3 Connection Test] FAILED for '{repo.name}': Unexpected error - {str(e)}",
                exc_info=True
            )
            return Response({
                'success': False,
                'message': error_msg,
                'error_code': 'UNKNOWN_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_bucket_actual_region(self, endpoint, access_key, secret_key, bucket, use_tls, fallback_region, url_style='virtual'):
        """
        尝试获取 bucket 的真实区域。
        华为云 OBS 和其他 S3 兼容存储可能返回 bucket 所在区域。
        """
        import re
        
        logger.info(f"[S3 Region Detection] Attempting to detect actual region for bucket '{bucket}'...")
        
        try:
            s3_config = Config(
                connect_timeout=5,
                read_timeout=10,
                retries={'max_attempts': 1},
                s3={'addressing_style': url_style}
            )
            
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                region_name=fallback_region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=s3_config,
                verify=False
            )
            
            # 方法 1: 使用 get_bucket_location
            try:
                location = s3_client.get_bucket_location(Bucket=bucket)
                region = location.get('LocationConstraint')
                # AWS 返回 None 表示 us-east-1，其他返回区域名
                if region is None:
                    region = 'us-east-1'
                logger.info(f"[S3 Region Detection] Bucket '{bucket}' location from get_bucket_location: {region}")
                return region
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.info(f"[S3 Region Detection] get_bucket_location failed for '{bucket}': {error_code}")
                logger.info(f"[S3 Region Detection] Full error response: {e.response}")
                
                # 方法 2: 从错误响应中提取区域（某些存储服务会返回）
                if error_code in ('PermanentRedirect', 'TemporaryRedirect', '404', 'AccessDenied', '403', 'VirtualHostDomainRequired'):
                    # 华为云 OBS 特殊处理：从 VirtualHost 字段提取区域
                    virtual_host = e.response.get('Error', {}).get('VirtualHost', '')
                    if virtual_host:
                        # VirtualHost 格式: bucket.obs.region.myhuaweicloud.com
                        match = re.search(r'\.obs\.([a-z0-9-]+)\.', virtual_host)
                        if match:
                            region = match.group(1)
                            logger.info(f"[S3 Region Detection] Bucket '{bucket}' region from VirtualHost: {region}")
                            return region
                    
                    # 从错误响应中提取正确的 endpoint
                    endpoint_from_error = e.response.get('Error', {}).get('Endpoint', '')
                    if endpoint_from_error:
                        # 解析 endpoint 获取区域，如 obs.cn-north-4.myhuaweicloud.com
                        match = re.search(r'obs\.([a-z0-9-]+)\.', endpoint_from_error)
                        if match:
                            region = match.group(1)
                            logger.info(f"[S3 Region Detection] Bucket '{bucket}' region extracted from error endpoint: {region}")
                            return region
                    
                    # 尝试从响应头获取
                    headers = e.response.get('ResponseMetadata', {}).get('HTTPHeaders', {})
                    region_header = headers.get('x-amz-bucket-region', '') or headers.get('x-obs-bucket-location', '')
                    if region_header:
                        logger.info(f"[S3 Region Detection] Bucket '{bucket}' region from response header: {region_header}")
                        return region_header
                    
                    # 华为云 OBS 特殊处理：从错误消息中解析
                    error_message = e.response.get('Error', {}).get('Message', '')
                    # 尝试匹配 "Bucket 'xxx' exists in region 'yyy'" 格式
                    match = re.search(r"exists in region ['\"]?([a-z0-9-]+)['\"]?", error_message, re.IGNORECASE)
                    if match:
                        region = match.group(1)
                        logger.info(f"[S3 Region Detection] Bucket '{bucket}' region from error message: {region}")
                        return region
                
                # 方法 3: 从请求 ID 中解析（某些服务）
                request_id = e.response.get('ResponseMetadata', {}).get('RequestId', '')
                
            logger.warning(f"[S3 Region Detection] Could not determine actual region for bucket '{bucket}'")
            return None
            
        except Exception as e:
            logger.warning(f"[S3 Region Detection] Failed to get bucket region for '{bucket}': {str(e)}")
            return None
    
    def _build_regional_endpoint(self, base_endpoint, region):
        """
        根据区域构建正确的 endpoint。
        支持华为云 OBS、AWS S3 等多种格式。
        """
        import re
        from urllib.parse import urlparse
        
        parsed = urlparse(base_endpoint)
        hostname = parsed.netloc or parsed.path
        
        # 华为云 OBS: obs.ap-southeast-3.myhuaweicloud.com -> obs.{region}.myhuaweicloud.com
        huaweicloud_pattern = r'^(obs\.)([a-z0-9-]+)(\.myhuaweicloud\.com)$'
        match = re.match(huaweicloud_pattern, hostname)
        if match:
            new_hostname = f"obs.{region}.myhuaweicloud.com"
            return f"{parsed.scheme}://{new_hostname}"
        
        # AWS S3: s3.ap-southeast-3.amazonaws.com -> s3.{region}.amazonaws.com
        aws_pattern = r'^(s3[.-])([a-z0-9-]*)(\.amazonaws\.com)$'
        match = re.match(aws_pattern, hostname)
        if match:
            new_hostname = f"s3.{region}.amazonaws.com"
            return f"{parsed.scheme}://{new_hostname}"
        
        # 通用格式: 如果 hostname 中已有区域，尝试替换
        # 格式: prefix.region.suffix -> prefix.{new_region}.suffix
        generic_pattern = r'^([a-z0-9-]+\.)([a-z0-9-]+)(\.[a-z0-9.-]+)$'
        match = re.match(generic_pattern, hostname)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_hostname = f"{prefix}{region}{suffix}"
            return f"{parsed.scheme}://{new_hostname}"
        
        # 无法解析，返回原始 endpoint
        logger.warning(f"[S3] Could not build regional endpoint for {base_endpoint} with region {region}")
        return base_endpoint
    
    def _test_node_connection(self, repo):
        """通过 Node 测试 NAS/Local 连接"""
        logger.info(
            f"[Node Connection Test] Starting test for repository '{repo.name}' "
            f"(ID: {repo.id}, Type: {repo.repo_type}, Bound Node: {repo.bound_node.name if repo.bound_node else 'None'})"
        )
        # TODO: 实现通过 WebSocket 向 Node 发送测试命令
        # 目前返回模拟结果
        logger.info(
            f"[Node Connection Test] Simulated test for '{repo.name}' - "
            f"actual WebSocket test not yet implemented"
        )
        repo.last_connection_test = timezone.now()
        repo.connection_test_result = 'Connection test successful (simulated)'
        repo.status = Repository.STATUS_ACTIVE
        repo.save()
        
        logger.info(
            f"[Node Connection Test] SUCCESS (simulated) for repository '{repo.name}'"
        )
        
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
    def create_s3_bucket(self, request):
        """
        Create a new S3 bucket.
        
        Request body:
        - endpoint: S3 endpoint URL
        - access_key: Access key ID
        - secret_key: Secret access key
        - region: Region (optional, default: us-east-1)
        - use_tls: Use SSL (optional, default: true)
        - bucket_name: Name of the bucket to create
        """
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_tls = request.data.get('use_tls', True)
        bucket_name = request.data.get('bucket_name')
        
        logger.info(f"[S3] Create bucket request - endpoint: {endpoint}, bucket: {bucket_name}, region: {region}")
        
        # Validation
        if not all([endpoint, access_key, secret_key, bucket_name]):
            return Response({
                'success': False,
                'message': 'Missing required parameters: endpoint, access_key, secret_key, bucket_name',
                'error_code': 'MISSING_PARAMETERS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate bucket name
        import re
        if not re.match(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$', bucket_name):
            return Response({
                'success': False,
                'message': 'Invalid bucket name. Must be 3-63 characters, start and end with lowercase letter or number, contain only lowercase letters, numbers, hyphens, and dots.',
                'error_code': 'INVALID_BUCKET_NAME'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
            
            # Build endpoint URL
            endpoint_url = endpoint if endpoint.startswith('http') else f"{'https' if use_tls else 'http'}://{endpoint}"
            
            # Determine URL style
            url_style = request.data.get('url_style', 'virtual')
            
            s3_config = Config(
                signature_version='s3v4',
                s3={'addressing_style': 'virtual' if url_style == 'virtual' else 'path'}
            )
            
            session = boto3.Session()
            s3_client = session.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=s3_config
            )
            
            # Create bucket
            try:
                if region == 'us-east-1':
                    # us-east-1 has special handling
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                
                logger.info(f"[S3] Successfully created bucket: {bucket_name}")
                return Response({
                    'success': True,
                    'message': f'Bucket "{bucket_name}" created successfully',
                    'bucket': {
                        'name': bucket_name,
                        'region': region,
                        'creation_date': 'now'
                    }
                })
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                
                if error_code == 'BucketAlreadyExists':
                    return Response({
                        'success': False,
                        'message': f'Bucket "{bucket_name}" already exists',
                        'error_code': 'BUCKET_ALREADY_EXISTS'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif error_code == 'AccessDenied':
                    return Response({
                        'success': False,
                        'message': 'Access denied. Check your permissions.',
                        'error_code': 'ACCESS_DENIED'
                    }, status=status.HTTP_403_FORBIDDEN)
                else:
                    logger.error(f"[S3] Failed to create bucket: {error_code} - {error_msg}")
                    return Response({
                        'success': False,
                        'message': f'Failed to create bucket: {error_msg}',
                        'error_code': error_code
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except Exception as e:
            logger.error(f"[S3] Unexpected error creating bucket: {str(e)}")
            return Response({
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'error_code': 'UNKNOWN_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def list_s3_buckets(self, request):
        """
        List S3 buckets from a given S3-compatible storage.
        
        Request body:
        - endpoint: S3 endpoint URL
        - access_key: Access key ID
        - secret_key: Secret access key
        - region: Region (optional, default: us-east-1)
        - use_tls: Use SSL (optional, default: true)
        """
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_tls = request.data.get('use_tls', True)
        
        logger.info(f"[S3] List buckets request - endpoint: {endpoint}, region: {region}, use_tls: {use_tls}")
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
            matched_buckets = []
            other_buckets = []
            
            logger.info(f"[S3] Starting bucket region detection for {len(response.get('Buckets', []))} buckets...")
            logger.info(f"[S3] Configured region for filtering: '{region}'")
            logger.info(f"[S3] Endpoint URL: '{endpoint}'")
            
            # For S3 bucket listing with accessibility check via head_bucket
            # We use concurrent requests to speed up the process
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            raw_buckets = response.get('Buckets', [])
            total_bucket_count = len(raw_buckets)
            logger.info(f"[S3] Starting concurrent accessibility check for {total_bucket_count} buckets (max 10 parallel)...")
            
            def check_bucket_accessibility(bucket):
                """Check if a bucket is accessible via head_bucket"""
                bucket_name = bucket['Name']
                bucket_region = 'unknown'
                actually_accessible = False
                
                try:
                    # Try head_bucket to verify bucket is accessible via configured endpoint
                    head_response = s3_client.head_bucket(Bucket=bucket_name)
                    headers = head_response.get('ResponseMetadata', {}).get('HTTPHeaders', {})
                    
                    # If we get here, bucket is accessible via configured endpoint
                    actually_accessible = True
                    
                    # Try to get region from response headers
                    bucket_region = headers.get('x-amz-bucket-region') or headers.get('x-obs-bucket-location')
                    if bucket_region:
                        logger.debug(f"[S3] Bucket '{bucket_name}': ACCESSIBLE, region = '{bucket_region}'")
                    else:
                        bucket_region = region or 'unknown'
                        logger.debug(f"[S3] Bucket '{bucket_name}': ACCESSIBLE, using configured region = '{bucket_region}'")
                        
                except ClientError as head_err:
                    error_code = head_err.response.get('Error', {}).get('Code', 'Unknown')
                    error_headers = head_err.response.get('ResponseMetadata', {}).get('HTTPHeaders', {})
                    
                    # Try to get region from error headers
                    bucket_region = error_headers.get('x-amz-bucket-region') or error_headers.get('x-obs-bucket-location')
                    
                    if bucket_region:
                        logger.debug(f"[S3] Bucket '{bucket_name}': NOT ACCESSIBLE (error={error_code}), actual region = '{bucket_region}'")
                    else:
                        bucket_region = region or 'unknown'
                        logger.debug(f"[S3] Bucket '{bucket_name}': NOT ACCESSIBLE (error={error_code})")
                        
                except Exception as e:
                    bucket_region = region or 'unknown'
                    logger.debug(f"[S3] Bucket '{bucket_name}': NOT ACCESSIBLE (exception: {type(e).__name__})")
                
                return {
                    'bucket': bucket,
                    'bucket_name': bucket_name,
                    'bucket_region': bucket_region,
                    'actually_accessible': actually_accessible
                }
            
            # Use thread pool for concurrent head_bucket requests
            bucket_results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_bucket_accessibility, bucket): bucket for bucket in raw_buckets}
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=30)
                        bucket_results.append(result)
                    except Exception as e:
                        bucket = futures[future]
                        logger.warning(f"[S3] Bucket '{bucket['Name']}': check failed: {e}")
                        bucket_results.append({
                            'bucket': bucket,
                            'bucket_name': bucket['Name'],
                            'bucket_region': region or 'unknown',
                            'actually_accessible': False
                        })
            
            # Process results - only include accessible buckets
            accessible_count = 0
            for result in bucket_results:
                bucket_name = result['bucket_name']
                bucket = result['bucket']
                bucket_region = result['bucket_region']
                actually_accessible = result['actually_accessible']
                
                logger.info(f"[S3] Bucket '{bucket_name}': region = '{bucket_region}', accessible = {actually_accessible}")
                
                # Only include buckets that are actually accessible
                if actually_accessible:
                    accessible_count += 1
                    bucket_info = {
                        'name': bucket_name,
                        'creation_date': bucket['CreationDate'].isoformat() if bucket.get('CreationDate') else None,
                        'region': bucket_region,
                        'accessible': True
                    }
                    buckets.append(bucket_info)
                    matched_buckets.append(bucket_info)
                else:
                    # Not accessible via configured endpoint, put in other_buckets
                    bucket_info = {
                        'name': bucket_name,
                        'creation_date': bucket['CreationDate'].isoformat() if bucket.get('CreationDate') else None,
                        'region': bucket_region,
                        'accessible': False
                    }
                    other_buckets.append(bucket_info)
            
            logger.info(f"[S3] Accessibility check complete: {accessible_count}/{total_bucket_count} buckets are accessible via configured endpoint")
            
            # Determine which buckets to return based on filter parameter
            filter_by_region = request.data.get('filter_by_region', True)
            
            # Log summary of region detection
            logger.info(f"[S3] === REGION DETECTION SUMMARY ===")
            logger.info(f"[S3] Total buckets found: {len(buckets)}")
            logger.info(f"[S3] Buckets matching configured region '{region}': {len(matched_buckets)}")
            logger.info(f"[S3] Buckets in other regions: {len(other_buckets)}")
            
            if matched_buckets:
                matched_names = [b['name'] for b in matched_buckets]
                logger.info(f"[S3] Matched bucket names: {matched_names}")
            
            if other_buckets:
                # Group by region for better visibility
                regions_summary = {}
                for b in other_buckets:
                    r = b['region']
                    if r not in regions_summary:
                        regions_summary[r] = []
                    regions_summary[r].append(b['name'])
                logger.info(f"[S3] Buckets by region: {regions_summary}")
            
            if filter_by_region and region:
                # Return only buckets matching the configured region
                # If no buckets match, return all with a warning
                result_buckets = matched_buckets if matched_buckets else buckets
                logger.info(f"[S3] Filtering by region '{region}': {len(matched_buckets)}/{len(buckets)} buckets match")
            else:
                # Return all buckets
                result_buckets = buckets
                logger.info(f"[S3] Returning all {len(buckets)} buckets (no region filter)")
            
            return Response({
                'success': True,
                'buckets': result_buckets,
                'total_count': len(buckets),
                'filtered_count': len(result_buckets),
                'matched_count': len(matched_buckets),
                'configured_region': region,
                'region_filter_applied': filter_by_region and region and bool(matched_buckets),
                'suggestion': None if matched_buckets or not region else 
                    f'No buckets found in region "{region}". Found {len(other_buckets)} buckets in other regions. '
                    f'Consider creating a bucket in this region or updating your region configuration.'
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
        use_tls = request.data.get('use_tls', True)
        
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
        - use_tls: Use SSL (optional, default: true)
        """
        bucket_name = request.data.get('bucket_name')
        endpoint = request.data.get('endpoint')
        access_key = request.data.get('access_key')
        secret_key = request.data.get('secret_key')
        region = request.data.get('region', 'us-east-1')
        use_tls = request.data.get('use_tls', True)
        
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
            use_tls = config.get('use_tls', True)
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
                    sock = socket.create_connection((hostname, parsed.port or (443 if use_tls else 80)), timeout=5)
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
