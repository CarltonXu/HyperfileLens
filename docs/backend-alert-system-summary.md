# 后端告警系统实现总结

## 概述

后端告警系统已成功实现，用于监控 Proxy 节点状态、任务执行情况和系统资源使用情况。

## 完成的功能

### 1. 告警类型 (AlertType)

支持 13 种告警类型：

**Proxy 告警**:
- `proxy_offline` - Proxy 离线
- `proxy_timeout` - Proxy 心跳超时
- `proxy_error` - Proxy 错误

**任务告警**:
- `task_failed` - 任务失败
- `task_timeout` - 任务超时
- `task_cancelled` - 任务取消

**资源告警**:
- `cpu_high` - CPU 使用率高
- `memory_high` - 内存使用率高
- `disk_high` - 磁盘使用率高
- `bandwidth_exceeded` - 带宽超限

**系统告警**:
- `connection_lost` - 连接丢失
- `error_rate_high` - 错误率高
- `storage_unavailable` - 存储不可用

### 2. 告警严重级别 (AlertSeverity)

- `INFO` - 信息
- `WARNING` - 警告
- `CRITICAL` - 严重
- `FATAL` - 致命

### 3. 告警阈值

默认阈值配置：
- CPU 警告: 75%, 严重: 90%
- 内存警告: 80%, 严重: 95%
- 磁盘警告: 80%, 严重: 90%
- 心跳超时: 3 × 心跳间隔
- 错误率警告: 5/分钟, 严重: 10/分钟

### 4. Alert 模型功能

- 关联代理、任务、仓库
- 支持确认、解决、静音操作
- 自动去重（5分钟内相同告警合并）
- 重复计数和首次/最后发生时间跟踪
- 通知发送状态跟踪
- 告警时长统计
- 支持元数据存储

### 5. AlertRule 模型功能

- 自定义告警规则
- 灵活的条件配置（JSON格式）
- 支持作用域（所有代理或特定代理）
- 可配置冷却期防止告警风暴
- 多通知通道支持
- 启用/禁用规则

### 6. AlertManager 功能

提供以下方法：
- `create_alert()` - 创建新告警
- `check_proxy_offline()` - 检查代理离线
- `check_proxy_timeout()` - 检查代理超时
- `check_task_failed()` - 检查任务失败
- `check_task_timeout()` - 检查任务超时
- `check_resource_alerts()` - 检查资源告警
- `check_error_rate()` - 检查错误率
- `evaluate_rules()` - 评估告警规则
- `get_active_alerts()` - 获取活动告警
- `acknowledge_alert()` - 确认告警
- `resolve_alert()` - 解决告警
- `silence_alert()` - 静音告警

### 7. 集成点

告警系统已集成到以下位置：

**backend/nodes/consumers.py**:
- `handle_heartbeat()` - 检查资源告警 (CPU/内存/磁盘)
- `handle_task_complete()` - 创建任务失败告警
- `disconnect()` - 检查代理超时告警

### 8. Django Admin 界面

提供完整的管理界面：
- 告警列表视图，支持筛选和搜索
- 告警规则管理界面
- 批量操作（确认、解决告警）
- 详细信息展示（时长、重复次数等）
- 进度详细信息展示

## 文件结构

```
backend/nodes/
├── alerts/
│   ├── __init__.py        # 模块初始化和导出
│   ├── manager.py         # AlertManager 类
│   └── types.py           # 告警类型定义
├── admin.py               # Django Admin 配置（新建）
├── consumers.py           # 集成告警检查
└── models.py              # Alert 和 AlertRule 模型
```

## 数据库迁移

- `nodes/migrations/0009_alertrule_alert.py` - 创建告警相关表

## 使用示例

```python
from nodes.alerts import alert_manager, AlertType, AlertSeverity
from nodes.models import ProxyNode, ProxyTask

# 获取代理
proxy = ProxyNode.objects.get(name='my-proxy')

# 检查资源告警
alert_manager.check_resource_alerts(proxy, {
    'cpu_usage': 85.0,
    'memory_usage': 78.0,
    'disk_usage': 82.0
})

# 创建任务失败告警
task = ProxyTask.objects.get(id='task-id')
alert_manager.check_task_failed(task, "Connection timeout")

# 创建代理超时告警
alert_manager.check_proxy_timeout(proxy)

# 获取活动告警
active_alerts = alert_manager.get_active_alerts(
    proxy=proxy,
    severity=AlertSeverity.CRITICAL,
    limit=50
)

# 确认告警
for alert in active_alerts:
    alert_manager.acknowledge_alert(alert.id, request.user, "Investigating")

# 解决告警
alert_manager.resolve_alert(alert.id, request.user, "Issue resolved")
```

## 配置建议

1. **告警阈值**: 根据实际环境调整 AlertThresholds 中的阈值
2. **冷却期**: 调整告警规则的冷却期避免告警风暴
3. **通知渠道**: 配置通知渠道（邮件、Slack、Webhook 等）
4. **告警规则**: 创建自定义告警规则以满足特定需求

## 后续改进建议

1. **通知集成**: 集成邮件、Slack、Webhook 通知
2. **告警聚合**: 实现告警聚合以减少通知量
3. **趋势分析**: 基于历史数据的趋势告警
4. **自动处理**: 实现告警自动处理逻辑
5. **告警面板**: 创建专门的告警展示面板

## 测试建议

1. 测试资源告警触发（模拟高 CPU/内存/磁盘）
2. 测试任务失败告警
3. 测试代理超时告警
4. 测试告警去重功能
5. 测试告警确认和解决流程
6. 测试告警规则评估
7. 测试 Admin 界面操作

## 完成

实现日期: 2026-05-09