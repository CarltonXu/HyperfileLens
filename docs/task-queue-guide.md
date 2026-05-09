# 任务队列使用指南

## 概述

任务队列系统提供了基于优先级的任务管理功能，支持任务的排队、调度、重试和依赖管理。

## 核心概念

### 任务优先级 (TaskPriority)

- `URGENT (0)` - 最紧急，优先处理
- `HIGH (1)` - 高优先级
- `NORMAL (2)` - 正常优先级（默认）
- `LOW (3)` - 低优先级

### 任务状态 (TaskStatus)

- `PENDING` - 等待执行
- `RUNNING` - 正在执行
- `COMPLETED` - 已完成
- `FAILED` - 失败
- `CANCELLED` - 已取消
- `TIMEOUT` - 超时

## 使用示例

### 基本使用

```python
from nodes.task_queue import get_task_queue, TaskPriority

# 获取任务队列
queue = get_task_queue()

# 启动任务队列
queue.start()

# 添加任务
queue.add_task(
    task_id="task-123",
    task_type="backup",
    priority=TaskPriority.NORMAL,
    payload={
        "proxy_id": "proxy-abc",
        "source_path": "/data/backup",
        "repository_id": "repo-123",
    }
)
```

### 添加带回调的任务

```python
def backup_callback(payload):
    """备份任务回调函数"""
    proxy_id = payload.get('proxy_id')
    source_path = payload.get('source_path')
    
    # 执行备份逻辑
    result = execute_backup(proxy_id, source_path)
    
    return result

queue.add_task(
    task_id="task-123",
    task_type="backup",
    priority=TaskPriority.HIGH,
    payload={"proxy_id": "proxy-abc", "source_path": "/data"},
    callback=backup_callback
)
```

### 添加带依赖的任务

```python
# 先添加快照任务
queue.add_task(
    task_id="snapshot-1",
    task_type="snapshot",
    priority=TaskPriority.HIGH,
    payload={"repository_id": "repo-123"}
)

# 然后添加依赖快照的备份任务
queue.add_task(
    task_id="backup-1",
    task_type="backup",
    priority=TaskPriority.NORMAL,
    payload={
        "proxy_id": "proxy-abc",
        "source_path": "/data",
        "snapshot_id": "snapshot-1"  # 依赖 snapshot-1
    },
    depends_on=["snapshot-1"]
)
```

### 添加带重试的任务

```python
queue.add_task(
    task_id="task-123",
    task_type="backup",
    priority=TaskPriority.NORMAL,
    payload={"proxy_id": "proxy-abc", "source_path": "/data"},
    timeout=7200,       # 2小时超时
    retries=5,          # 最多重试5次
    retry_delay=120     # 重试间隔120秒
)
```

### 任务管理

```python
# 检查任务状态
status = queue.get_task_status("task-123")
print(status['status'])  # "running"

# 获取队列统计
stats = queue.get_queue_stats()
print(f"队列中的任务: {stats['queued_tasks']}")
print(f"正在执行的任务: {stats['running_tasks']}")

# 取消任务
queue.cancel_task("task-123")

# 从队列移除任务
queue.remove_task("task-123")
```

### 添加事件回调

```python
def on_task_started(task):
    """任务开始时的回调"""
    logger.info(f"Task started: {task.task_id}")

def on_task_completed(task):
    """任务完成时的回调"""
    logger.info(f"Task completed: {task.task_id}")

def on_task_failed(task):
    """任务失败时的回调"""
    logger.error(f"Task failed: {task.task_id}, error: {task.error}")

# 注册回调
queue.add_callback('started', on_task_started)
queue.add_callback('completed', on_task_completed)
queue.add_callback('failed', on_task_failed)
queue.add_callback('cancelled', lambda t: logger.info(f"Task cancelled: {t.task_id}"))
queue.add_callback('timeout', lambda t: logger.warning(f"Task timeout: {t.task_id}"))
```

### 清理已完成任务

```python
# 清理7天前的已完成任务
queue.clear_completed_tasks(days=7)
```

## 在 Django 应用中使用

### 集成到 signals

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProxyTask
from .task_queue import get_task_queue, TaskPriority

@receiver(post_save, sender=ProxyTask)
def on_proxy_task_created(sender, instance, created, **kwargs):
    """当 ProxyTask 创建时添加到队列"""
    if created and instance.status == 'pending':
        queue = get_task_queue()
        
        # 确定优先级
        priority = TaskPriority.NORMAL
        if instance.priority == 'urgent':
            priority = TaskPriority.URGENT
        elif instance.priority == 'high':
            priority = TaskPriority.HIGH
        elif instance.priority == 'low':
            priority = TaskPriority.LOW
        
        # 添加到队列
        queue.add_task(
            task_id=str(instance.id),
            task_type=instance.task_type,
            priority=priority,
            payload={
                'proxy_id': str(instance.proxy_id),
                'parameters': instance.parameters,
            }
        )
```

### 在 API 视图中使用

```python
from django.http import JsonResponse
from .task_queue import get_task_queue, TaskPriority

def create_backup_task(request):
    """创建备份任务"""
    proxy_id = request.data.get('proxy_id')
    source_path = request.data.get('source_path')
    
    # 创建任务记录
    task = ProxyTask.objects.create(
        proxy_id=proxy_id,
        task_type='backup',
        parameters={'source_path': source_path},
        status='pending'
    )
    
    # 添加到队列
    queue = get_task_queue()
    queue.add_task(
        task_id=str(task.id),
        task_type='backup',
        priority=TaskPriority.NORMAL,
        payload={
            'proxy_id': proxy_id,
            'source_path': source_path,
        }
    )
    
    return JsonResponse({
        'task_id': str(task.id),
        'status': 'queued'
    })
```

## 高级功能

### 优先级队列

```python
# 高优先级任务
queue.add_task(
    task_id="urgent-task",
    task_type="backup",
    priority=TaskPriority.URGENT,
    payload={"proxy_id": "proxy-abc", "source_path": "/important/data"}
)

# 低优先级任务
queue.add_task(
    task_id="low-priority-task",
    task_type="cleanup",
    priority=TaskPriority.LOW,
    payload={"proxy_id": "proxy-abc", "type": "old_logs"}
)
```

### 任务依赖

```python
# 创建任务链
tasks = []

# 第1个任务
queue.add_task(
    task_id="task-1",
    task_type="snapshot",
    priority=TaskPriority.HIGH,
    payload={"repository_id": "repo-123"}
)
tasks.append("task-1")

# 第2个任务（依赖第1个）
queue.add_task(
    task_id="task-2",
    task_type="backup",
    priority=TaskPriority.NORMAL,
    payload={"proxy_id": "proxy-abc", "source_path": "/data"},
    depends_on=["task-1"]
)
tasks.append("task-2")

# 第3个任务（依赖前2个）
queue.add_task(
    task_id="task-3",
    task_type="cleanup",
    priority=TaskPriority.NORMAL,
    payload={"proxy_id": "proxy-abc", "type": "temp_files"},
    depends_on=["task-1", "task-2"]
)
tasks.append("task-3")
```

### 批量添加任务

```python
from .task_queue import get_task_queue, TaskPriority

queue = get_task_queue()

# 批量添加备份任务
backup_tasks = [
    {
        "task_id": f"backup-{i}",
        "task_type": "backup",
        "priority": TaskPriority.NORMAL,
        "payload": {
            "proxy_id": "proxy-abc",
            "source_path": f"/data/directory{i}",
        }
    }
    for i in range(10)
]

for task in backup_tasks:
    queue.add_task(**task)
```

### 动态调整优先级

```python
# 将待处理任务提升为高优先级
from .task_queue import get_task_queue, TaskPriority

queue = get_task_queue()

# 移除原任务
queue.remove_task("task-123")

# 重新添加，使用更高优先级
queue.add_task(
    task_id="task-123",
    task_type="backup",
    priority=TaskPriority.HIGH,
    payload={"proxy_id": "proxy-abc", "source_path": "/important/data"}
)
```

## 配置

### 在 settings.py 中配置

```python
# 任务队列配置
TASK_QUEUE = {
    'MAX_CONCURRENT_TASKS': 5,  # 最大并发任务数
    'CHECK_INTERVAL': 1,         # 检查新任务的间隔（秒）
}

# 启动任务队列
from nodes.task_queue import task_queue

task_queue.max_concurrent_tasks = TASK_QUEUE['MAX_CONCURRENT_TASKS']
task_queue.check_interval = TASK_QUEUE['CHECK_INTERVAL']
task_queue.start()
```

### 在应用启动时启动

```python
# 在 apps.py 或 wsgi.py 中
from django.apps import AppConfig

class NodesConfig(AppConfig):
    name = 'nodes'
    
    def ready(self):
        # 只在主进程中启动
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            from .task_queue import task_queue
            
            task_queue.start()
```

## 监控和调试

### 查看队列状态

```python
from nodes.task_queue import get_task_queue

queue = get_task_queue()
stats = queue.get_queue_stats()

print(f"运行中: {stats['running']}")
print(f"队列任务: {stats['queued_tasks']}")
print(f"运行任务: {stats['running_tasks']}")
print(f"已完成: {stats['completed_tasks']}")
print(f"总任务: {stats['total_tasks']}")
```

### 查看任务历史

```python
from nodes.models import ProxyTask

# 获取最近的任务
recent_tasks = ProxyTask.objects.order_by('-created_at')[:10]

for task in recent_tasks:
    print(f"{task.id}: {task.status} - {task.task_type}")
```

### 调试任务执行

```python
import logging

logger = logging.getLogger('nodes.task_queue')

# 设置详细日志
logger.setLevel(logging.DEBUG)

# 查看任务执行日志
# 在日志文件中查找包含 "Executing task" 的行
```

## 性能优化

### 1. 调整并发数

```python
# 根据系统资源调整
import multiprocessing

cpu_count = multiprocessing.cpu_count()

queue = get_task_queue()
queue.max_concurrent_tasks = cpu_count * 2  # 通常设置为 CPU 核心数的 2 倍
```

### 2. 使用批量操作

```python
# 批量创建任务
from django.db import transaction

with transaction.atomic():
    for i in range(100):
        task = ProxyTask.objects.create(
            proxy_id=proxy.id,
            task_type='backup',
            parameters={'source_path': f'/data/dir{i}'},
            status='pending'
        )

# 批量添加到队列
queue = get_task_queue()
for task in ProxyTask.objects.filter(status='pending'):
    queue.add_task(
        task_id=str(task.id),
        task_type=task.task_type,
        priority=TaskPriority.NORMAL,
        payload={'proxy_id': str(task.proxy_id), 'parameters': task.parameters}
    )
```

### 3. 定期清理内存

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)  # 每天凌晨2点
def cleanup_task_queue():
    """清理任务队列中的已完成任务"""
    from nodes.task_queue import get_task_queue
    
    queue = get_task_queue()
    cleared = queue.clear_completed_tasks(days=7)
    
    logger.info(f"Cleaned up {cleared} completed tasks from queue")

scheduler.start()
```

## 故障排查

### 1. 任务未执行

```python
# 检查队列是否运行
queue = get_task_queue()
stats = queue.get_queue_stats()

if not stats['running']:
    print("Task queue is not running, starting...")
    queue.start()

# 检查任务状态
status = queue.get_task_status("task-123")
if not status:
    print("Task not found in queue")
elif status['status'] == 'pending':
    print("Task is still pending, check dependencies")
```

### 2. 任务超时

```python
# 增加任务超时时间
queue.add_task(
    task_id="task-123",
    task_type="backup",
    payload={"proxy_id": "proxy-abc", "source_path": "/large/data"},
    timeout=14400  # 4小时
)
```

### 3. 任务重试失败

```python
# 增加重试次数和延迟
queue.add_task(
    task_id="task-123",
    task_type="backup",
    payload={"proxy_id": "proxy-abc", "source_path": "/unstable/data"},
    retries=10,         # 最多重试10次
    retry_delay=300     # 重试间隔5分钟
)
```

## 最佳实践

### 1. 合理设置优先级

```python
# 紧急任务
queue.add_task(
    task_id="critical-backup",
    task_type="backup",
    priority=TaskPriority.URGENT,
    payload={"proxy_id": "proxy-abc", "source_path": "/critical/data"}
)

# 定期任务
queue.add_task(
    task_id="scheduled-cleanup",
    task_type="cleanup",
    priority=TaskPriority.LOW,
    payload={"proxy_id": "proxy-abc", "type": "temp_files"}
)
```

### 2. 使用任务依赖

```python
# 确保快照完成后再备份
queue.add_task(
    task_id="backup-1",
    task_type="backup",
    priority=TaskPriority.NORMAL,
    payload={
        "proxy_id": "proxy-abc",
        "source_path": "/data",
        "snapshot_id": "snapshot-1"  # 依赖快照
    },
    depends_on=["snapshot-1"]
)
```

### 3. 设置合理的超时

```python
# 根据数据量设置超时
data_size = get_data_size(source_path)

if data_size > 10 * 1024 * 1024 * 1024:  # > 10GB
    timeout = 14400  # 4小时
elif data_size > 1 * 1024 * 1024 * 1024:  # > 1GB
    timeout = 7200  # 2小时
else:
    timeout = 3600  # 1小时

queue.add_task(
    task_id="backup-1",
    task_type="backup",
    payload={"proxy_id": "proxy-abc", "source_path": source_path},
    timeout=timeout
)
```

### 4. 监控队列性能

```python
# 定期检查队列状态
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', minutes=5)
def monitor_queue():
    queue = get_task_queue()
    stats = queue.get_queue_stats()
    
    # 记录指标
    logger.info(
        "Queue stats",
        extra={
            'queued': stats['queued_tasks'],
            'running': stats['running_tasks'],
            'completed': stats['completed_tasks'],
            'total': stats['total_tasks'],
        }
    )
    
    # 发送告警
    if stats['queued_tasks'] > 100:
        send_alert(f"Task queue backlog: {stats['queued_tasks']} tasks")

scheduler.start()
```

---

文档版本: 1.0
最后更新: 2026-05-09
