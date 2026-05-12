# Alert Center 告警中心技术实现方案

## 1. 实现目标

为平台实现一套全局告警中心，支持：

- 告警策略配置
- 资源指标告警
- 可用性告警
- 任务告警
- 事件告警
- 系统告警
- 告警触发
- 告警恢复
- 告警通知
- 当前告警查看
- 历史告警查看
- 告警确认
- 手动恢复

一期要求：告警类型完整，但功能保持简化，不实现复杂的通知策略、升级通知、静默、复杂聚合等高级能力。

---

## 2. 技术栈假设

### 前端

- Vue 3
- TypeScript
- Element Plus / Naive UI / Ant Design Vue 均可
- Axios
- Vue Router
- Pinia

### 后端

- Django
- Django REST Framework
- PostgreSQL
- Celery
- Redis

---

## 3. 告警类型

一期需要支持 5 类告警：

| Type         | 名称               | 说明                                           |
| ------------ | ------------------ | ---------------------------------------------- |
| metric       | Metric Alert       | 指标告警，例如 CPU、Memory、Disk、容量         |
| availability | Availability Alert | 可用性告警，例如 Proxy 离线、Repository 不可达 |
| job          | Job Alert          | 任务告警，例如 Backup 失败、Restore 失败       |
| event        | Event Alert        | 事件告警，例如用户删除、License 过期           |
| system       | System Alert       | 系统告警，例如平台服务异常、数据库不可达       |

---

## 4. 告警等级

```ts
type AlertSeverity = 'critical' | 'warning' | 'info'
Severity	说明
critical	严重告警
warning	警告告警
info	信息告警
5. 告警状态
type AlertStatus = 'pending' | 'firing' | 'acknowledged' | 'resolved'
Status	说明
pending	已满足条件，但未达到持续时间
firing	正在告警
acknowledged	已确认
resolved	已恢复
6. 资源类型
type ResourceType =
  | 'sync_proxy'
  | 'gateway'
  | 'agent_proxy'
  | 'backup_repository'
  | 'source_resource'
  | 'target_storage'
  | 'job'
  | 'system_service'
  | 'license'
  | 'user'
Resource Type	说明
sync_proxy	Sync Proxy
gateway	Gateway
agent_proxy	Agent Proxy
backup_repository	Backup Repository
source_resource	Source Resource
target_storage	Target Storage
job	Job
system_service	System Service
license	License
user	User
7. 页面设计

一期只实现 4 个页面：

Alert Policies
Active Alerts
Alert History
Notification Channels
8. 页面一：Alert Policies
8.1 功能

用于管理告警策略。

支持：

创建策略
编辑策略
删除策略
启用策略
禁用策略
复制策略
8.2 列表字段
字段	说明
Name	告警名称
Type	告警类型
Severity	告警等级
Resource Type	资源类型
Enabled	是否启用
Notification Channels	通知渠道
Created At	创建时间
Actions	操作
8.3 操作按钮
Edit
Duplicate
Enable / Disable
Delete
9. 页面二：Create / Edit Alert Policy
9.1 页面结构

创建和编辑策略使用一个普通表单，不做复杂步骤向导。

表单分为 5 个区域：

Basic Info
Monitor Target
Trigger Rule
Recovery Rule
Notification
9.2 Basic Info 字段
字段	类型	必填	说明
name	input	是	告警名称
description	textarea	否	告警描述
type	select	是	metric / availability / job / event / system
severity	select	是	critical / warning / info
enabled	switch	是	是否启用
9.3 Monitor Target 字段
字段	类型	必填	说明
resource_type	select	是	资源类型
resource_ids	multi-select	否	选择具体资源
scope	radio	是	all / selected

说明：

当 scope = all 时，resource_ids 可以为空。
当 scope = selected 时，resource_ids 必须有值。
Event Alert 可以不强制选择 resource_ids。
System Alert 可以选择 system_service。
9.4 Notification 字段
字段	类型	必填	说明
notification_channel_ids	multi-select	否	选择通知渠道

一期不做 Notification Policy，直接在 Alert Policy 上绑定 Notification Channels。

10. Metric Alert 设计
10.1 支持资源和指标
Resource Type	Metrics
sync_proxy	cpu_usage, memory_usage, disk_usage, network_rx, network_tx
gateway	cpu_usage, memory_usage, disk_usage, network_rx, network_tx
agent_proxy	cpu_usage, memory_usage, disk_usage, network_rx, network_tx
backup_repository	capacity_usage, used_size, free_size
source_resource	capacity_usage, data_size, file_count
target_storage	capacity_usage, used_size, free_size
10.2 trigger_rule
{
  "metric_key": "cpu_usage",
  "operator": ">=",
  "threshold": 80,
  "unit": "%",
  "duration_seconds": 300,
  "evaluation_interval_seconds": 60
}
10.3 字段说明
字段	说明
metric_key	指标 key
operator	比较符
threshold	阈值
unit	单位
duration_seconds	持续时间
evaluation_interval_seconds	检测周期
10.4 operator
type Operator = '>' | '>=' | '<' | '<=' | '==' | '!='
10.5 recovery_rule
{
  "enabled": true,
  "operator": "<",
  "threshold": 70,
  "duration_seconds": 180
}

含义：

CPU 使用率低于 70%，持续 3 分钟后自动恢复。
11. Availability Alert 设计
11.1 支持场景
Alert	Resource Type
Sync Proxy Offline	sync_proxy
Agent Proxy Offline	agent_proxy
Gateway Offline	gateway
Repository Unreachable	backup_repository
Source Resource Unreachable	source_resource
Target Storage Unreachable	target_storage
11.2 trigger_rule
{
  "check_type": "heartbeat",
  "timeout_seconds": 60,
  "duration_seconds": 300
}
11.3 字段说明
字段	说明
check_type	检查方式
timeout_seconds	超时时间
duration_seconds	持续异常多久触发
11.4 check_type
type AvailabilityCheckType =
  | 'heartbeat'
  | 'connection'
  | 'api_health'
11.5 recovery_rule
{
  "enabled": true,
  "recovery_condition": "heartbeat_restored",
  "duration_seconds": 120
}

含义：

心跳恢复并持续 2 分钟后，自动恢复告警。
12. Job Alert 设计
12.1 支持 Job Type
Job Type	说明
backup	备份任务
sync	同步任务
restore	恢复任务
verify	校验任务
cleanup	清理任务
12.2 支持 Event Type
Event Type	说明
job_failed	任务失败
job_timeout	任务超时
retry_exceeded	超过重试次数
partial_success	部分成功
12.3 trigger_rule 示例一：任务失败
{
  "job_type": "backup",
  "event_type": "job_failed",
  "consecutive_failures": 1
}
12.4 trigger_rule 示例二：任务超时
{
  "job_type": "backup",
  "event_type": "job_timeout",
  "timeout_seconds": 7200
}
12.5 recovery_rule
{
  "enabled": true,
  "recovery_condition": "next_success"
}

含义：

下一次同类型任务执行成功后，自动恢复之前的 Job Alert。
13. Event Alert 设计
13.1 Event Category
type EventCategory =
  | 'user'
  | 'license'
  | 'repository'
  | 'configuration'
  | 'security'
13.2 User Events
user_created
user_deleted
user_disabled
user_enabled
password_changed
user_role_changed
login_success
login_failed
logout
13.3 License Events
license_added
license_updated
license_expired
license_near_expiration
license_capacity_exceeded
13.4 Repository Events
repository_created
repository_deleted
repository_updated
repository_unreachable
repository_readonly
repository_capacity_low
13.5 Configuration Events
configuration_changed
notification_channel_changed
alert_policy_changed
repository_config_changed
proxy_config_changed
13.6 Security Events
multiple_login_failures
api_token_created
api_token_deleted
permission_changed
mfa_disabled
13.7 trigger_rule
{
  "event_category": "user",
  "event_types": [
    "user_deleted",
    "login_failed"
  ]
}
13.8 recovery_rule

Event Alert 一期默认不自动恢复。

{
  "enabled": false
}

建议处理方式：

一次性事件触发后直接记录为 firing。
用户可手动 acknowledge。
用户可手动 resolve。
对于 license_near_expiration 这类事件，后续可扩展自动恢复。
14. System Alert 设计
14.1 支持场景
Event	说明
api_service_down	API 服务异常
database_unreachable	数据库不可达
celery_worker_down	Celery Worker 异常
scheduler_down	定时任务异常
disk_space_low	平台节点磁盘不足
14.2 trigger_rule
{
  "check_type": "service_health",
  "service_name": "celery_worker",
  "duration_seconds": 300
}
14.3 recovery_rule
{
  "enabled": true,
  "recovery_condition": "service_restored",
  "duration_seconds": 120
}
15. Notification Channels 设计
15.1 一期支持类型
type NotificationChannelType =
  | 'email'
  | 'webhook'
  | 'dingtalk'
  | 'wecom'

建议最小实现：

email
webhook

钉钉和企业微信可以预留字段。

15.2 Notification Channel 字段
字段	类型	说明
name	string	通知渠道名称
type	string	email / webhook / dingtalk / wecom
enabled	boolean	是否启用
config	json	渠道配置
15.3 Email Config
{
  "smtp_host": "smtp.example.com",
  "smtp_port": 587,
  "smtp_username": "alert@example.com",
  "smtp_password": "******",
  "from_email": "alert@example.com",
  "to_emails": [
    "admin@example.com"
  ],
  "use_tls": true
}
15.4 Webhook Config
{
  "url": "https://example.com/webhook",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer token"
  }
}
16. 数据库设计
16.1 alert_policies
CREATE TABLE alert_policies (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,

    resource_type VARCHAR(100),
    scope VARCHAR(50) DEFAULT 'selected',
    resource_ids JSONB,

    trigger_rule JSONB NOT NULL,
    recovery_rule JSONB,
    notification_channel_ids JSONB,

    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
16.2 alert_records
CREATE TABLE alert_records (
    id UUID PRIMARY KEY,

    policy_id UUID,
    type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,

    resource_type VARCHAR(100),
    resource_id UUID,
    resource_name VARCHAR(255),

    title VARCHAR(255) NOT NULL,
    message TEXT,

    current_value NUMERIC,
    threshold_value NUMERIC,
    unit VARCHAR(50),

    fingerprint VARCHAR(255),
    metadata JSONB,

    first_triggered_at TIMESTAMP,
    last_triggered_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    acknowledged_by UUID,
    resolved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
16.3 notification_channels
CREATE TABLE notification_channels (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
16.4 notification_logs
CREATE TABLE notification_logs (
    id UUID PRIMARY KEY,
    alert_record_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);
16.5 建议索引
CREATE INDEX idx_alert_records_status ON alert_records(status);
CREATE INDEX idx_alert_records_type ON alert_records(type);
CREATE INDEX idx_alert_records_severity ON alert_records(severity);
CREATE INDEX idx_alert_records_fingerprint ON alert_records(fingerprint);
CREATE INDEX idx_alert_policies_enabled ON alert_policies(enabled);
CREATE INDEX idx_alert_policies_type ON alert_policies(type);
17. Django App 结构
apps/alerts/
├── __init__.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── choices.py
├── tasks.py
├── services/
│   ├── evaluator.py
│   ├── metric_evaluator.py
│   ├── availability_evaluator.py
│   ├── job_evaluator.py
│   ├── event_handler.py
│   ├── system_evaluator.py
│   ├── notifier.py
│   └── fingerprint.py
18. 后端模型
18.1 AlertPolicy

字段：

class AlertPolicy(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    type = models.CharField(max_length=50)
    severity = models.CharField(max_length=50)
    enabled = models.BooleanField(default=True)

    resource_type = models.CharField(max_length=100, null=True, blank=True)
    scope = models.CharField(max_length=50, default="selected")
    resource_ids = models.JSONField(default=list, blank=True)

    trigger_rule = models.JSONField()
    recovery_rule = models.JSONField(null=True, blank=True)
    notification_channel_ids = models.JSONField(default=list, blank=True)

    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
18.2 AlertRecord
class AlertRecord(models.Model):
    id = models.UUIDField(primary_key=True)

    policy_id = models.UUIDField(null=True, blank=True)
    type = models.CharField(max_length=50)
    severity = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    resource_type = models.CharField(max_length=100, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=255, null=True, blank=True)

    title = models.CharField(max_length=255)
    message = models.TextField(null=True, blank=True)

    current_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)

    fingerprint = models.CharField(max_length=255, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    first_triggered_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.UUIDField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
19. 后端 API 设计
19.1 Alert Policies
GET    /api/alerts/policies/
POST   /api/alerts/policies/
GET    /api/alerts/policies/{id}/
PUT    /api/alerts/policies/{id}/
DELETE /api/alerts/policies/{id}/
POST   /api/alerts/policies/{id}/enable/
POST   /api/alerts/policies/{id}/disable/
POST   /api/alerts/policies/{id}/duplicate/
19.2 Alert Records
GET  /api/alerts/records/
GET  /api/alerts/records/{id}/
POST /api/alerts/records/{id}/acknowledge/
POST /api/alerts/records/{id}/resolve/

筛选参数：

status
type
severity
resource_type
resource_id
start_time
end_time
19.3 Notification Channels
GET    /api/alerts/notification-channels/
POST   /api/alerts/notification-channels/
GET    /api/alerts/notification-channels/{id}/
PUT    /api/alerts/notification-channels/{id}/
DELETE /api/alerts/notification-channels/{id}/
POST   /api/alerts/notification-channels/{id}/test/
19.4 Metadata API
GET /api/alerts/metadata/alert-types/
GET /api/alerts/metadata/resource-types/
GET /api/alerts/metadata/metrics/?resource_type=sync_proxy
GET /api/alerts/metadata/job-types/
GET /api/alerts/metadata/event-types/
GET /api/alerts/metadata/system-check-types/
20. 核心告警逻辑
20.1 Fingerprint 规则

同一个策略、同一个资源、同一个指标，只允许存在一条活跃告警。

fingerprint = sha256(f"{policy.id}:{resource_id}:{alert_key}")

alert_key 示例：

metric_key
event_type
job_type + event_type
check_type
service_name
20.2 创建或更新告警

逻辑：

def fire_alert(policy, resource, title, message, current_value=None):
    fingerprint = build_fingerprint(policy, resource)

    alert = AlertRecord.objects.filter(
        fingerprint=fingerprint,
        status__in=["pending", "firing", "acknowledged"]
    ).first()

    if alert:
        alert.status = "firing"
        alert.last_triggered_at = now()
        alert.current_value = current_value
        alert.save()
        return alert

    alert = AlertRecord.objects.create(
        policy_id=policy.id,
        type=policy.type,
        severity=policy.severity,
        status="firing",
        resource_type=policy.resource_type,
        resource_id=resource.id if resource else None,
        resource_name=resource.name if resource else None,
        title=title,
        message=message,
        current_value=current_value,
        fingerprint=fingerprint,
        first_triggered_at=now(),
        last_triggered_at=now()
    )

    send_notification(alert)
    return alert
20.3 自动恢复告警
def resolve_alert(alert):
    alert.status = "resolved"
    alert.resolved_at = now()
    alert.save()

    send_resolved_notification(alert)
21. Celery 定时任务
21.1 周期任务
@shared_task
def evaluate_alert_policies():
    policies = AlertPolicy.objects.filter(enabled=True)

    for policy in policies:
        if policy.type == "metric":
            evaluate_metric_policy(policy)

        elif policy.type == "availability":
            evaluate_availability_policy(policy)

        elif policy.type == "system":
            evaluate_system_policy(policy)

建议执行周期：

每 60 秒执行一次
21.2 Job Alert 触发方式

Job Alert 不通过定时扫描为主，而是在任务完成时触发事件。

def on_job_finished(job):
    if job.status in ["failed", "timeout", "partial_success"]:
        handle_job_event(job)

    if job.status == "success":
        recover_job_alerts(job)
21.3 Event Alert 触发方式

业务模块调用：

emit_platform_event(
    category="user",
    event_type="user_deleted",
    actor=request.user,
    target=user,
    metadata={}
)

事件处理：

def handle_platform_event(event):
    policies = AlertPolicy.objects.filter(
        enabled=True,
        type="event"
    )

    for policy in policies:
        rule = policy.trigger_rule

        if rule["event_category"] == event.category and event.type in rule["event_types"]:
            fire_alert(
                policy=policy,
                resource=None,
                title=f"Event Alert: {event.type}",
                message=f"Platform event triggered: {event.type}",
                current_value=None
            )
22. 通知逻辑
22.1 发送通知
def send_notification(alert):
    policy = get_policy(alert.policy_id)
    channel_ids = policy.notification_channel_ids or []

    for channel_id in channel_ids:
        channel = NotificationChannel.objects.get(id=channel_id)

        if not channel.enabled:
            continue

        try:
            if channel.type == "email":
                send_email(channel, alert)
            elif channel.type == "webhook":
                send_webhook(channel, alert)

            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                status="success"
            )

        except Exception as e:
            NotificationLog.objects.create(
                alert_record_id=alert.id,
                channel_id=channel.id,
                status="failed",
                error_message=str(e)
            )
23. 前端目录结构
src/views/alerts/
├── AlertPolicies.vue
├── AlertPolicyCreate.vue
├── AlertPolicyEdit.vue
├── ActiveAlerts.vue
├── AlertHistory.vue
├── NotificationChannels.vue

src/components/alerts/
├── AlertSeverityTag.vue
├── AlertStatusTag.vue
├── AlertTypeTag.vue
├── ResourceSelector.vue
├── MetricRuleForm.vue
├── AvailabilityRuleForm.vue
├── JobRuleForm.vue
├── EventRuleForm.vue
├── SystemRuleForm.vue
├── RecoveryRuleForm.vue
├── NotificationChannelSelector.vue
24. 前端路由
export default [
  {
    path: '/alerts',
    redirect: '/alerts/policies',
    children: [
      {
        path: 'policies',
        name: 'AlertPolicies',
        component: () => import('@/views/alerts/AlertPolicies.vue')
      },
      {
        path: 'policies/create',
        name: 'AlertPolicyCreate',
        component: () => import('@/views/alerts/AlertPolicyCreate.vue')
      },
      {
        path: 'policies/:id/edit',
        name: 'AlertPolicyEdit',
        component: () => import('@/views/alerts/AlertPolicyEdit.vue')
      },
      {
        path: 'active',
        name: 'ActiveAlerts',
        component: () => import('@/views/alerts/ActiveAlerts.vue')
      },
      {
        path: 'history',
        name: 'AlertHistory',
        component: () => import('@/views/alerts/AlertHistory.vue')
      },
      {
        path: 'notification-channels',
        name: 'NotificationChannels',
        component: () => import('@/views/alerts/NotificationChannels.vue')
      }
    ]
  }
]
25. 前端动态表单逻辑
25.1 根据 type 显示不同 Rule Form
<MetricRuleForm
  v-if="form.type === 'metric'"
  v-model="form.trigger_rule"
/>

<AvailabilityRuleForm
  v-if="form.type === 'availability'"
  v-model="form.trigger_rule"
/>

<JobRuleForm
  v-if="form.type === 'job'"
  v-model="form.trigger_rule"
/>

<EventRuleForm
  v-if="form.type === 'event'"
  v-model="form.trigger_rule"
/>

<SystemRuleForm
  v-if="form.type === 'system'"
  v-model="form.trigger_rule"
/>
25.2 根据 resource_type 加载 metrics
watch(
  () => form.resource_type,
  async (resourceType) => {
    if (!resourceType) return

    metrics.value = await getMetricsByResourceType(resourceType)
  }
)
26. Active Alerts 页面
26.1 列表字段
字段	说明
Severity	告警等级
Title	告警标题
Type	告警类型
Resource	资源
Status	状态
First Triggered At	首次触发时间
Last Triggered At	最近触发时间
Actions	操作
26.2 操作
Acknowledge
Resolve
View Detail
27. Alert History 页面
27.1 列表字段
字段	说明
Severity	告警等级
Title	告警标题
Type	告警类型
Resource	资源
Status	状态
First Triggered At	首次触发时间
Resolved At	恢复时间
Duration	持续时间
27.2 筛选条件
Severity
Type
Status
Resource Type
Time Range
28. Notification Channels 页面
28.1 列表字段
字段	说明
Name	渠道名称
Type	渠道类型
Enabled	是否启用
Created At	创建时间
Actions	操作
28.2 操作
Create
Edit
Delete
Enable / Disable
Test
29. 默认告警模板

系统初始化时建议预置以下策略模板，但默认可以 disabled。

Name	Type	Severity
High CPU Usage	metric	warning
High Memory Usage	metric	warning
Low Disk Space	metric	critical
Repository Capacity Usage High	metric	critical
Sync Proxy Offline	availability	critical
Agent Proxy Offline	availability	critical
Gateway Offline	availability	critical
Backup Job Failed	job	critical
Restore Job Failed	job	critical
License Near Expiration	event	warning
License Expired	event	critical
Celery Worker Down	system	critical
30. 一期不实现内容

以下能力一期不做，但数据结构应尽量预留扩展空间：

Notification Policy
Escalation
Suppression
Maintenance Window
Alert Grouping
Alert Dependency
AI Root Cause Analysis
复杂告警降噪
复杂权限控制
多租户隔离策略
31. 实现优先级

推荐开发顺序：

1. notification_channels
2. alert_policies
3. alert_records
4. notification_logs
5. Metric Alert Evaluation
6. Availability Alert Evaluation
7. Job Alert Event Handler
8. Event Alert Handler
9. System Alert Evaluation
10. 前端页面联调
32. 最终验收标准

一期完成后，需要满足：

可以创建 5 类告警策略
可以启用 / 禁用告警策略
可以配置 Trigger Rule
可以配置 Recovery Rule
可以绑定 Notification Channel
可以触发告警
可以查看 Active Alerts
可以查看 Alert History
可以手动 Acknowledge
可以手动 Resolve
Metric Alert 可以自动恢复
Availability Alert 可以自动恢复
Job Alert 可以在下一次任务成功后自动恢复
通知发送成功或失败有日志记录
```
