# 告警系统迁移总结

## 概述

完成了告警系统的统一化和迁移工作，将平台级告警模块 (`backend/alerts/`) 设为唯一的告警管理系统，并清理了旧的节点级告警模块 (`backend/nodes/alerts/`)。

## 迁移时间

2026-05-09

## 完成的工作

### 1. 更新 `backend/alerts/types.py`

**更新内容**:
- 添加了节点/Proxy 特定的 alert types（NODE_OFFLINE, NODE_TIMEOUT, NODE_ERROR）
- 添加了向后兼容的别名（PROXY_OFFLINE, PROXY_TIMEOUT, PROXY_ERROR）
- 更新了 ALERT_MESSAGES 模板，支持节点和任务相关告警
- 添加了 `normalize_alert_type()` 函数，用于将旧的 proxy_* 类型映射到新的 node_* 类型
- 添加了 `PROXY_ALERT_TYPE_MAPPING` 字典，用于向后兼容

**新增/更新的 Alert Types**:
```python
# Node/Proxy alerts
NODE_OFFLINE = "node_offline"
NODE_TIMEOUT = "node_timeout"
NODE_ERROR = "node_error"
NODE_HEALTH_DEGRADED = "node_health_degraded"

# Legacy aliases
PROXY_OFFLINE = "node_offline"  # 向后兼容
PROXY_TIMEOUT = "node_timeout"  # 向后兼容
PROXY_ERROR = "node_error"      # 向后兼容
```

### 2. 更新 `backend/alerts/manager.py`

**更新内容**:
- 添加了节点特定的检查方法：
  - `check_node_offline()` - 检查节点是否离线
  - `check_node_timeout()` - 检查节点心跳超时
  - `check_task_failed()` - 检查任务失败
  - `check_task_timeout()` - 检查任务超时
  - `check_resource_alerts()` - 检查资源告警（CPU/内存/磁盘）
  - `check_error_rate()` - 检查错误率
- 保留了向后兼容的方法：
  - `check_proxy_offline()` - 旧方法别名
  - `check_proxy_timeout()` - 旧方法别名
- 更新了 `create_alert()` 方法，添加 `normalize_alert_type()` 调用
- 更新了 `evaluate_rules()` 方法，支持实体类型和 ID 过滤
- 更新了 `get_active_alerts()` 方法，支持更多过滤选项

**方法签名**:
```python
def check_node_offline(self, node) -> Optional[Alert]
def check_node_timeout(self, node) -> Optional[Alert]
def check_resource_alerts(self, node, metrics: dict) -> List[Alert]
def check_task_failed(self, task, error: str = None) -> Optional[Alert]
def check_task_timeout(self, task) -> Optional[Alert]
def check_error_rate(self, node, error_rate: int) -> Optional[Alert]
```

### 3. 更新 `backend/alerts/__init__.py`

**更新内容**:
- 添加了便捷函数用于常见告警检查
- 导出了 `normalize_alert_type()` 函数
- 添加了节点特定的便捷方法：
  - `check_node_offline()`
  - `check_proxy_offline()` - 向后兼容
  - `check_node_timeout()`
  - `check_proxy_timeout()` - 向后兼容
  - `check_resource_alerts()`
  - `check_task_failed()`
  - `check_task_timeout()`
  - `check_error_rate()`

### 4. 删除 `backend/nodes/alerts/` 目录

**删除的内容**:
- `backend/nodes/alerts/__init__.py`
- `backend/nodes/alerts/manager.py`
- `backend/nodes/alerts/types.py`

**原因**: 这些功能已完全迁移到 `backend/alerts/` 模块，统一管理平台级告警。

### 5. 验证集成

**检查结果**:
- ✅ `backend/nodes/consumers.py` 已使用 `from alerts import get_manager`
- ✅ 没有其他地方引用 `nodes.alerts`
- ✅ `backend/nodes/models.py` 中没有 Alert 模型（已迁移到 `backend/alerts/models.py`）
- ✅ 数据库迁移已完成：
  - `nodes/migrations/0010_remove_alertrule_proxies_delete_alert_and_more.py` - 删除 nodes 中的 Alert 模型
  - `alerts/migrations/0001_initial.py` - 创建 alerts 模块的 Alert 和 AlertRule 表

## 向后兼容性

为了确保现有代码的平滑迁移，保留了以下向后兼容性：

1. **Alert Type 别名**:
   - `PROXY_OFFLINE` → `NODE_OFFLINE`
   - `PROXY_TIMEOUT` → `NODE_TIMEOUT`
   - `PROXY_ERROR` → `NODE_ERROR`

2. **Manager 方法别名**:
   - `check_proxy_offline()` → `check_node_offline()`
   - `check_proxy_timeout()` → `check_node_timeout()`

3. **便捷函数**:
   - `alerts.check_proxy_offline(proxy)` 可用
   - `alerts.check_proxy_timeout(proxy)` 可用

## 使用示例

### 创建节点离线告警

```python
from alerts import alert_manager, AlertType, AlertSeverity

alert_manager.check_node_offline(proxy)
```

### 检查资源告警

```python
from alerts import alert_manager

metrics = {
    'cpu_usage': 85.0,
    'memory_usage': 78.0,
    'disk_usage': 82.0
}
alerts = alert_manager.check_resource_alerts(proxy, metrics)
```

### 使用便捷函数

```python
from alerts import check_node_offline, check_resource_alerts

# 检查节点离线
check_node_offline(proxy)

# 检查资源告警
check_resource_alerts(proxy, metrics)
```

### 向后兼容的使用方式

```python
from alerts import check_proxy_offline, check_proxy_timeout

# 旧方法仍然可用
check_proxy_offline(proxy)
check_proxy_timeout(proxy)
```

## 数据库结构

### Alert 模型 (`alerts_alert`)

```python
class Alert(models.Model):
    id = UUIDField(primary_key=True)
    alert_type = CharField(max_length=50)  # 例如 "node_offline", "task_failed"
    severity = CharField(max_length=20)   # info, warning, critical, fatal
    status = CharField(max_length=20)     # active, acknowledged, resolved, silenced
    entity_type = CharField(max_length=50) # 例如 "nodes.ProxyNode"
    entity_id = CharField(max_length=255)
    entity_name = CharField(max_length=255)
    proxy = ForeignKey('nodes.ProxyNode')
    task = ForeignKey('nodes.ProxyTask')
    backup_task = ForeignKey('backup_tasks.BackupTask')
    repository = ForeignKey('repository.Repository')
    title = CharField(max_length=255)
    message = TextField()
    details = JSONField()
    metric_value = FloatField(null=True)
    threshold_value = FloatField(null=True)
    triggered_at = DateTimeField()
    acknowledged_at = DateTimeField(null=True)
    resolved_at = DateTimeField(null=True)
    # ... 其他字段
```

### AlertRule 模型 (`alerts_rule`)

```python
class AlertRule(models.Model):
    id = UUIDField(primary_key=True)
    name = CharField(max_length=255, unique=True)
    alert_type = CharField(max_length=50)
    severity = CharField(max_length=20)
    condition = JSONField()
    applies_to_all_entities = BooleanField(default=True)
    entity_type = CharField(max_length=50)
    target_ids = JSONField()
    threshold_value = FloatField(null=True)
    enabled = BooleanField(default=True)
    # ... 其他字段
```

## 告警类型列表

| 类型 | 值 | 严重级别 | 说明 |
|------|-----|----------|------|
| Node Offline | node_offline | warning | 节点离线 |
| Node Timeout | node_timeout | warning | 节点心跳超时 |
| Node Error | node_error | warning | 节点错误 |
| Task Failed | task_failed | warning | 任务失败 |
| Task Timeout | task_timeout | critical | 任务超时 |
| CPU High | cpu_high | warning/critical | CPU 使用率高 |
| Memory High | memory_high | warning/critical | 内存使用率高 |
| Disk High | disk_high | warning/critical | 磁盘使用率高 |
| Bandwidth Exceeded | bandwidth_exceeded | warning | 带宽超限 |
| Error Rate High | error_rate_high | warning/critical | 错误率高 |
| Connection Lost | connection_lost | warning | 连接丢失 |
| Storage Unavailable | storage_unavailable | critical | 存储不可用 |

## 告警阈值

```python
CPU_WARNING = 75.0%
CPU_CRITICAL = 90.0%

MEMORY_WARNING = 80.0%
MEMORY_CRITICAL = 95.0%

DISK_WARNING = 80.0%
DISK_CRITICAL = 90.0%

TASK_TIMEOUT_DEFAULT = 3600 秒

ERROR_RATE_WARNING = 5/分钟
ERROR_RATE_CRITICAL = 10/分钟
```

## 后续建议

1. **测试验证**:
   - 测试节点离线告警触发
   - 测试资源告警触发
   - 测试任务失败告警触发
   - 测试告警去重功能
   - 测试告警确认和解决

2. **性能优化**:
   - 监控告警系统性能
   - 优化告警检查频率
   - 优化缓存策略

3. **功能增强**:
   - 添加告警聚合功能
   - 添加告警趋势分析
   - 添加告警自动处理
   - 添加告警通知渠道配置

4. **文档完善**:
   - 更新 API 文档
   - 更新告警配置指南
   - 更新告警排查手册

## 文件变更

### 新增文件
- 无

### 修改文件
- `backend/alerts/types.py` - 添加节点特定的 alert types 和向后兼容支持
- `backend/alerts/manager.py` - 添加节点特定的检查方法
- `backend/alerts/__init__.py` - 添加便捷函数

### 删除文件
- `backend/nodes/alerts/__init__.py`
- `backend/nodes/alerts/manager.py`
- `backend/nodes/alerts/types.py`

## 迁移状态

✅ 完成 - 告警系统已成功统一到 `backend/alerts/` 模块
✅ 完成 - `backend/nodes/alerts/` 目录已删除
✅ 完成 - 向后兼容性已确保
✅ 完成 - 集成验证通过

---
