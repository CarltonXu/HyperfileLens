# 优雅关闭使用指南

## 概述

优雅关闭功能确保系统在接收到关闭信号时，能够：
- 通知所有连接的客户端
- 等待正在运行的任务完成或安全取消
- 关闭所有 WebSocket 连接
- 保存系统状态
- 清理资源

## 核心组件

### 1. GracefulShutdownManager

管理整个系统的优雅关闭过程。

### 2. WebSocketConnectionManager

管理 WebSocket 连接，支持优雅关闭。

### 3. TaskGracefulShutdownManager

管理正在运行的任务的优雅关闭。

### 4. ShutdownSignalHandler

处理系统信号（SIGINT, SIGTERM）。

## 使用方法

### 在应用启动时初始化

```python
# 在 apps.py 或 wsgi.py 中
from django.apps import AppConfig
from nodes.graceful_shutdown import (
    shutdown_manager, 
    websocket_manager, 
    signal_handler
)

class NodesConfig(AppConfig):
    name = 'nodes'
    
    def ready(self):
        # 只在主进程中启动
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            # 设置信号处理器
            signal_handler.setup()
            
            # 注册组件
            shutdown_manager.register_component('websocket', websocket_manager)
            shutdown_manager.register_component('task_queue', get_task_queue())
```

### 在 WebSocket Consumer 中管理连接

```python
from channels.generic.websocket import AsyncWebsocketConsumer
from nodes.graceful_shutdown import websocket_manager, shutdown_manager

class ProxyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """接受 WebSocket 连接"""
        self.proxy_id = self.scope['url_route']['kwargs'].get('proxy_id')
        self.connection_id = str(uuid.uuid4())
        
        # 注册连接
        websocket_manager.add_connection(
            connection_id=self.connection_id,
            proxy_id=self.proxy_id,
            consumer=self
        )
        
        await self.accept()
        logger.info(f"WebSocket connection established: {self.connection_id}")

    async def disconnect(self, close_code):
        """WebSocket 连接断开"""
        # 取消注册连接
        websocket_manager.remove_connection(self.connection_id)
        
        logger.info(f"WebSocket connection closed: {self.connection_id}, code: {close_code}")

    async def receive(self, text_data):
        """接收并处理消息"""
        # 检查是否正在关闭
        if shutdown_manager.is_shutting_down():
            await self.close(code=1000, reason='Server shutdown')
            return
        
        # 正常处理消息
        await self.handle_message(text_data)
```

### 添加自定义关闭组件

```python
class MyComponent:
    """自定义组件，支持优雅关闭"""
    
    def __init__(self):
        self._running = False
    
    def start(self):
        """启动组件"""
        self._running = True
        # 启动后台线程或协程
        self._worker_thread = threading.Thread(target=self._run)
        self._worker_thread.start()
    
    def graceful_shutdown(self, timeout=30):
        """优雅关闭组件"""
        logger.info("Component shutting down...")
        
        # 通知线程停止
        self._running = False
        
        # 等待线程停止
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("Component thread did not stop gracefully")
        
        # 清理资源
        self.cleanup()
        logger.info("Component shutdown completed")
    
    def _run(self):
        """后台工作线程"""
        while self._running:
            # 执行工作
            time.sleep(1)
    
    def cleanup(self):
        """清理资源"""
        pass

# 注册组件
shutdown_manager.register_component('my_component', MyComponent())
```

### 添加关闭回调

```python
# 预关闭回调 - 在关闭前执行
def save_pending_state():
    """保存挂起的状态"""
    logger.info("Saving pending state...")
    # 保存数据库状态
    # 保存缓存
    pass

shutdown_manager.add_pre_shutdown_callback(save_pending_state)

# 后关闭回调 - 在关闭后执行
def cleanup_resources():
    """清理资源"""
    logger.info("Cleaning up resources...")
    # 清理临时文件
    # 关闭数据库连接
    pass

shutdown_manager.add_post_shutdown_callback(cleanup_resources)
```

### 手动触发关闭

```python
from nodes.graceful_shutdown import shutdown_manager

# 手动触发优雅关闭
shutdown_manager.initiate_shutdown(reason="manual")
```

### 检查关闭状态

```python
from nodes.graceful_shutdown import shutdown_manager

# 获取关闭状态
status = shutdown_manager.get_shutdown_status()
print(f"正在关闭: {status['shutdown_in_progress']}")
print(f"关闭请求时间: {status['shutdown_requested_at']}")
print(f"注册的组件: {status['components']}")
print(f"超时时间: {status['timeout']}秒")

# 检查剩余时间
remaining = shutdown_manager.get_time_until_shutdown()
if remaining is not None:
    print(f"剩余时间: {remaining:.1f}秒")
```

### 获取 WebSocket 连接信息

```python
from nodes.graceful_shutdown import websocket_manager

# 获取所有连接
all_connections = websocket_manager.get_all_connections()
print(f"当前连接数: {len(all_connections)}")

# 获取特定代理的连接
proxy_connections = websocket_manager.get_connections_for_proxy("proxy-abc")
print(f"代理连接数: {len(proxy_connections)}")

# 获取连接详情
for conn_id, conn_info in all_connections.items():
    print(f"{conn_id}: proxy={conn_info['proxy_id']}, user={conn_info['user_id']}")
```

### 获取运行中的任务

```python
from nodes.graceful_shutdown import task_shutdown_manager

# 获取运行中的任务
running_tasks = task_shutdown_manager.get_running_tasks()
print(f"运行中的任务数: {len(running_tasks)}")

for task in running_tasks:
    print(f"{task['task_id']}: {task['task_type']}, 代理={task['proxy_id']}")
```

## 在 Django ASGI 中使用

### 配置 asgi.py

```python
import os
import django
from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from nodes.graceful_shutdown import signal_handler, shutdown_manager

# 初始化信号处理器
signal_handler.setup()

# 注册关闭处理器
def on_shutdown():
    """应用关闭时的处理"""
    # 保存状态
    # 关闭连接
    # 清理资源
    pass

shutdown_manager.add_pre_shutdown_callback(on_shutdown)

application = get_default_application()
```

## 集成到 Gunicorn/Uvicorn

### Gunicorn 配置

```python
# gunicorn_config.py
import os
import signal
import sys

from nodes.graceful_shutdown import shutdown_manager

def worker_int(worker):
    """工作进程初始化"""
    # 初始化信号处理器
    from nodes.graceful_shutdown import signal_handler
    signal_handler.setup()

def on_starting(server):
    """服务器启动时的处理"""
    print("Server starting...")

def on_shutdown(server):
    """服务器关闭时的处理"""
    print("Server shutting down...")
    
    # 触发优雅关闭
    shutdown_manager.initiate_shutdown(reason="gunicorn")
```

启动 Gunicorn：

```bash
gunicorn core.asgi:application \
    --config gunicorn_config.py \
    --workers 4 \
    --timeout 120 \
    --graceful-timeout 30
```

### Uvicorn 配置

```python
# uvicorn_config.py
from nodes.graceful_shutdown import signal_handler, shutdown_manager

def on_startup():
    """应用启动时的处理"""
    # 初始化信号处理器
    signal_handler.setup()

def on_shutdown():
    """应用关闭时的处理"""
    # 触发优雅关闭
    shutdown_manager.initiate_shutdown(reason="uvicorn")
```

启动 Uvicorn：

```bash
uvicorn core.asgi:application \
    --config uvicorn_config.py \
    --workers 4 \
    --timeout 120 \
    --graceful-timeout 30
```

## 监控和调试

### 监控关闭过程

```python
import time
from nodes.graceful_shutdown import shutdown_manager

# 监控关闭状态
while shutdown_manager.is_shutting_down():
    status = shutdown_manager.get_shutdown_status()
    print(f"关闭中... 剩余时间: {shutdown_manager.get_time_until_shutdown():.1f}秒")
    time.sleep(1)
```

### 检查组件状态

```python
# 检查 WebSocket 连接
from nodes.graceful_shutdown import websocket_manager

connections = websocket_manager.get_all_connections()
print(f"WebSocket 连接: {len(connections)}")

for conn_id, conn_info in connections.items():
    print(f"{conn_id}: {conn_info['proxy_id']}")

# 检查运行中的任务
from nodes.graceful_shutdown import task_shutdown_manager

running_tasks = task_shutdown_manager.get_running_tasks()
print(f"运行中的任务: {len(running_tasks)}")

for task in running_tasks:
    print(f"{task['task_id']}: {task['task_type']}")
```

## 最佳实践

### 1. 设置合理的超时时间

```python
# 根据任务类型设置不同的超时
BACKUP_TASK_TIMEOUT = 3600   # 1小时
RESTORE_TASK_TIMEOUT = 7200  # 2小时
CLEANUP_TASK_TIMEOUT = 300   # 5分钟

shutdown_manager = GracefulShutdownManager(shutdown_timeout=BACKUP_TASK_TIMEOUT)
```

### 2. 实现组件超时处理

```python
class MyComponent:
    def graceful_shutdown(self, timeout=30):
        """优雅关闭组件"""
        logger.info(f"Shutting down with timeout: {timeout}s")
        
        # 启动超时检查线程
        def check_timeout():
            time.sleep(timeout)
            if self._running:
                logger.warning("Component shutdown timeout, forcing shutdown")
                self._force_shutdown()
        
        timeout_thread = threading.Thread(target=check_timeout, daemon=True)
        timeout_thread.start()
        
        # 正常关闭流程
        self._graceful_shutdown()
        
        # 等待超时线程完成
        timeout_thread.join(timeout=0.1)
    
    def _graceful_shutdown(self):
        """正常的优雅关闭流程"""
        pass
    
    def _force_shutdown(self):
        """强制关闭"""
        pass
```

### 3. 保存检查点

```python
def save_checkpoint():
    """保存检查点"""
    logger.info("Saving checkpoint...")
    
    # 保存未完成的任务
    from nodes.models import ProxyTask
    
    running_tasks = ProxyTask.objects.filter(status='running')
    for task in running_tasks:
        task.status = 'pending'
        task.save()
    
    # 保存任务队列状态
    from nodes.task_queue import get_task_queue
    
    queue = get_task_queue()
    queue_stats = queue.get_queue_stats()
    
    # 保存到数据库或文件
    save_to_disk('queue_state.json', queue_stats)
    
    logger.info("Checkpoint saved")

shutdown_manager.add_pre_shutdown_callback(save_checkpoint)
```

### 4. 恢复检查点

```python
def restore_checkpoint():
    """恢复检查点"""
    logger.info("Restoring checkpoint...")
    
    # 从数据库恢复任务
    from nodes.models import ProxyTask
    
    pending_tasks = ProxyTask.objects.filter(status='pending')
    queue = get_task_queue()
    
    for task in pending_tasks:
        queue.add_task(
            task_id=str(task.id),
            task_type=task.task_type,
            payload=task.parameters,
        )
    
    logger.info(f"Restored {len(pending_tasks)} tasks from checkpoint")

# 在应用启动时调用
restore_checkpoint()
```

### 5. 健康检查端点

```python
from django.http import JsonResponse
from nodes.graceful_shutdown import shutdown_manager, websocket_manager, task_shutdown_manager

def health_check(request):
    """健康检查端点"""
    status = {
        'status': 'healthy',
        'shutdown_in_progress': shutdown_manager.is_shutting_down(),
        'websocket_connections': len(websocket_manager.get_all_connections()),
        'running_tasks': len(task_shutdown_manager.get_running_tasks()),
        'time_until_shutdown': shutdown_manager.get_time_until_shutdown(),
    }
    
    http_status = 200
    if status['shutdown_in_progress']:
        status['status'] 'draining'
        http_status = 503
    
    return JsonResponse(status, status=http_status)
```

## 故障排查

### 1. 组件未关闭

```python
# 检查组件注册
from nodes.graceful_shutdown import shutdown_manager

status = shutdown_manager.get_shutdown_status()
print(f"注册的组件: {status['components']}")

# 检查组件是否有关闭方法
for name, component in shutdown_manager._components.items():
    has_method = hasattr(component, 'graceful_shutdown')
    print(f"{name}: has graceful_shutdown method = {has_method}")
```

### 2. 任务未取消

```python
# 检查任务是否注册
from nodes.graceful_shutdown import task_shutdown_manager

running_tasks = task_shutdown_manager.get_running_tasks()
print(f"注册的任务: {list(running_tasks.keys())}")

# 检查任务状态
from nodes.models import ProxyTask

for task_id in running_tasks.keys():
    task = ProxyTask.objects.filter(id=task_id).first()
    print(f"{task_id}: {task.status if task else 'not found'}")
```

### 3. WebSocket 连接未关闭

```python
# 检查连接状态
from nodes.graceful_shutdown import websocket_manager

connections = websocket_manager.get_all_connections()
print(f"剩余连接: {len(connections)}")

# 手动关闭连接
for conn_id, conn_info in connections.items():
    consumer = conn_info.get('consumer')
    if consumer:
        consumer.close(code=1000, reason='Server shutdown')
```

## 性能考虑

### 1. 优化关闭超时

```python
# 根据连接数动态调整超时
from nodes.graceful_shutdown import websocket_manager

connections = len(websocket_manager.get_all_connections())

if connections > 100:
    timeout = 60  # 更多时间
elif connections > 50:
    timeout = 30  # 正常时间
else:
    timeout = 10  # 较少时间

shutdown_manager = GracefulShutdownManager(shutdown_timeout=timeout)
```

### 2. 并行关闭组件

```python
import concurrent.futures

def shutdown_components_parallel():
    """并行关闭组件"""
    components = list(shutdown_manager._components.items())
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(components)) as executor:
        futures = {}
        
        for name, component in components:
            future = executor.submit(_shutdown_component, name, component)
            futures[future] = name
        
        # 等待所有组件关闭
        concurrent.futures.wait(futures, timeout=30)

def _shutdown_component(name, component):
    """关闭单个组件"""
    try:
        if hasattr(component, 'graceful_shutdown'):
            component.graceful_shutdown()
        elif hasattr(component, 'shutdown'):
            component.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down {name}: {e}")
```

### 3. 分阶段关闭

```python
def staged_shutdown():
    """分阶段关闭"""
    # 第一阶段：停止接收新任务
    logger.info("Stage 1: Stopping new tasks...")
    stop_accepting_tasks()
    
    # 第二阶段：等待当前任务完成
    logger.info("Stage 2: Waiting for tasks to complete...")
    wait_for_tasks_completion(timeout=60)
    
    # 第三阶段：关闭连接
    logger.info("Stage 3: Closing connections...")
    close_connections(timeout=30)
    
    # 第四阶段：清理资源
    logger.info("Stage 4: Cleaning up resources...")
    cleanup_resources()

shutdown_manager.add_pre_shutdown_callback(staged_shutdown)
```

---

文档版本: 1.0
最后更新: 2026-05-09
