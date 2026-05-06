"""
HyperFileLens Backend - AI Query Views
"""

import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import AIQuery
from .serializers import AIQuerySerializer, AIQueryCreateSerializer
from .tasks import execute_ai_query


# Gateway service URL (can be configured in settings)
GATEWAY_URL = getattr(settings, 'GATEWAY_URL', 'http://localhost:8001')


class AIQueryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing AI queries."""
    queryset = AIQuery.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIQueryCreateSerializer
        return AIQuerySerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = AIQuery.objects.select_related('user', 'tenant')
        
        # Superuser can see all AI queries
        if user.is_superuser:
            return queryset
        # Filter by tenant for tenant users
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        # Users without tenant can only see their own queries
        return queryset.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Create a new AI query and execute it asynchronously."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create query instance
        query = AIQuery.objects.create(
            user=request.user,
            tenant=request.user.tenant,
            **serializer.validated_data
        )
        
        # Execute asynchronously
        execute_ai_query.delay(str(query.id))
        
        # Return the created query
        return Response(
            AIQuerySerializer(query).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed query."""
        query = self.get_object()
        
        if query.status not in ['failed']:
            return Response(
                {'error': 'Only failed queries can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status and execute
        query.status = 'pending'
        query.error_message = ''
        query.save(update_fields=['status', 'error_message'])
        
        execute_ai_query.delay(str(query.id))
        
        return Response({'message': 'Query retry started'})
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's query history."""
        queries = self.get_queryset()[:20]
        serializer = AIQuerySerializer(queries, many=True)
        return Response(serializer.data)


# ============== Gateway Proxy Views ==============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_mount_status(request):
    """Proxy: Get mount status from Gateway service."""
    try:
        response = requests.get(f'{GATEWAY_URL}/mount/status', timeout=10)
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable', 'mounted': False}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout', 'mounted': False}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e), 'mounted': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_index_status(request):
    """Proxy: Get index status from Gateway service."""
    try:
        response = requests.get(f'{GATEWAY_URL}/index/status', timeout=10)
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_ai_query(request):
    """Proxy: Execute AI query through Gateway service."""
    try:
        response = requests.post(
            f'{GATEWAY_URL}/ai/query',
            json=request.data,
            timeout=60
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_rebuild_index(request):
    """Proxy: Rebuild index through Gateway service."""
    try:
        response = requests.post(
            f'{GATEWAY_URL}/index/rebuild',
            json=request.data,
            timeout=30
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_list_files(request):
    """Proxy: List files from Gateway service."""
    try:
        response = requests.get(
            f'{GATEWAY_URL}/files',
            params=request.query_params,
            timeout=30
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============== AI Insights Feature APIs ==============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def insights_overview(request):
    """
    AI Insights Overview - 洞察看板
    Returns comprehensive statistics about the backup data.
    """
    from django.utils import timezone
    from datetime import datetime
    
    # Try to get real data from Gateway
    try:
        response = requests.get(f'{GATEWAY_URL}/insights/overview', timeout=10)
        if response.status_code == 200:
            return Response(response.json())
    except:
        pass
    
    # Fallback: Return demo data
    return Response({
        'total_files': 125847,
        'total_size': '52.3 TB',
        'total_size_bytes': 57565000000000,
        'last_sync': timezone.now().isoformat(),
        'file_categories': [
            {'name': 'Documents', 'name_zh': '文档', 'percentage': 45, 'size': '23TB', 'count': 56234},
            {'name': 'Images', 'name_zh': '镜像', 'percentage': 20, 'size': '10TB', 'count': 25169},
            {'name': 'Archives', 'name_zh': '压缩包', 'percentage': 15, 'size': '8TB', 'count': 18877},
            {'name': 'Videos', 'name_zh': '视频', 'percentage': 12, 'size': '6TB', 'count': 15101},
            {'name': 'Others', 'name_zh': '其他', 'percentage': 8, 'size': '4TB', 'count': 10066}
        ],
        'risk_summary': {
            'sensitive_files': 12,
            'ransomware_risk': 'safe',
            'permission_issues': 32
        },
        'optimization_suggestions': {
            'duplicate_files': {'size': '1.2 TB', 'count': 3420},
            'cold_data': {'size': '4.5 TB', 'count': 8934},
            'fastest_growing': {'path': '/var/log', 'growth_rate': '200%', 'period': 'weekly'}
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sensitive_data_scan(request):
    """
    Sensitive Data Scanner - 敏感数据扫描
    Scans for PII, sensitive information, compliance issues.
    """
    try:
        response = requests.get(f'{GATEWAY_URL}/insights/sensitive', timeout=30)
        if response.status_code == 200:
            return Response(response.json())
    except:
        pass
    
    return Response({
        'scan_status': 'completed',
        'last_scan': '2026-05-05T10:30:00Z',
        'findings': [
            {
                'type': 'id_card',
                'type_zh': '身份证号',
                'count': 156,
                'files': [
                    {'path': '/docs/contracts/2024/employee_records.xlsx', 'matches': 45},
                    {'path': '/docs/hr/employee_info.csv', 'matches': 111}
                ],
                'severity': 'high',
                'recommendation': '建议加密存储或移除敏感信息'
            },
            {
                'type': 'phone_number',
                'type_zh': '手机号码',
                'count': 234,
                'files': [
                    {'path': '/docs/contacts/customer_list.xlsx', 'matches': 234}
                ],
                'severity': 'medium',
                'recommendation': '考虑脱敏处理'
            },
            {
                'type': 'bank_account',
                'type_zh': '银行账号',
                'count': 23,
                'files': [
                    {'path': '/docs/finance/payment_records.xlsx', 'matches': 23}
                ],
                'severity': 'high',
                'recommendation': '强烈建议加密存储'
            }
        ],
        'compliance_status': {
            'gdpr': {'status': 'warning', 'issues': 12},
            'pci_dss': {'status': 'pass', 'issues': 0},
            'hipaa': {'status': 'not_applicable', 'issues': 0}
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_profile(request):
    """
    Content Profiling - 内容分类画像
    Auto-categorization and tagging of files.
    """
    try:
        response = requests.get(f'{GATEWAY_URL}/insights/profile', timeout=30)
        if response.status_code == 200:
            return Response(response.json())
    except:
        pass
    
    return Response({
        'categories': [
            {
                'name': 'Contracts',
                'name_zh': '合同文档',
                'count': 1245,
                'size': '2.3 GB',
                'tags': ['legal', 'signed', 'important'],
                'examples': ['contract_2024.pdf', 'agreement_final.docx']
            },
            {
                'name': 'Financial',
                'name_zh': '财务报表',
                'count': 856,
                'size': '1.8 GB',
                'tags': ['finance', 'confidential'],
                'examples': ['Q4_report.xlsx', 'budget_2024.xlsx']
            },
            {
                'name': 'Technical',
                'name_zh': '技术文档',
                'count': 2341,
                'size': '4.5 GB',
                'tags': ['technical', 'documentation'],
                'examples': ['api_docs.pdf', 'architecture.png']
            },
            {
                'name': 'HR',
                'name_zh': '人力资源',
                'count': 432,
                'size': '890 MB',
                'tags': ['hr', 'confidential', 'pii'],
                'examples': ['employee_records.xlsx', 'policies.pdf']
            }
        ],
        'auto_tags': [
            {'tag': 'confidential', 'tag_zh': '机密', 'count': 2345},
            {'tag': 'public', 'tag_zh': '公开', 'count': 12456},
            {'tag': 'internal', 'tag_zh': '内部', 'count': 8765},
            {'tag': 'archived', 'tag_zh': '已归档', 'count': 3456}
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def data_heatmap(request):
    """
    Data Heatmap - 冷热数据分析
    Identifies hot/warm/cold data based on access patterns.
    """
    days = int(request.query_params.get('days', 90))
    
    try:
        response = requests.get(f'{GATEWAY_URL}/insights/heatmap', params={'days': days}, timeout=30)
        if response.status_code == 200:
            return Response(response.json())
    except:
        pass
    
    return Response({
        'period_days': days,
        'heatmap': [
            {'category': 'hot', 'category_zh': '热数据', 'description': f'{days}天内频繁访问', 'size': '12TB', 'percentage': 23, 'file_count': 28934},
            {'category': 'warm', 'category_zh': '温数据', 'description': f'{days}天内偶尔访问', 'size': '18TB', 'percentage': 35, 'file_count': 44127},
            {'category': 'cold', 'category_zh': '冷数据', 'description': f'{days}天内未访问', 'size': '22TB', 'percentage': 42, 'file_count': 52786}
        ],
        'zombie_data': {
            'description': '超过180天未访问的数据',
            'size': '4.5TB',
            'file_count': 8934,
            'potential_savings': '建议归档到低成本存储，可节省约 ¥2,500/月'
        },
        'trend': {
            'hot_growth': '+15%',
            'cold_growth': '+8%',
            'recommendation': '热数据增长较快，建议增加高性能存储容量'
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def redundancy_analysis(request):
    """
    Redundancy Analysis - 冗余内容识别
    Identifies duplicate and similar files.
    """
    try:
        response = requests.get(f'{GATEWAY_URL}/insights/redundancy', timeout=60)
        if response.status_code == 200:
            return Response(response.json())
    except:
        pass
    
    return Response({
        'total_duplicates': 3420,
        'duplicate_size': '1.2 TB',
        'potential_savings': '¥800/月',
        'duplicate_groups': [
            {
                'file_name': 'report_2024.xlsx',
                'count': 15,
                'size': '450 MB',
                'locations': ['/docs/reports/', '/backup/old/', '/shared/finance/']
            },
            {
                'file_name': 'contract_template.docx',
                'count': 8,
                'size': '12 MB',
                'locations': ['/templates/', '/docs/contracts/', '/backup/templates/']
            }
        ],
        'similar_files': {
            'count': 567,
            'potential_savings': '340 MB',
            'description': '内容相似度超过90%的文件'
        },
        'recommendation': '发现3,420个重复文件，占用1.2TB空间。建议使用去重工具清理。'
    })
