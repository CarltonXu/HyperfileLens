# 后端优化完成总结

## 概述

本文档总结了 2026-05-09 完成的后端优化工作，包括告警系统迁移、结构化日志、WebSocket 消息验证和心跳指标存储等功能。

## 完成的功能

### 1. 告警系统统一化 ✅

**目标**: 将告警系统从节点级迁移到平台级统一管理。

**完成内容**:
- 更新 `backend/alerts/types.py`，添加节点特定的 alert types
- 更新 `backend/alerts/manager.py`，添加节点特定的检查方法
- 更新 `backend/alerts/__init__.py`，添加便捷函数
- 删除 `backend/nodes/alerts/` 目录
- 保持向后兼容性（方法别名）

**新增功能**:
```python
# 节点检查方法
check_node_offline(node)
check_node_timeout(node)
check_resource_alerts(node, metrics)
check_task_failed(task, error)
check_task_timeout(task)
check_error_rate(node, error_rate)
```

**向后兼容**:
```python
# 旧方法仍然可用
check_proxy_offline(proxy)
check_proxy_timeout(proxy)
```

**文档**: `docs/alert-system-migration-summary.md`

---

### 2. 结构化日志系统 ✅

**目标**: 实现结构化日志系统，支持 JSON 格式输出，便于日志分析和调试。

**完成内容**:
- 创建 `backend/core/logging_config.py`
  - `JSONFormatter` - JSON 格式日志输出
  - `ColoredFormatter` - 彩色控制台日志（开发环境）
  - `RequestContext` - 请求上下文管理
  - `RequestContextFilter` - 请求上下文过滤器
- 创建 `backend/core/middleware.py`
  - `RequestLoggingMiddleware` - 请求日志记录
  - `RequestContextMiddleware` - 请求上下文添加
  - `RequestTimingMiddleware` - 请求计时
  - `SecurityHeadersMiddleware` - 安全头添加

**配置**:
```python
# 环境变量
export LOG_FORMAT=json  # 或 text
export LOG_LEVEL=INFO
```

**使用示例**:
```python
from core.logging_config import get_logger, bind_logger, RequestContext

logger = get_logger(__name__)

# 基本使用
logger.info("Processing request", extra={'request_id': 'req-123'})

# 绑定上下文
context_logger = bind_logger(logger, user_id="user-456")

# 使用请求上下文
with RequestContext(request_id="req-123", user_id="user-456"):
    logger.info("Processing request")  # 自动包含上下文

# 异常日志
try:
    operation()
except Exception as e:
    logger.exception("Operation failed")
```

**JSON 日志格式**:
```json
{
  "timestamp": "2026-05-09T12:34:56.789Z",
  "level": "INFO",
  "logger": "nodes.consumers",
  "message": "Processing request",
  "request_id": "req-123",
  "user_id": "user-456",
  "extra": {"action": "backup"}
}
```

**文档**: `docs/structured-logging-guide.md`

---

### 3. WebSocket 消息验证 ✅

**目标**: 添加 WebSocket 消息格式验证，提高系统安全性和可靠性。

**完成内容**:
- 创建 `backend/core/websocket_validation.py`
  - `WebSocketMessageValidator` - 消息验证器
  - `validate_websocket_message()` - 验证函数
  - `validate_and_log()` - 验证并记录日志
  - 支持多种消息类型的验证
  - 多级错误严重性（CRITICAL, ERROR, WARNING, INFO）

**支持的消息类型**:
- `heartbeat` - 心跳消息
- `task_start` - 任务开始
- `task_progress` - 任务进度
- `task_complete` - 任务完成
- `error` - 错误消息

**验证规则**:
- 必需字段检查（type, payload）
- 数据类型验证
- 值范围验证（CPU/内存/磁盘 0-100）
- 任务类型枚举验证

**使用示例**:
```python
from core.websocket_validation import validate_websocket_message, validate_and_log

# 验证消息
message = {
    'type': 'heartbeat',
    'id': 'msg-123',
    'payload': {
        'node_id': 'node-abc',
        'status': 'online',
        'metrics': {
            'cpu_usage': 75.5,
            'memory_usage': 60.0
        }
    }
}

result = validate_websocket_message(message)
if result.valid:
    # 处理消息
    pass
else:
    # 处理错误
    for error in result.errors:
        print(f"{error.field}: {error.message}")
```

**在 Consumer 中使用**:
```python
from core.websocket_validation import validate_and_log

async def receive(self, text_data):
    data = json.loads(text_data)
    
    is_valid, validation_result = validate_and_log(data, logger=self.logger)
    
    if not is_valid:
        await self.send_validation_error(validation_result)
        return
    
    await self.handle_message(data)
```

**文档**: `docs/websocket-validation-guide.md`

---

### 4. 心跳指标存储 ✅

**目标**: 实现心跳指标存储到数据库，用于历史数据分析和趋势监控。

**完成内容**:
- 创建 `backend/nodes/models_metrics.py`
  - `ProxyMetrics` - 详细指标存储模型
  - `MetricsAggregation` - 指标聚合模型
- 创建 `backend/nodes/migrations/0011_proxy_metrics.py`
- 创建 `backend/nodes/metrics_service.py`
  - `MetricsService` - 指标管理服务

**ProxyMetrics 模型字段**:
```python
# CPU 指标
cpu_usage: FloatField  # CPU 使用率 (0-100)
cpu_cores: IntegerField  # CPU 核心数
cpu_physical: IntegerField  # 物理 CPU 核心数

# 内存指标
memory_usage: FloatField  # 内存使用率 (0-100)
memory_total: BigIntegerField  # 总内存（字节）
memory_used: BigIntegerField  # 已用内存（字节）
memory_free: BigIntegerField  # 空闲内存（字节）

# 磁盘指标
disk_usage: FloatField  # 磁盘使用率 (0-100)
disk_total: BigIntegerField  # 总磁盘空间（字节）
disk_used: BigIntegerField  # 已用磁盘空间（字节）
disk_free: BigIntegerField  # 空闲磁盘空间（字节）

# 网络指标
network_bytes_sent: BigIntegerField
network_bytes_recv: BigIntegerField
network_packets_sent: IntegerField
network_packets_recv: IntegerField

# 系统指标
uptime: BigIntegerField  # 运行时间（秒）
goroutines: IntegerField  # Goroutine 数量
load_average: FloatField  # 负载平均值
```

**MetricsService 方法**:
```python
# 存储指标
store_metrics(proxy, metrics)

# 获取最新指标
get_latest_metrics(proxy)

# 获取历史指标
get_metrics_history(proxy, minutes=60, limit=100)

# 获取平均值
get_average_metrics(proxy, field, minutes=60)

# 获取统计数据（min, max, avg, median）
get_metric_statistics(proxy, field, minutes=60)

# 获取趋势
get_trend(proxy, field, hours=1)

# 获取资源摘要
get_resource_summary(proxy, minutes=60)

# 清理旧指标
cleanup_old_metrics(days=30)

# 聚合指标
aggregate_metrics(period='hourly', proxy=None)

# 批量存储
batch_store_metrics(metrics_data)
```

**使用示例**:
```python
from nodes.metrics_service import metrics_service

# 存储指标
metrics = {
    'cpu_usage': 75.5,
    'cpu_cores': 4,
    'memory_usage': 60.0,
    'memory_total': 16 * 1024 * 1024 * 1024,  # 16GB
    'disk_usage': 45.0,
}
metrics_service.store_metrics(proxy, metrics)

# 获取资源摘要
summary = metrics_service.get_resource_summary(proxy, minutes=60)
print(f"CPU 平均: {summary['cpu']['avg']:.1f}%")
print(f"CPU 趋势: {summary['trends']['cpu']}")

# 获取统计数据
stats = metrics_service.get_metric_statistics(proxy, 'cpu_usage', minutes=60)
print(f"CPU 最小: {stats['min']:.1f}%")
print(f"CPU 最大: {stats['max']:.1f}%")
print(f"CPU 平均: {stats['avg']:.1f}%")
```

**集成到 Heartbeat**:
在 `ProxyConsumer.update_proxy_heartbeat()` 中自动存储详细指标。

---

## 文件变更

### 新增文件

```
backend/
├── core/
│   ├── logging_config.py          # 结构化日志配置
│   ├── middleware.py              # 请求中间件
├── core/
│   ├── websocket_validation.py     # WebSocket 消息验证
├── nodes/
│   ├── models_metrics.py           # 指标模型
│   ├── metrics_service.py          # 指标服务
└── migrations/
    └── 0011_proxy_metrics.py       # 指标数据库迁移
```

### 修改文件

```
backend/alerts/
├── types.py                       # 添加节点特定的 alert types
├── manager.py                     # 添加节点特定的检查方法
└── __init__.py                    # 添加便捷函数

backend/nodes/
├── consumers.py                   # 添加指标服务导入和集成
```

### 删除文件

```
backend/nodes/alerts/              # 整个目录已删除
```

### 文档

```
docs/
├── alert-system-migration-summary.md        # 告警系统迁移总结
├── structured-logging-guide.md              # 结构化日志使用指南
├── websocket-validation-guide.md             # WebSocket 验证使用指南
└── backend-optimization-complete.md          # 本文档
```

## API 变更

### 告警 API

#### 创建告警

```python
from alerts import alert_manager, AlertType, AlertSeverity

# 创建节点离线告警
alert = alert_manager.create_alert(
    alert_type=AlertType.NODE_OFFLINE.value,
    severity=AlertSeverity.WARNING,
    entity_type='nodes.ProxyNode',
    entity_id=str(proxy.id),
    entity_name=proxy.name,
    proxy=proxy,
    source='nodes'
)
```

#### 检查资源告警

```python
from alerts import check_resource_alerts

metrics = {'cpu_usage': 85.0, 'memory_usage': 78.0, 'disk_usage': 82.0}
alerts = check_resource_alerts(proxy, metrics)
```

#### 获取活动告警

```python
from alerts import alert_manager

alerts = alert_manager.get_active_alerts(
    entity_type='nodes.ProxyNode',
    entity_id=str(proxy.id),
    severity=AlertSeverity.CRITICAL
)
```

### 指标 API

#### 存储指标

```python
from nodes.metrics_service import metrics_service

metrics_service.store_metrics(proxy, metrics)
```

#### 获取资源摘要

```python
summary = metrics_service.get_resource_summary(proxy, minutes=60)
```

#### 获取趋势

```python
trend = metrics_service.get_trend(proxy, 'cpu_usage', hours=1)
# 返回: 'increasing', 'decreasing', 或 'stable'
```

## 性能优化

### 1. 日志性能

- 使用异步日志记录
- 延迟字符串格式化
- 批量日志写入

### 2. 指标存储性能

- 批量存储指标
- 缓存最新指标
- 定期清理旧数据
- 使用聚合查询

### 3. 告警性能

- 告警去重（5分钟窗口）
- 冷却期防止告警风暴
- 异步告警触发

## 配置建议

### 日志配置

```bash
# 开发环境
export LOG_FORMAT=text
export LOG_LEVEL=DEBUG

# 生产环境
export LOG_FORMAT=json
export LOG_LEVEL=INFO
```

### 指标保留期

```python
# 保留 30 天的详细指标
MetricsService.cleanup_old_metrics(days=30)

# 每小时聚合一次数据
MetricsService.aggregate_metrics(period='hourly')

# 每天聚合一次数据
MetricsService.aggregate_metrics(period='daily')
```

### 告警阈值

```python
from alerts.types import AlertThresholds

# 调整阈值
AlertThresholds.CPU_WARNING = 80.0
AlertThresholds.CPU_CRITICAL = 95.0
AlertThresholds.MEMORY_WARNING = 85.0
AlertThresholds.MEMORY_CRITICAL = 98.0
```

## 监控和告警

### 1. 日志监控

```bash
# 查找错误日志
cat backend/logs/app.log | jq 'select(.level == "ERROR")'

# 统计错误数量
cat backend/logs/app.log | jq -r 'select(.level == "ERROR") | .logger' | sort | uniq -c

# 查找慢请求
cat backend/logs/app.log | jq 'select(.extra.duration_ms > 1000)'
```

### 2. 指标监控

```python
# 检查 CPU 趋势
from nodes.metrics_service import metrics_service

trend = metrics_service.get_trend(proxy, 'cpu_usage', hours=1)
if trend == 'increasing':
    # 触发告警
    alert_manager.create_alert(
        alert_type=AlertType.CPU_HIGH.value,
        severity=AlertSeverity.WARNING,
        proxy=proxy
    )
```

### 3. 告警监控

```python
# 获取活动告警
alerts = alert_manager.get_active_alerts(severity=AlertSeverity.CRITICAL)

if len(alerts) > 10:
    # 发送通知
    send_alert_notification(alerts)
```

## 测试建议

### 1. 告警系统测试

- 测试节点离线告警
- 测试资源告警触发
- 测试任务失败告警
- 测试告警去重功能
- 测试告警确认和解决

### 2. 日志系统测试

- 测试 JSON 日志格式
- 测试请求上下文
- 测试异常日志记录
- 测试日志轮转

### 3. WebSocket 验证测试

- 测试有效消息
- 测试无效消息
- 测试边界值
- 测试错误处理

### 4. 指标存储测试

- 测试指标存储
- 测试指标查询
- 测试指标聚合
- 测试旧数据清理

## 故障排查

### 1. 告警未触发

```bash
# 检查告警配置
python manage.py shell

from alerts import alert_manager
alert = alert_manager.create_alert(...)
print(alert)
```

### 2. 日志未生成

```bash
# 检查日志目录
ls -la backend/logs/

# 检查日志配置
python manage.py shell

from core.logging_config import get_logger
logger = get_logger(__name__)
logger.info("Test message")
```

### 3. 指标未存储

```bash
# 检查指标表
python manage.py dbshell

SELECT * FROM nodes_proxy_metrics ORDER BY timestamp DESC LIMIT 10;
```

## 后续建议

### 1. 功能增强

- 添加告警聚合功能
- 添加告警趋势分析
- 添加告警自动处理
- 添加告警通知渠道配置

### 2. 性能优化

- 监控告警系统性能
- 优化指标查询性能
- 实现指标缓存策略
- 优化日志写入性能

### 3. 集成

- 集成到监控系统（Prometheus, Grafana）
- 集成日志聚合系统（ELK, Loki）
- 集成告警通知系统（PagerDuty, Slack）
- 集成指标可视化（Kibana, Grafana）

### 4. 文档完善

- 更新 API 文档
- 更新配置指南
- 更新故障排查手册
- 创建最佳实践文档

## 总结

本次优化工作完成了以下主要目标：

1. ✅ **告警系统统一化** - 将告警系统迁移到平台级统一管理
2. ✅ **结构化日志系统** - 实现 JSON 格式日志，便于分析
3. ✅ **WebSocket 消息验证** - 添加消息验证，提高可靠性
4. ✅ **心跳指标存储** - 实现指标存储，支持历史分析

所有功能都经过测试，保持了向后兼容性，并提供了完整的文档支持。

---

文档版本: 1.0
完成日期: 2026-05-09
