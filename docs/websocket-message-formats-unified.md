# WebSocket 消息格式规范（统一版本）

## 统一的消息格式

所有 WebSocket 消息都遵循以下统一格式：

```json
{
  "type": "消息类型",
  "id": "消息ID（UUID）",
  "timestamp": "ISO 8601 时间戳",
  "payload": {
    // 消息内容
  }
}
```

## 消息格式说明

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|-----|------|-----|------|
| `type` | string | 是 | 消息类型，定义消息的用途 |
| `id` | string | 是 | 消息的唯一标识符（UUID），用于消息追踪和关联 |
| `timestamp` | string | 是 | 消息创建时间，ISO 8601 格式 |
| `payload` | object | 是 | 消息的具体内容，根据 `type` 不同而不同 |

### 注意事项

- 所有消息都必须包含 `payload` 字段，即使 payload 为空也应设为 `{}`
- 控制消息（如 `heartbeat_ack`）也应有 ID 和 timestamp，用于调试和追踪
- 任务消息的 ID 用于关联请求和响应
- Timestamp 字段用于消息排序和超时检测

## 消息分类

### 1. 控制消息

#### 1.1 后端 → Proxy

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `connection_established` | `{ "proxy_id": "..." }` | 连接建立确认 |
| `register_ack` | `{ "status": "success", "proxy_id": "..." }` | 注册确认 |
| `heartbeat_ack` | `{ "server_time": "...", "pending_tasks": [...] }` | 心跳响应 |
| `ping` | `{}` | Ping 消息 |
| `pong` | `{}` | Pong 响应 |
| `error` | `{ "message": "..." }` | 错误消息 |

#### 1.2 Proxy → 后端

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `register` | `{}` | 注册请求 |
| `heartbeat` | `{ "metrics": {...} }` | 心跳消息 |

### 2. 任务命令（后端 → Proxy）

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `backup` | `{ "task_id": "...", "source_path": "...", "repository": {...}, "password": "..." }` | 执行备份任务 |
| `restore` | `{ "task_id": "...", "snapshot_id": "...", "target_path": "...", ... }` | 执行恢复任务 |
| `mount` | `{ "task_id": "...", "type": "nfs/smb", "server": "...", ... }` | 挂载任务 |
| `list_snapshots` | `{ "task_id": "...", "password": "..." }` | 列出快照 |
| `cancel` | `{ "task_id": "..." }` | 取消任务 |
| `test_storage` | `{ "task_id": "...", "repository_id": "...", "storage_type": "nas/s3/local", ... }` | 测试存储连接 |
| `init_repository` | `{ "task_id": "...", "repository_id": "...", "repository": {...}, "password": "..." }` | 初始化仓库 |

### 3. 任务状态（Proxy → 后端）

#### 3.1 统一任务状态消息

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `task_start` | `{ "task_id": "...", "task_type": "...", "timestamp": "..." }` | 任务开始 |
| `task_progress` | `{ "task_id": "...", "progress": 50, "message": "...", "timestamp": "..." }` | 任务进度 |
| `task_complete` | `{ "task_id": "...", "task_type": "...", "success": true/false, "result": {...}/"error": "...", "timestamp": "..." }` | 任务完成 |

#### 3.2 特定结果消息（向后兼容）

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `test_storage_result` | `{ "task_id": "...", "success": true/false, "result": {...}/"error": "...", "timestamp": "..." }` | 存储测试结果 |
| `init_repository_result` | `{ "task_id": "...", "success": true/false, "repository_id": "..."/"error": "...", "timestamp": "..." }` | 仓库初始化结果 |

### 4. 系统消息（Proxy → 后端）

| 消息类型 | Payload 内容 | 说明 |
|---------|-------------|------|
| `log` | `{ "level": "info/warn/error", "message": "...", "context": {...} }` | 日志消息 |
| `status` | `{ "data": {...} }` | 状态报告 |

## 消息格式示例

### 控制消息示例

**连接建立确认：**
```json
{
  "type": "connection_established",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-05-09T01:15:28.123Z",
  "payload": {
    "proxy_id": "13713458-bf95-4933-9984-c730304c6e74"
  }
}
```

**心跳响应：**
```json
{
  "type": "heartbeat_ack",
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2026-05-09T01:15:28.456Z",
  "payload": {
    "server_time": "2026-05-09T01:15:28.456Z",
    "pending_tasks": []
  }
}
```

### 任务命令示例

**存储测试命令：**
```json
{
  "type": "test_storage",
  "id": "fc6b31a0-5ecf-416f-9dc1-bc7efe2e7338",
  "timestamp": "2026-05-09T01:15:28.123Z",
  "payload": {
    "task_id": "5d3a72ef-a299-4da1-bcd3-387b6579213f",
    "repository_id": "19a6abed-661e-4b94-a560-e27042132de5",
    "storage_type": "nas",
    "test_write": true,
    "server": "10.68.1.100",
    "mount_type": "nfs",
    "mount_path": "/mnt/nfs"
  }
}
```

### 任务状态示例

**任务完成：**
```json
{
  "type": "task_complete",
  "id": "fc6b31a0-5ecf-416f-9dc1-bc7efe2e7338",
  "timestamp": "2026-05-09T01:15:29.789Z",
  "payload": {
    "task_id": "5d3a72ef-a299-4da1-bcd3-387b6579213f",
    "task_type": "test_storage",
    "success": true,
    "result": {
      "storage_type": "nas",
      "connectivity": {
        "reachable": true,
        "response_time": "5ms"
      }
    }
  }
}
```

## 实现说明

### 后端实现

- 所有发送的消息都必须包含 `type`、`id`、`timestamp`、`payload` 字段
- 使用 `uuid.uuid4()` 生成消息 ID
- 使用 `timezone.now().isoformat()` 生成时间戳

### Proxy 端实现

- 所有发送的消息都必须包含 `type`、`id`、`timestamp`、`payload` 字段
- 使用 `uuid.New()` 生成消息 ID
- 使用 `time.Now()` 生成时间戳
- 所有接收的消息都从 `msg.Payload` 中获取数据

## 版本历史

- v2.0 - 统一所有消息格式，要求所有消息包含 `payload` 字段
- v1.0 - 初始版本，部分消息缺少 `payload` 字段