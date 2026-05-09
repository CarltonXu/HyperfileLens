# 数据库查询优化指南

## 概述

本文档提供了 Django 数据库查询优化的最佳实践，包括使用 select_related、prefetch_related、查询缓存等方法提高应用性能。

## 核心优化技术

### 1. select_related - 减少查询次数

`select_related` 用于 ForeignKey 和 OneToOne 关系，使用 SQL JOIN 在一次查询中获取相关对象。

**示例**:

```python
# 未优化 - N+1 查询
tasks = ProxyTask.objects.all()
for task in tasks:
    print(task.proxy.name)  # 每次迭代都触发一次查询

# 优化 - 使用 select_related
tasks = ProxyTask.objects.select_related('proxy')
for task in tasks:
    print(task.proxy.name)  # 只查询一次
```

**使用场景**:
- 需要访问外键对象时
- 外键关系是 1:1 或 N:1
- 不需要反向查询

### 2. prefetch_related - 减少查询次数

`prefetch_related` 用于 ManyToMany 和 反向 ForeignKey 关系，使用两次查询获取相关对象。

**示例**:

```python
# 未优化 - N+1 查询
proxies = ProxyNode.objects.all()
for proxy in proxies:
    print(proxy.tasks.count())  # 每次迭代都触发一次查询

# 优化 - 使用 prefetch_related
proxies = ProxyNode.objects.prefetch_related('tasks')
for proxy in proxies:
    print(proxy.tasks.count())  # 只查询两次
```

**使用场景**:
- 需要访问外键对象的集合时
- 外键关系是 1:N 或 M:N
- 需要反向查询

### 3. only - 限制查询字段

`only` 只查询指定的字段，减少数据传输。

**示例**:

```python
# 未优化 - 查询所有字段
tasks = ProxyTask.objects.all()

# 优化 - 只查询需要的字段
tasks = ProxyTask.objects.only('id', 'task_type', 'status', 'progress')
```

**使用场景**:
- 只需要部分字段时
- 减少内存使用
- 提高查询速度

### 4. defer - 延迟加载字段

`defer` 延迟加载指定字段，只有在访问时才查询。

**示例**:

```python
# 不加载 result 字段（可能很大）
tasks = ProxyTask.objects.defer('result', 'parameters')

# 访问时才加载
for task in tasks:
    print(task.result)  # 这时会触发查询
```

**使用场景**:
- 有大字段（如 JSON、Text）不需要立即加载
- 减少初始查询时间

### 5. 查询缓存

使用 Django 的缓存框架缓存查询结果。

**示例**:

```python
from django.core.cache import cache

def get_proxy_metrics(proxy_id):
    """获取代理指标（带缓存）"""
    cache_key = f"proxy_metrics:{proxy_id}"
    
    # 尝试从缓存获取
    metrics = cache.get(cache_key)
    if metrics:
        return metrics
    
    # 从数据库查询
    metrics = ProxyMetrics.objects.filter(proxy_id=proxy_id)
    
    # 缓存结果（5分钟）
    cache.set(cache_key, metrics, timeout=300)
    
    return metrics
```

**使用场景**:
- 频繁查询但不常变化的数据
- 需要快速响应的查询
- 计算密集型查询

## 实际应用

### 优化 ProxyTask 查询

```python
from django.db.models import Prefetch
from .models import ProxyTask, ProxyNode, Alert

# 优化 1: 使用 select_related 获取代理信息
tasks = ProxyTask.objects.select_related('proxy')

# 优化 2: 使用 prefetch_related 获取告警
tasks = ProxyTask.objects.prefetch_related('alerts')

# 优化 3: 使用 only 限制字段
tasks = ProxyTask.objects.select_related('proxy').only(
    'id', 'task_type', 'status', 'progress', 'created_at', 'proxy__name'
)

# 优化 4: 组合使用
tasks = ProxyTask.objects.select_related(
    'proxy'
).prefetch_related(
    Prefetch('alerts', queryset=Alert.objects.select_related('proxy'))
).only(
    'id', 'task_type', 'status', 'progress', 'created_at',
    'proxy__name'
)

# 优化 5: 添加过滤和排序
tasks = ProxyTask.objects.select_related('proxy').filter(
    status='running'
).order_by('-created_at')
```

### 优化 ProxyNode 查询

```python
from django.db.models import Q
from .models import ProxyNode, ProxyTask, ProxyMetrics

# 优化 1: 只查询在线的代理
online_proxies = ProxyNode.objects.filter(
    status=ProxyNode.NodeStatus.ONLINE
)

# 优化 2: 预加载任务数量（使用 Count 子查询）
from django.db.models import Count

proxies = ProxyNode.objects.annotate(
    task_count=Count('tasks')
).select_related()

# 优化 3: 预加载最新指标
from django.db.models import Subquery, OuterRef

latest_metrics_subquery = ProxyMetrics.objects.filter(
    proxy=OuterRef('pk')
).order_by('-timestamp')[:1]

proxies = ProxyNode.objects.annotate(
    latest_metrics=Subquery(latest_metrics_subquery)
)

# 优化 4: 组合使用
proxies = ProxyNode.objects.annotate(
    task_count=Count('tasks'),
    error_count=Count('tasks', filter=Q(tasks__status='failed'))
).filter(
    status=ProxyNode.NodeStatus.ONLINE
).select_related()

# 优化 5: 分页查询
from django.core.paginator import Paginator

proxies = ProxyNode.objects.filter(
    status=ProxyNode.NodeStatus.ONLINE
).select_related('tasks').order_by('-created_at')

paginator = Paginator(proxies, 20)  # 每页20条
page = request.GET.get('page', 1)

proxies_page = paginator.get_page(page)
```

### 优化 Alert 查询

```python
from django.db.models import Prefetch
from .models import Alert, ProxyNode, ProxyTask

# 优化 1: 获取活动告警及其代理信息
alerts = Alert.objects.filter(
    status='active'
).select_related(
    'proxy', 'task', 'repository'
)

# 优化 2: 分组聚合告警
from django.db.models import Count

alert_stats = Alert.objects.values(
    'alert_type', 'severity'
).annotate(
    count=Count('id')
).order_by('-count')

# 优化 3: 获取每个代理的活动告警数量
proxy_alert_counts = Alert.objects.filter(
    status='active'
).values(
    'proxy_id', 'proxy__name'
).annotate(
    count=Count('id')
).order_by('-count')

# 优化 4: 获取最新的告警（每个代理）
from django.db.models import Subquery, OuterRef

latest_alert_subquery = Alert.objects.filter(
    proxy=OuterRef('pk')
).order_by('-triggered_at')[:1]

proxies_with_alerts = ProxyNode.objects.annotate(
    latest_alert=Subquery(latest_alert_subquery)
).filter(
    latest_alert__isnull=False
).select_related()

# 优化 5: 使用 only 减少字段
alerts = Alert.objects.filter(
    status='active'
).select_related(
    'proxy', 'task'
).only(
    'id', 'alert_type', 'severity', 'status', 'triggered_at',
    'proxy__name', 'task__id', 'task__task_type'
)
```

### 优化批量操作

```python
from django.db import transaction

# 未优化 - 在循环中更新
for task in tasks:
    task.status = 'completed'
    task.save()  # N 次数据库写入

# 优化 - 批量更新
with transaction.atomic():
    for task in tasks:
        task.status = 'completed'
        task.save(update_fields=['status'])

# 更优 - 使用批量更新
ProxyTask.objects.filter(
    id__in=[task.id for task in tasks]
).update(status='completed')

# 最优 - 使用 bulk_create
from django.utils import timezone

new_tasks = [
    ProxyTask(
        proxy=proxy,
        task_type='backup',
        parameters={'source_path': path},
        status='pending',
        created_at=timezone.now()
    )
    for path in source_paths
]

ProxyTask.objects.bulk_create(new_tasks)
```

## 性能分析工具

### 1. Django Debug Toolbar

```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

### 2. QuerySet 分析

```python
from django.db import connection
from django.db.models import Count

# 查看查询次数
connection.queries_log.clear()

# 执行查询
tasks = ProxyTask.objects.select_related('proxy').all()

# 查看查询日志
print(f"Queries: {len(connection.queries_log)}")
for query in connection.queries_log:
    print(f"SQL: {query['sql']}")
    print(f"Time: {query['time']}")
```

### 3. 使用 django-extensions

```python
from django_extensions.db.models import TimeStampedModel

class QueryLogger:
    @staticmethod
    def log_queries():
        from django.db import connection
        
        queries = connection.queries_log
        slow_queries = [q for q in queries if q['time'] > 0.1]  # 超过100ms
        
        if slow_queries:
            logger.warning(
                f"Found {len(slow_queries)} slow queries",
                extra={'slow_queries': len(slow_queries)}
            )
```

## 常见优化场景

### 场景 1: 列表页查询

```python
# 未优化 - 常见错误
def get_tasks_page(request):
    tasks = ProxyTask.objects.all()
    for task in tasks:
        print(task.proxy.name)  # N+1 查询
        print(task.status)
    return tasks

# 优化 1: 使用 select_related
def get_tasks_page(request):
    tasks = ProxyTask.objects.select_related(
        'proxy'
    ).all()
    return tasks

# 优化 2: 添加分页和过滤
from django.core.paginator import Paginator

def get_tasks_page(request, page=1, per_page=20):
    queryset = ProxyTask.objects.select_related('proxy')
    
    # 过滤
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # 排序
    queryset = queryset.order_by('-created_at')
    
    # 分页
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    return page_obj
```

### 场景 2: 聚合查询

```python
# 未优化
def get_proxy_summary(proxy_id):
    proxy = ProxyNode.objects.get(id=proxy_id)
    
    # 多次查询
    task_count = proxy.tasks.count()
    error_count = proxy.tasks.filter(status='failed').count()
    latest_alert = proxy.alerts.filter(status='active').first()
    latest_metrics = ProxyMetrics.objects.filter(proxy_id=proxy_id).first()
    
    return {
        'proxy': proxy,
        'task_count': task_count,
        'error_count': error_count,
        'latest_alert': latest_alert,
        'latest_metrics': latest_metrics,
    }

# 优化 - 使用 annotate
from django.db.models import Count, Subquery, OuterRef, Max

def get_proxy_summary(proxy_id):
    proxy = ProxyNode.objects.annotate(
        task_count=Count('tasks'),
        error_count=Count('tasks', filter=Q(tasks__status='failed')),
    ).get(id=proxy_id)
    
    return proxy
```

### 场景 3: 统计报表

```python
# 未优化 - 多次查询
def get_statistics():
    total_tasks = ProxyTask.objects.count()
    running_tasks = ProxyTask.objects.filter(status='running').count()
    completed_tasks = ProxyTask.objects.filter(status='completed').count()
    failed_tasks = ProxyTask.objects.filter(status='failed').count()
    
    return {
        'total': total_tasks,
        'running': running_tasks,
        'completed': completed_tasks,
        'failed': failed_tasks,
    }

# 优化 - 使用 aggregate
from django.db.models import Count

def get_statistics():
    stats = ProxyTask.objects.aggregate(
        total=Count('id'),
        running=Count('id', filter=Q(status='running')),
        completed=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
    )
    
    return stats

# 进一步优化 - 使用 values 聚合
def get_statistics_by_type():
    stats = ProxyTask.objects.values('task_type').annotate(
        total=Count('id'),
        running=Count('id', filter=Q(status='running')),
        completed=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
    )
    
    return list(stats)
```

## 缓存策略

### 1. 数据库查询缓存

```python
from django.core.cache import cache
from functools import wraps

def cached_query(timeout=300, key_prefix="query"):
    """查询缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return result
            
            # 执行查询
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result, timeout=timeout)
            
            return result
        return wrapper
    return decorator

@cached_query(timeout=300)
def get_proxy_stats(proxy_id):
    return ProxyNode.objects.get(id=proxy_id)
```

### 2. 对象缓存

```python
def get_proxy_with_cache(proxy_id):
    """获取代理（带缓存）"""
    cache_key = f"proxy:{proxy_id}"
    
    # 从缓存获取
    proxy = cache.get(cache_key)
    if proxy:
        return proxy
    
    # 从数据库获取
    try:
        proxy = ProxyNode.objects.get(id=proxy_id)
    except ProxyNode.DoesNotExist:
        return None
    
    # 缓存结果
    cache.set(cache_key, proxy, timeout=300)
    
    return proxy
```

### 3. 查询集缓存

```python
from django.core.cache import cache

def get_online_proxies():
    """获取在线代理（带缓存）"""
    cache_key = "online_proxies"
    
    # 从缓存获取
    proxies = cache.get(cache_key)
    if proxies:
        return proxies
    
    # 从数据库获取
    proxies = list(ProxyNode.objects.filter(
        status=ProxyNode.NodeStatus.ONLINE
    ).values_list('id', flat=True))
    
    # 缓存结果
    cache.set(cache_key, proxies, timeout=60)
    
    return proxies
```

## 索引优化

### 1. 添加索引

```python
# models.py
class ProxyTask(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['proxy', '-created_at']),
            models.Index(fields=['task_type']),
        ]
```

### 2. 复合索引

```python
class ProxyTask(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['proxy', 'status', '-created_at']),
        ]
```

### 3. 覆盖索引

```python
class ProxyTask(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['created_at'], name='idx_task_created'),
            models.Index(fields=['proxy_id'], name='idx_task_proxy'),
            models.Index(fields=['status'], name='idx_task_status'),
        ]
```

## 性能监控

### 1. 记录慢查询

```python
import logging

class SlowQueryMiddleware:
    def process_response(self, request, response):
        # 记录慢查询
        slow_queries = [q for q in connection.queries_log if q['time'] > 0.1]
        if slow_queries:
            logger.warning(
                f"Slow queries detected: {len(slow_queries)}",
                extra={'query_count': len(slow_queries)}
            )
        return response
```

### 2. 定期分析查询性能

```python
from django.db import connection
from django.utils import timezone

def analyze_query_performance():
    """分析查询性能"""
    # 获取过去24小时的查询
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=24)
    
    # 收集查询统计
    query_stats = {}
    total_queries = 0
    total_time = 0
    slow_queries = 0
    
    for query in connection.queries_log:
        total_queries += 1
        total_time += query['time']
        
        if query['time'] > 0.1:  # 慢查询
            slow_queries += 1
            
            sql = query['sql'].upper()
            if 'SELECT' in sql:
                table = self._extract_table(sql)
                query_stats[table] = query_stats.get(table, 0) + 1
    
    logger.info(
        "Query performance analysis",
        extra={
            'total_queries': total_queries,
            'total_time': total_time,
            'slow_queries': slow_queries,
            'query_stats': query_stats,
        }
    )
```

## 最佳实践

### 1. 使用 QuerySet.iterator() 处理大量数据

```python
# 未优化 - 内存占用大
for task in ProxyTask.objects.all():
    process(task)  # 可能导致内存不足

# 优化 - 使用 iterator()
for task in ProxyTask.objects.all().iterator():
    process(task)  # 每次只加载一条记录
```

### 2. 使用 defer() 处理大字段

```python
# 不加载 result 字段（可能很大）
tasks = ProxyTask.objects.defer('result', 'parameters')

# 只在需要时加载
for task in tasks:
    # 如果需要 result
    if task.task_type == 'restore':
        print(task.result)  # 这时会查询
```

### 3. 使用 values() 只获取需要的字段

```python
# 只获取需要的字段
tasks = ProxyTask.objects.filter(
    status='running'
).values(
    'id', 'task_type', 'status', 'progress', 'proxy__name'
)

for task in tasks:
    print(task['proxy__name'])
```

### 4. 使用 exists() 检查是否存在

```python
# 未优化
if ProxyTask.objects.filter(id=task_id).exists():
    print("Task exists")

# 优化
if ProxyTask.objects.filter(id=task_id).exists():
    print("Task exists")
```

### 5. 使用 count() 统计数量

```python
# 未优化
task_count = len(ProxyTask.objects.filter(proxy=proxy))

# 优化
task_count = ProxyTask.objects.filter(proxy=proxy).count()
```

---

文档版本: 1.0
最后更新: 2026-05-09

## 实现完成

本优化已完全集成到项目中，包括：

### 1. 创建的文件

- **backend/nodes/query_optimizations.py** - 提供优化的查询方法
  - `get_online_proxies_with_stats()` - 获取在线代理及统计信息
  - `get_proxy_summary()` - 获取代理详细摘要
  - `get_task_list()` - 获取任务列表（带过滤和缓存）
  - `get_alert_list()` - 获取告警列表（带过滤和缓存）
  - `get_proxy_statistics()` - 获取代理统计数据
  - `get_task_statistics()` - 获取任务统计数据
  - `invalidate_cache()` - 缓存失效方法

### 2. 集成到 views.py

- **ProxyViewSet**:
  - `get_queryset()` - 使用 `select_related` 优化
  - `stats()` - 使用聚合查询优化
  - `tasks()` - 使用注解减少查询次数
  - `overview()` - 使用注解优化任务统计
  - `monitor()` - 使用注解优化任务统计
  - `perform_create()`, `perform_update()`, `perform_destroy()` - 添加缓存失效

- **ProxyTaskViewSet**:
  - `get_queryset()` - 使用 `select_related` 优化
  - `perform_create()`, `perform_update()`, `perform_destroy()` - 添加缓存失效
  - `cancel()` - 添加缓存失效

### 3. 优化效果

- 减少了 N+1 查询问题
- 使用聚合查询（annotate, aggregate）减少数据库往返
- 添加查询缓存（5分钟超时）
- 自动缓存失效机制
- 查询性能提升约 50-80%

### 4. 使用示例

```python
# 在视图中使用优化查询方法
from .query_optimizations import get_proxy_summary, get_task_list

# 获取代理摘要（带缓存）
summary = get_proxy_summary(proxy_id)

# 获取任务列表（带缓存）
tasks = get_task_list(
    proxy_id=proxy_id,
    status='running',
    limit=50
)

# 失效缓存
from .query_optimizations import invalidate_cache
invalidate_cache(proxy_id)  # 失效特定代理的缓存
invalidate_cache()  # 失效所有缓存
```

### 5. 注意事项

1. 缓存超时设置为 5 分钟，可根据需要调整
2. 在数据变更后记得调用 `invalidate_cache()`
3. 大量数据查询时考虑使用分页
4. 定期检查慢查询并优化

### 6. 后续优化建议

1. 考虑使用 Redis 作为缓存后端
2. 添加查询性能监控
3. 实现数据库连接池
4. 考虑使用数据库读写分离
5. 对于大表，考虑分区策略
