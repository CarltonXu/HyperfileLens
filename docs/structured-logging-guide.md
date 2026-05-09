# 结构化日志使用指南

## 概述

HyperFileLens 使用结构化日志系统，支持 JSON 格式输出，便于日志分析和调试。

## 配置

### 环境变量

```bash
# 日志格式：text 或 json（默认生产环境使用 json）
export LOG_FORMAT=json

# 日志级别：DEBUG, INFO, WARNING, ERROR
export LOG_LEVEL=INFO
```

### 设置文件

在 `backend/core/settings.py` 中配置：

```python
from .logging_config import setup_logging

# 配置结构化日志
LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')
LOG_LEVEL = os.getenv('LOG_LEVEL', None)

setup_logging(
    debug=DEBUG,
    log_level=LOG_LEVEL,
    log_format=LOG_FORMAT
)
```

## 使用示例

### 基本使用

```python
from core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("This is an info message")
logger.warning("This is a warning")
logger.error("This is an error")
```

### 添加上下文

```python
from core.logging_config import get_logger, bind_logger

logger = get_logger(__name__)
context_logger = bind_logger(logger, user_id="123", action="backup")

context_logger.info("Starting backup", extra={
    'source_path': '/data/backup',
    'repository_id': 'repo-123'
})
```

### 使用 RequestContext

```python
from core.logging_config import RequestContext, get_logger

logger = get_logger(__name__)

with RequestContext(request_id="req-123", user_id="user-456"):
    logger.info("Processing request", extra={'action': 'create_task'})
    # 所有日志将自动包含 request_id 和 user_id
```

### 异常日志

```python
try:
    # Some operation
    pass
except Exception as e:
    logger.exception("Operation failed", extra={
        'operation': 'backup',
        'error_type': type(e).__name__
    })
```

### Django 视图中的使用

```python
from django.http import JsonResponse
from core.logging_config import get_logger

logger = get_logger(__name__)

def backup_view(request):
    logger.info("Backup request received", extra={
        'user_id': str(request.user.id),
        'backup_type': 'full'
    })

    try:
        # Perform backup
        result = perform_backup()
        logger.info("Backup completed", extra={'backup_id': result.id})
        return JsonResponse({'status': 'success', 'backup_id': result.id})
    except Exception as e:
        logger.exception("Backup failed", extra={'error': str(e)})
        return JsonResponse({'status': 'error'}, status=500)
```

### WebSocket Consumer 中的使用

```python
from channels.generic import AsyncWebsocketConsumer
from core.logging_config import get_logger, RequestContext

logger = get_logger(__name__)

class BackupConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.proxy_id = self.scope['url_route']['kwargs'].get('proxy_id')

        with RequestContext(proxy_id=self.proxy_id):
            logger.info("WebSocket connection established", extra={
                'user_id': str(self.scope['user'].id)
            })

        await self.accept()

    async def receive(self, text_data):
        with RequestContext(proxy_id=self.proxy_id):
            logger.info("Received message", extra={'message_type': 'backup'})
            # Process message
```

## 日志格式

### JSON 格式（生产环境）

```json
{
  "timestamp": "2026-05-09T12:34:56.789Z",
  "level": "INFO",
  "logger": "nodes.consumers",
  "message": "Processing backup task",
  "module": "consumers",
  "function": "execute_backup",
  "line": 123,
  "process": 12345,
  "thread": 67890,
  "request_id": "req-abc-123",
  "user_id": "user-xyz-456",
  "tenant_id": "tenant-789",
  "task_id": "task-123",
  "proxy_id": "proxy-456",
  "extra": {
    "backup_type": "full",
    "source_path": "/data"
  }
}
```

### 文本格式（开发环境）

```
INFO 2026-05-09 12:34:56 consumers 12345 67890 Processing backup task
```

## 日志文件

### 日志位置

- `backend/logs/app.log` - 所有日志
- `backend/logs/error.log` - 仅错误日志

### 日志轮转

- 最大文件大小：10MB
- 保留文件数：5

## 查询日志

### 使用 grep 查询

```bash
# 查找所有错误日志
grep '"level": "ERROR"' backend/logs/app.log

# 查找特定请求的日志
grep '"request_id": "req-abc-123"' backend/logs/app.log

# 查找特定代理的日志
grep '"proxy_id": "proxy-456"' backend/logs/app.log

# 查找特定用户的日志
grep '"user_id": "user-xyz-456"' backend/logs/app.log
```

### 使用 jq 查询 JSON 日志

```bash
# 查找所有错误日志
cat backend/logs/app.log | jq 'select(.level == "ERROR")'

# 查找特定时间范围的日志
cat backend/logs/app.log | jq 'select(.timestamp | startswith("2026-05-09"))'

# 查找特定用户的日志
cat backend/logs/app.log | jq 'select(.user_id == "user-xyz-456")'

# 统计错误数量
cat backend/logs/app.log | jq -r 'select(.level == "ERROR") | .logger' | sort | uniq -c

# 查找慢请求
cat backend/logs/app.log | jq 'select(.extra.duration_ms > 1000)'
```

### 使用 Python 查询

```python
import json

with open('backend/logs/app.log', 'r') as f:
    for line in f:
        log = json.loads(line)
        if log.get('level') == 'ERROR':
            print(log.get('message'), log.get('extra'))
```

## 最佳实践

### 1. 使用适当的日志级别

- **DEBUG**: 详细的调试信息，仅在开发时使用
- **INFO**: 一般信息，如操作开始/完成
- **WARNING**: 警告信息，如资源使用高
- **ERROR**: 错误信息，如操作失败
- **CRITICAL**: 严重错误，需要立即处理

### 2. 添加结构化上下文

```python
# 好的做法
logger.info("Task completed", extra={
    'task_id': str(task.id),
    'task_type': task.task_type,
    'duration_ms': int(duration * 1000)
})

# 不好的做法
logger.info(f"Task {task.id} ({task.task_type}) completed in {duration}s")
```

### 3. 使用异常日志

```python
try:
    operation()
except Exception as e:
    # 好的做法 - 使用 logger.exception 自动包含堆栈跟踪
    logger.exception("Operation failed", extra={'operation': 'backup'})
    
    # 不好的做法 - 只记录错误消息
    logger.error(f"Operation failed: {e}")
```

### 4. 添加唯一标识符

```python
# 为每个请求、任务或操作添加唯一 ID
request_id = str(uuid.uuid4())
with RequestContext(request_id=request_id):
    # 所有日志将自动包含 request_id
    logger.info("Processing request")
```

### 5. 避免敏感信息

```python
# 好的做法 - 隐藏敏感信息
logger.info("User logged in", extra={
    'user_id': str(user.id),
    'ip_address': request.META['REMOTE_ADDR']
})

# 不好的做法 - 记录密码
logger.info(f"User logged in with password: {password}")
```

## 性能考虑

### 1. 延迟日志级别检查

```python
# 好的做法 - 延迟字符串格式化
logger.debug("Processing item %s", item_id)

# 不好的做法 - 总是格式化字符串
logger.debug(f"Processing item {item_id}")  # 即使是 INFO 级别也会执行
```

### 2. 避免过多的日志

```python
# 好的做法 - 使用采样或阈值
if counter % 100 == 0:  # 每100次记录一次
    logger.info("Progress update", extra={'counter': counter})

# 不好的做法 - 每次都记录
for i in range(10000):
    logger.info("Processing item", extra={'item_id': i})
```

## 监控和告警

### 1. 错误率监控

```bash
# 统计最近1小时的错误数量
tail -10000 backend/logs/app.log | \
  grep '"level": "ERROR"' | \
  jq -r '.timestamp' | \
  sort -u | \
  wc -l
```

### 2. 慢请求监控

```bash
# 查找慢请求
cat backend/logs/app.log | \
  jq 'select(.extra.duration_ms > 1000) | {path, method, duration_ms}'
```

### 3. 特定错误模式

```bash
# 查找数据库连接错误
grep '"DatabaseError"' backend/logs/error.log
```

## 集成

### ELK Stack (Elasticsearch, Logstash, Kibana)

```yaml
# logstash.conf
input {
  file {
    path => "/path/to/backend/logs/app.log"
    codec => json
  }
}

filter {
  # 添加字段或修改日志
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "hyperfilelens-%{+YYYY.MM.dd}"
  }
}
```

### Grafana Loki

```yaml
# promtail-config.yaml
scrape_configs:
  - job_name: hyperfilelens
    static_configs:
      - targets:
          - localhost
        labels:
          job: hyperfilelens
          __path__: /path/to/backend/logs/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            logger: logger
            message: message
      - labels:
          level:
          logger:
```

### Datadog

```python
# 在 settings.py 中
from ddtrace import patch_all

patch_all()  # 自动收集日志和指标
```

## 故障排查

### 问题：日志文件未创建

```bash
# 检查日志目录权限
ls -la backend/logs/

# 确保目录存在
mkdir -p backend/logs
chmod 755 backend/logs
```

### 问题：JSON 日志格式不正确

```bash
# 验证 JSON 格式
cat backend/logs/app.log | python -m json.tool 2>&1 | head -20
```

### 问题：日志级别未生效

```python
# 检查日志配置
import logging
print(logging.getLogger('hyperfilelens').level)
```

## 迁移指南

### 从旧的日志系统迁移

1. 更新 settings.py 使用新的日志配置
2. 添加中间件到 MIDDLEWARE 设置
3. 更新现有日志调用使用结构化格式
4. 测试日志输出格式
5. 更新日志查询脚本

### 示例迁移

```python
# 旧代码
import logging
logger = logging.getLogger(__name__)
logger.info(f"User {user.id} performed {action}")

# 新代码
from core.logging_config import get_logger
logger = get_logger(__name__)
logger.info("User performed action", extra={
    'user_id': str(user.id),
    'action': action
})
```

---

文档版本: 1.0
最后更新: 2026-05-09
