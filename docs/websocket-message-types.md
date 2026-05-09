# WebSocket 消息类型规范

## 概述

本文档定义了 HyperFileLens Proxy 和后端之间的 WebSocket 消息类型规范，确保双方消息格式的统一和一致性。

## 消息格式

所有 WebSocket 消息都遵循以下格式：

```json
{
  "type": "消息类型",
  "id": "消息ID（可选）",
  "payload": {
    // 消息内容
  }
}
```

## 消息分类

### 1. 控制消息

#### 1.1 后端 → Proxy

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `connection_established` | 连接建立确认 | - |
| `register_ack` | 注册确认 | `status`, `proxy_id` |
| `heartbeat_ack` | 心跳响应 | `server_time`, `pending_tasks` |
| `ping` | Ping 消息 | - |
| `error` | 错误消息 | `error` |

#### 1.2 Proxy → 后端

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `register` | 注册请求 | - |
| `heartbeat` | 心跳消息 | `metrics` |
| `pong` | Pong 响应 | - |

### 2. 任务命令（后端 → Proxy）

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `backup` | 执行备份任务 | `task_id`, `source_path`, `repository`, `password` |
| `restore` | 执行恢复任务 | `task_id`, `snapshot_id`, `target_path`, `repository`, `password`, `overwrite` |
| `mount` | 挂载任务 | `task_id`, `type`, `server`, `path`, `target`, `username`, `password` |
| `list_snapshots` | 列出快照 | `task_id`, `password` |
| `cancel` | 取消任务 | `task_id` |
| `test_storage` | 测试存储连接 | `task_id`, `storage_type`, `repository_id`, `test_write` |
| `init_repository` | 初始化仓库 | `task_id`, `repository_id`, `repository`, `password` |

### 3. 任务状态（Proxy → 后端）

#### 3.1 统一任务状态消息

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `task_start` | 任务开始 | `task_id`, `task_type`, `timestamp` |
| `task_progress` | 任务进度 | `task_id`, `progress`, `message`, `timestamp` |
| `task_complete` | 任务完成 | `task_id`, `task_type`, `success`, `result`, `error`, `timestamp` |

#### 3.2 特定结果消息（向后兼容）

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `test_storage_result` | 存储测试结果 | `task_id`, `success`, `result`, `error`, `timestamp` |
| `init_repository_result` | 仓库初始化结果 | `task_id`, `success`, `repository_id`, `error`, `timestamp` |
| `backup_result` | 备份结果 | `task_id`, `success`, `result`, `error` |
| `restore_result` | 恢复结果 | `task_id`, `success`, `result`, `error` |
| `mount_result` | 挂载结果 | `task_id`, `success`, `result`, `error` |
| `snapshot_list_result` | 快照列表结果 | `task_id`, `success`, `result`, `error` |

### 4. 系统消息（Proxy → 后端）

| 消息类型 | 说明 | Payload |
|---------|------|---------|
| `log` | 日志消息 | `level`, `message`, `context` |
| `status` | 状态报告 | `data` |

## 任务类型常量

- `backup` - 备份任务
- `restore` - 恢复任务
- `mount` - 挂载任务
- `list_snapshots` - 列出快照
- `test_storage` - 测试存储
- `init_repository` - 初始化仓库

## 任务状态常量

- `running` - 运行中
- `completed` - 已完成
- `failed` - 失败
- `cancelled` - 已取消

## 消息流程示例

### 1. 连接和注册流程

```
Proxy                           Backend
  |                               |
  |-- CONNECT -------------------->|
  |                               |
  |<--- connection_established ---|
  |                               |
  |-- register ------------------>|
  |                               |
  |<--- register_ack ------------>|
  |                               |
```

### 2. 心跳流程

```
Proxy                           Backend
  |                               |
  |-- heartbeat ----------------->|
  |                               |
  |<--- heartbeat_ack ----------->|
  | (包含 pending_tasks)          |
```

### 3. 任务执行流程

```
Proxy                           Backend
  |                               |
  |<--- backup ------------------>|
  |                               |
  |-- task_start ---------------->|
  |                               |
  |-- task_progress ------------->|
  | (进度更新)                    |
  |                               |
  |-- task_complete ------------>|
  | (包含结果)                    |
```

## 向后兼容性

为了保持向后兼容性，以下消息类型仍然支持：
- `task_update` - 遗留的任务更新消息
- `task_result` - 遗留的任务结果消息

新的实现应优先使用统一的消息格式（`task_start`、`task_progress`、`task_complete`）。

## 实现说明

### Proxy 端实现

- 使用 `task` 包中的消息类型常量
- 所有消息都使用 `payload` 字段传递数据
- 任务状态使用 `task_start`、`task_progress`、`task_complete` 统一格式

### 后端实现

- 同时支持统一消息格式和遗留格式
- 优先处理 `payload` 字段中的数据
- 为特定任务类型提供专门的处理方法

## 版本历史

- v1.0 - 初始版本，统一消息类型系统