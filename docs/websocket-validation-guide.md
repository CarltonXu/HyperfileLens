# WebSocket 消息验证指南

## 概述

WebSocket 消息验证模块确保从 Proxy 发送到后端的消息格式正确、数据有效，提高系统可靠性和安全性。

## 使用方法

### 基本使用

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
            'memory_usage': 60.0,
            'disk_usage': 45.0
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

### 在 Consumer 中使用

```python
from channels.generic.websocket import AsyncWebsocketConsumer
from core.websocket_validation import validate_and_log
import json

class ProxyConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        """接收并验证 WebSocket 消息"""
        try:
            data = json.loads(text_data)
            
            # 验证消息
            is_valid, validation_result = validate_and_log(
                data, 
                logger=self.logger
            )
            
            if not is_valid:
                # 发送验证错误
                await self.send_error(
                    message=f"Invalid message format: {validation_result.to_dict()}",
                    code='validation_error'
                )
                return
            
            # 根据消息类型路由
            await self.route_message(data)
            
        except json.JSONDecodeError as e:
            await self.send_error(
                message=f"Invalid JSON: {str(e)}",
                code='json_decode_error'
            )
```

## 支持的消息类型

### 1. Heartbeat (心跳消息)

```python
message = {
    'type': 'heartbeat',
    'id': 'msg-123',
    'payload': {
        'node_id': 'node-abc',
        'status': 'online',  # or 'offline'
        'metrics': {
            'cpu_usage': 75.5,      # 0-100
            'memory_usage': 60.0,   # 0-100
            'disk_usage': 45.0,      # 0-100
            'network_bytes_sent': 1024000,
            'network_bytes_recv': 2048000
        }
    }
}
```

### 2. Task Start (任务开始)

```python
message = {
    'type': 'task_start',
    'id': 'msg-123',
    'payload': {
        'task_id': 'task-abc-123',
        'task_type': 'backup',  # backup, restore, mount, list_snapshots
        'timestamp': '2026-05-09T12:34:56Z'
    }
}
```

### 3. Task Progress (任务进度)

```python
message = {
    'type': 'task_progress',
    'id': 'msg-123',
    'payload': {
        'task_id': 'task-abc-123',
        'task_type': 'backup',
        'status': 'running',
        'progress': 50,  # 0-100
        'message': 'Processing file 50/100',
        'current_file': '/data/file50.dat',
        'total_files': 100,
        'processed_files': 50,
        'total_bytes': 1048576000,
        'processed_bytes': 524288000,
        'speed_mbps': 10.5,
        'eta': '00:05:30',
        'timestamp': '2026-05-09T12:34:56Z'
    }
}
```

### 4. Task Complete (任务完成)

```python
message = {
    'type': 'task_complete',
    'id': 'msg-123',
    'payload': {
        'task_id': 'task-abc-123',
        'success': True,
        'result': {
            'snapshot_id': 'snap-123',
            'files_count': 100
        },
        'timestamp': '2026-05-09T12:34:56Z'
    }
}
```

### 5. Error (错误消息)

```python
message = {
    'type': 'error',
    'id': 'msg-123',
    'payload': {
        'error': 'Connection timeout',
        'task_id': 'task-abc-123',
        'timestamp': '2026-05-09T12:34:56Z'
    }
}
```

## 验证规则

### 必需字段

所有消息必须包含：
- `type`: 消息类型
- `payload`: 消息内容（字典）

可选字段：
- `id`: 消息唯一标识符

### 数据类型验证

- `type`: 必须是字符串
- `payload`: 必须是字典
- `id`: 必须是字符串（如果存在）

### 值范围验证

- CPU 使用率: 0-100
- 内存使用率: 0-100
- 磁盘使用率: 0-100
- 任务进度: 0-100
- 文件计数: 非负整数
- 字节计数: 非负整数
- 速度: 非负数

## 验证错误级别

### CRITICAL (严重)

消息无法被处理，例如：
- 消息不是字典
- 缺少必需字段（type, payload）
- 无效的消息类型

### ERROR (错误)

消息存在数据问题但可以部分处理，例如：
- 无效的任务类型
- 无效的状态值

### WARNING (警告)

消息数据可能不正确但可以继续处理，例如：
- 度量值超出范围
- 可选字段格式错误

### INFO (信息)

消息格式建议，例如：
- 空的消息 ID

## 验证结果

### ValidationResult 类

```python
class ValidationResult:
    def __init__(self, valid: bool, errors: List[ValidationError] = None)
    
    def add_error(
        field: str, 
        message: str, 
        severity: ValidationSeverity = ValidationSeverity.ERROR, 
        code: str = "invalid"
    )
    
    def get_errors_by_severity(severity: ValidationSeverity) -> List[ValidationError]
    
    def has_critical_errors() -> bool
    
    def to_dict() -> Dict[str, Any]
```

### 示例

```python
result = validate_websocket_message(message)

print(result.valid)  # True/False

# 获取所有错误
for error in result.errors:
    print(f"{error.field}: {error.message} ({error.severity})")

# 检查是否有严重错误
if result.has_critical_errors():
    print("Message has critical errors")

# 转换为字典
print(result.to_dict())

# 输出:
# {
#     "valid": False,
#     "errors": [
#         {
#             "field": "payload.metrics.cpu_usage",
#             "message": "cpu_usage must be between 0 and 100",
#             "severity": "warning",
#             "code": "out_of_range"
#         }
#     ]
# }
```

## 在 Django Consumers 中的集成

### 示例：添加验证到现有 Consumer

```python
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from core.websocket_validation import validate_and_log
from core.logging_config import get_logger

logger = get_logger(__name__)

class ProxyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """接受 WebSocket 连接"""
        self.proxy_id = self.scope['url_route']['kwargs']['proxy_id']
        self.logger = bind_logger(logger, proxy_id=self.proxy_id)
        
        # 验证代理是否存在
        proxy = await self.get_proxy()
        if not proxy:
            self.logger.warning("Proxy not found", extra={'proxy_id': self.proxy_id})
            await self.close(code=4000)
            return
        
        self.proxy = proxy
        await self.accept()
        self.logger.info("WebSocket connection established")

    async def receive(self, text_data):
        """接收并处理消息"""
        try:
            data = json.loads(text_data)
            
            # 验证消息
            is_valid, validation_result = validate_and_log(data, logger=self.logger)
            
            if not is_valid:
                await self.send_validation_error(validation_result)
                return
            
            # 处理消息
            await self.handle_message(data)
            
        except json.JSONDecodeError as e:
            await self.send_error(
                message=f"Invalid JSON: {str(e)}",
                code='json_decode_error'
            )
        except Exception as e:
            self.logger.exception("Error processing message", extra={'error': str(e)})
            await self.send_error(
                message=f"Internal error: {str(e)}",
                code='internal_error'
            )

    async def send_validation_error(self, result: ValidationResult):
        """发送验证错误"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'error': 'Message validation failed',
                'details': result.to_dict()
            }
        }))

    async def send_error(self, message: str, code: str):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'id': str(uuid.uuid4()),
            'timestamp': timezone.now().isoformat(),
            'payload': {
                'error': message,
                'code': code
            }
        }))

    async def handle_message(self, data):
        """根据消息类型路由到处理函数"""
        message_type = data.get('type')
        
        handlers = {
            'heartbeat': self.handle_heartbeat,
            'task_start': self.handle_task_start,
            'task_progress': self.handle_task_progress,
            'task_complete': self.handle_task_complete,
            'error': self.handle_error,
        }
        
        handler = handlers.get(message_type)
        if handler:
            await handler(data.get('payload', {}))
        else:
            self.logger.warning("Unknown message type", extra={'type': message_type})
```

## 测试

### 单元测试示例

```python
import pytest
from core.websocket_validation import validate_websocket_message

def test_valid_heartbeat_message():
    """测试有效的心跳消息"""
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
    assert result.valid
    assert len(result.errors) == 0

def test_invalid_cpu_usage():
    """测试无效的 CPU 使用率"""
    message = {
        'type': 'heartbeat',
        'payload': {
            'node_id': 'node-abc',
            'status': 'online',
            'metrics': {
                'cpu_usage': 150.0  # 超出范围
            }
        }
    }
    
    result = validate_websocket_message(message)
    assert not result.valid
    assert any('cpu_usage' in e.field for e in result.errors)

def test_missing_required_field():
    """测试缺少必需字段"""
    message = {
        'type': 'heartbeat'
        # 缺少 payload
    }
    
    result = validate_websocket_message(message)
    assert not result.valid
    assert result.has_critical_errors()
```

## 性能考虑

### 缓存验证结果

对于频繁发送的消息类型（如心跳），可以缓存验证模式：

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_message_schema(message_type: str) -> Dict[str, Any]:
    """获取消息 schema（带缓存）"""
    return MESSAGE_SCHEMAS.get(message_type)
```

### 异步验证

对于高负载场景，可以考虑异步验证：

```python
async def async_validate_message(message: Dict[str, Any]) -> ValidationResult:
    """异步验证消息"""
    # 将验证逻辑放到线程池
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, validate_websocket_message, message)
    return result
```

## 安全考虑

### 1. 输入清理

验证后仍然需要对数据进行清理：

```python
def sanitize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """清理消息中的潜在恶意内容"""
    sanitized = message.copy()
    
    # 限制字段数量
    if len(sanitized) > 100:
        raise ValueError("Too many fields")
    
    # 限制字符串长度
    for key, value in sanitized.items():
        if isinstance(value, str) and len(value) > 10000:
            sanitized[key] = value[:10000]
    
    return sanitized
```

### 2. 速率限制

对消息验证进行速率限制：

```python
from django.core.cache import cache

def check_rate_limit(proxy_id: str, max_requests: int = 1000) -> bool:
    """检查速率限制"""
    key = f"ws_rate_limit:{proxy_id}:{datetime.now().minute}"
    count = cache.get(key, 0)
    
    if count >= max_requests:
        return False
    
    cache.set(key, count + 1, 60)  # 60秒过期
    return True
```

### 3. 消息大小限制

```python
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB

async def receive(self, text_data):
    if len(text_data) > MAX_MESSAGE_SIZE:
        await self.close(code=4001)
        return
    
    # 处理消息...
```

## 故障排查

### 常见验证错误

#### 1. "Message type is required"

原因：消息缺少 `type` 字段

解决方案：
```python
message = {
    'type': 'heartbeat',  # 添加必需字段
    'payload': {...}
}
```

#### 2. "Unknown message type"

原因：使用了不支持的消息类型

解决方案：检查 MESSAGE_SCHEMAS 中定义的可用类型

#### 3. "Payload must be a dictionary"

原因：`payload` 字段不是字典

解决方案：
```python
# 错误
'payload': "invalid"

# 正确
'payload': {'key': 'value'}
```

#### 4. "cpu_usage must be between 0 and 100"

原因：指标值超出范围

解决方案：确保指标值在有效范围内

---

文档版本: 1.0
最后更新: 2026-05-09
