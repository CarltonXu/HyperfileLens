# 后端优化建议清单

## ✅ 已完成优化

### 1. 扩展任务进度处理（支持新字段） ✅

**状态**: 已完成 (2026-05-09)

**修改文件**:
- `backend/nodes/models.py` - 添加了详细的进度字段
- `backend/nodes/consumers.py` - 更新了 handle_task_progress 方法
- `backend/nodes/migrations/0007_proxynode_bandwidth_limit_kbps_and_more.py` - 数据库迁移
- `backend/nodes/migrations/0008_proxytask_accepted_at.py` - 添加 accepted_at 字段

**新增字段** (`backend/nodes/models.py`):
```python
class ProxyTask(models.Model):
    # 新增详细进度字段
    current_file = models.CharField(max_length=512, blank=True, null=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    processed_bytes = models.BigIntegerField(default=0)
    total_bytes = models.BigIntegerField(default=0)
    speed_mbps = models.FloatField(default=0.0)
    eta = models.CharField(max_length=64, blank=True, null=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
```

---

### 2. 实现后端告警系统 ✅

**状态**: 已完成 (2026-05-09)

**创建的文件**:
```
backend/nodes/
├── alerts/
│   ├── __init__.py        # 模块初始化
│   ├── manager.py         # AlertManager 类
│   └── types.py           # 告警类型定义
├── admin.py               # Django Admin 配置
└── models.py              # 添加了 Alert 和 AlertRule 模型
```

**数据库迁移**: `nodes/migrations/0009_alertrule_alert.py`

**告警类型** (AlertType):
- Proxy 告警: `proxy_offline`, `proxy_timeout`, `proxy_error`
- 任务告警: `task_failed`, `task_timeout`, `task_cancelled`
- 资源告警: `cpu_high`, `memory_high`, `disk_high`, `bandwidth_exceeded`
- 系统告警: `connection_lost`, `error_rate_high`, `storage_unavailable`

**告警严重级别** (AlertSeverity):
- INFO - 信息
- WARNING - 警告
- CRITICAL - 严重
- FATAL - 致命

**Alert 模型功能**:
- 关联代理、任务、仓库
- 支持确认、解决、静音操作
- 自动去重和重复计数
- 通知发送跟踪
- 时长统计

**AlertRule 模型功能**:
- 自定义告警规则
- 灵活的条件配置
- 支持作用域（所有代理或特定代理）
- 可配置冷却期防止告警风暴
- 多通知通道支持

**集成位置**:
- `handle_heartbeat()` - 检查资源告警 (CPU/内存/磁盘)
- `handle_task_complete()` - 创建任务失败告警
- `disconnect()` - 检查代理超时告警

**Admin 功能**:
- 告警列表视图，支持筛选和搜索
- 批量操作（确认、解决告警）
- 告警规则管理界面
- 详细信息展示（时长、重复次数等）

**使用示例**:
```python
from nodes.alerts import alert_manager, AlertType, AlertSeverity

# 创建资源告警
alert_manager.check_resource_alerts(proxy, {
    'cpu_usage': 85.0,
    'memory_usage': 78.0,
    'disk_usage': 82.0
})

# 创建任务失败告警
alert_manager.check_task_failed(task, "Connection timeout")

# 创建代理超时告警
alert_manager.check_proxy_timeout(proxy)

# 获取活动告警
active_alerts = alert_manager.get_active_alerts(
    proxy=proxy,
    severity=AlertSeverity.CRITICAL
)
```

---

## 🔴 高优先级优化（待处理）

### 3. 结构化日志系统

**当前问题**：后端使用标准的 Python logging，没有结构化日志

**建议实现**:
```python
# backend/core/logging.py
import json
import logging
import structlog

# 配置 structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_method_name,
        structlog.stdlib.add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# 自定义日志处理器
class ProxyJSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "path": record.pathname,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)
```

### 4. WebSocket 消息验证

**当前问题**：后端没有验证消息格式的完整性

**建议添加** (`backend/nodes/consumers.py`):
```python
def validate_message(data, expected_type):
    """Validate incoming WebSocket message format."""
    # Check required fields
    if 'type' not in data:
        return False, "Missing 'type' field"
    if 'payload' not in data:
        return False, "Missing 'payload' field"

    # Validate type
    if expected_type and data.get('type') != expected_type:
        return False, f"Expected type '{expected_type}', got '{data.get('type')}'"

    return True, ""
```

---

## 🟡 中优先级优化

### 5. 任务队列和优先级

**建议实现**:
```python
# backend/nodes/queue.py
class TaskQueue:
    def __init__(self):
        self.high_priority = deque()
        self.normal_priority = deque()
        self.low_priority = deque()

    def add_task(self, task_id, priority='normal'):
        queue = self._get_queue(priority)
        queue.append(task_id)

    def get_next_task(self):
        # 优先处理高优先级任务
        for queue in [self.high_priority, self.normal_priority, self.low_priority]:
            if queue:
                return queue.popleft()
        return None
```

### 6. WebSocket 心跳指标存储

**当前问题**：proxy 发送的心跳指标没有持久化到数据库

**建议更新** (`backend/nodes/consumers.py`):
```python
async def handle_heartbeat(self, data):
    metrics = data.get('metrics', {})

    # 保存详细指标到数据库
    await self.save_proxy_detailed_metrics(metrics)

    # 检查告警
    await self.check_metric_alerts(metrics)
```

**数据库模型更新** (`backend/nodes/models.py`):
```python
class ProxyMetrics(models.Model):
    proxy = models.ForeignKey('ProxyNode', on_delete=CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    # CPU
    cpu_usage = models.FloatField()
    cpu_cores = models.IntegerField()
    cpu_physical = models.IntegerField()

    # Memory
    memory_usage = models.FloatField()
    memory_total = models.BigIntegerField()
    memory_used = models.BigIntegerField()

    # Disk
    disk_usage = models.FloatField()
    disk_total = models.BigIntegerField()
    disk_used = models.BigIntegerField()

    # Network
    network_bytes_sent = models.BigIntegerField()
    network_bytes_recv = models.BigIntegerField()

    # System
    uptime = models.BigIntegerField()
    goroutines = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['proxy', '-timestamp'])
        ]
```

### 7. 请求验证和安全增强

**建议添加**:
```python
# backend/nodes/middleware.py
class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections."""
    def __init__(self):
        self.limiter = {}
        self.max_requests_per_minute = 60

    def check_rate_limit(self, proxy_id):
        key = f"ws:{proxy_id}:{datetime.now().minute}"
        if key not in self.limiter:
            self.limiter[key] = 0
        self.limiter[key] += 1
        return self.limiter[key] <= self.max_requests_per_minute
```

---

## 🟢 低优先级优化

### 8. 优雅关闭

**实现 WebSocket 优雅关闭**:
```python
class ProxyConsumer(AsyncWebsocketConsumer):
    async def disconnect(self, close_code):
        # 标记正在处理的任务为待处理状态
        await self.mark_incomplete_tasks_as_pending()
        # 保存当前状态
        await self.save_connection_state(close_code)

    async def mark_incomplete_tasks_as_pending(self):
        """将正在执行的任务标记为待处理，以便重连后继续"""
        # 实现逻辑...
```

### 9. 任务超时和重试机制

**建议添加** (`backend/nodes/services.py`):
```python
class TaskTimeoutChecker:
    """检查并处理超时任务"""
    async def check_timeouts(self):
        """检查所有运行中的任务是否超时"""
        running_tasks = ProxyTask.objects.filter(status='running')
        for task in running_tasks:
            if task.is_timeout():
                # 标记为超时
                task.timeout("Task execution timeout")
                # 发送告警
                send_timeout_alert(task)
```

### 10. 性能优化

**建议优化**:
1. 批量任务处理
2. 数据库连接池优化
3. Redis 缓存频繁查询
4. 异步任务队列

---

## 🔧 立即需要做的

### 2. 实现后端告警系统

优先级: 高

需要创建告警管理器来监控 proxy 状态和任务执行情况，包括：
- Proxy 离线告警
- 任务失败告警
- 任务超时告警
- 系统资源告警（CPU/内存/磁盘）
- 错误率告警

### 3. 结构化日志系统

优先级: 高

后端使用标准的 Python logging，建议添加结构化日志支持以便于日志分析。

### 4. WebSocket 消息验证

优先级: 高

后端没有验证消息格式的完整性，需要添加消息验证逻辑。

---

## 实现建议

建议按照以下顺序实现剩余优化：

1. **告警系统** - 提高系统可靠性，及时发现问题
2. **结构化日志** - 便于问题排查和系统分析
3. **消息验证** - 提高系统安全性
4. **心跳指标存储** - 为历史数据分析提供基础
5. **任务队列** - 优化任务调度和执行效率
6. **优雅关闭** - 提高系统的稳定性
7. **性能优化** - 提高系统吞吐量

需要我帮你实现这些优化吗？我可以从最重要的（告警系统）开始。