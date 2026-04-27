# HyperFileLens Development Guide

## Project Overview

HyperFileLens is an AI-powered file intelligence platform for backup and archive data. This document provides development guidelines and architectural overview for contributors.

## Technology Stack

### Control Plane (Backend)
- Python 3.11+
- Django 5.x
- Django REST Framework
- Celery (task queue)
- Redis (broker/cache)
- PostgreSQL 15+
- Django Channels (WebSocket)
- Kopia (backup engine)

### Frontend
- Vue 3.4+
- TypeScript
- Vite
- Pinia (state management)
- Tailwind CSS
- Headless UI
- vue-i18n

### Gateway (AI + Index Service)
- Python 3.11+
- FastAPI
- Kopia mount + indexing
- AI query integration

### Proxy (Go-based Agent)
- Go 1.21+
- Kopia CLI integration
- WebSocket client
- Cross-platform support (Linux, Windows, macOS)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HyperFileLens                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Frontend  │    │   Control   │    │   Gateway   │     │
│  │   (Vue 3)   │───▶│  (Django)   │◀──▶│  (FastAPI)  │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                │
│                     ┌──────┴──────┐                         │
│                     │  WebSocket  │                         │
│                     └──────┬──────┘                         │
│                            │                                │
│         ┌──────────────────┼──────────────────┐            │
│         ▼                  ▼                  ▼            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Proxy 1   │    │   Proxy 2   │    │   Proxy N   │     │
│  │    (Go)     │    │    (Go)     │    │    (Go)     │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │            │
│         ▼                  ▼                  ▼            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Kopia     │    │   Kopia     │    │   Kopia     │     │
│  │  (Backup)   │    │  (Backup)   │    │  (Backup)   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
hyperfilelens/
├── backend/
│   ├── core/              # Django project configuration
│   ├── accounts/          # User authentication & management
│   ├── nodes/             # Proxy management & WebSocket
│   ├── backup_tasks/      # Backup operations
│   ├── recovery_tasks/    # Recovery operations
│   ├── repository/        # Storage repository management
│   ├── source_resources/  # Backup source resources (NAS/S3/etc)
│   ├── policies/          # Backup policy scheduling
│   ├── ai_query/          # AI-powered queries
│   ├── audit_log/         # Audit logging
│   └── services/          # Business services
│       └── kopia_service.py  # Kopia integration
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios API client
│   │   ├── components/   # Reusable UI components
│   │   ├── views/        # Page components
│   │   ├── stores/       # Pinia stores
│   │   ├── router/       # Vue Router config
│   │   ├── types/        # TypeScript type definitions
│   │   └── i18n/         # Internationalization
│   └── package.json
├── gateway/                # AI + Index service
│   ├── app/
│   │   ├── main.py       # FastAPI app
│   │   ├── mount.py      # Kopia mount
│   │   ├── indexer.py    # File indexing
│   │   └── ai.py         # AI query integration
│   └── requirements.txt
├── proxy/                  # Proxy agent (Go)
│   ├── main.go            # Entry point
│   ├── config/config.go   # Configuration management
│   ├── agent/client.go    # Proxy registration & heartbeat
│   ├── ws/client.go       # WebSocket client
│   ├── task/dispatcher.go # Task routing & execution
│   ├── kopia/client.go    # Kopia CLI wrapper
│   ├── mount/manager.go   # Mount operations (Sync only)
│   ├── monitor/metrics.go # System metrics
│   ├── utils/utils.go     # Utility functions
│   ├── install.sh         # Installation script
│   ├── build.sh           # Cross-platform build
│   └── config.example.yaml
└── docker/                 # Docker configurations
```

## Development Setup

### Prerequisites
- Python 3.11+
- Go 1.21+
- Node.js 20+
- pnpm
- Docker & Docker Compose

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
pnpm install

# Run dev server
pnpm run dev
```

### Gateway Setup
```bash
cd gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8001
```

### Proxy Setup
```bash
cd proxy

# Build locally
go build -o hyperfilelens-proxy .

# Run with config
./hyperfilelens-proxy --config config.yaml

# Or run with environment variables
SERVER_URL=http://localhost:8000 ./hyperfilelens-proxy
```

### Docker Development
```bash
# Copy environment file
cp env.sample .env.dev

# Start all services
docker-compose -f docker-compose.dev.yml up -d
```

## Proxy (Go Agent)

The Proxy is a Go-based agent that runs on source and target servers. It supports **two roles** in a single program:

### Core Principles

1. **Proxy 负责"执行"，不负责"决策"** - Control plane makes all decisions
2. **Proxy 不持久化业务数据** - No local business data storage (except cache)
3. **所有任务来自控制端** - Tasks are pushed via WebSocket
4. **所有数据写入通过 Kopia 完成** - Data operations via Kopia CLI

### Proxy Roles

#### 🟢 Agent Proxy (源端代理)
- **运行位置**: 业务服务器 (Windows / Linux / MacOS)
- **职责**:
  - 读取本地文件系统
  - 执行备份 (Kopia snapshot)
  - 上报状态
- **不负责**:
  - 挂载 NAS ❌
  - 管理 Repository ❌

#### 🔵 Sync Proxy (采集节点)
- **运行位置**: 独立节点 / 跳板机
- **职责**:
  - 挂载 NAS (NFS/SMB)
  - 接入对象存储 (S3 API, not mount)
  - 提供统一数据接入点
  - 执行备份任务

### Proxy Directory Structure

```
proxy/
├── main.go              # Entry point
├── config/
│   └── config.go        # Configuration management
├── agent/
│   └── client.go        # Proxy registration & heartbeat
├── ws/
│   └── client.go        # WebSocket client
├── task/
│   └── dispatcher.go    # Task routing & execution
├── kopia/
│   └── client.go        # Kopia CLI wrapper
├── mount/
│   └── manager.go       # Mount operations (Sync only)
├── monitor/
│   └── metrics.go       # System metrics
└── utils/
    └── utils.go         # Utility functions
```

### Proxy Configuration

Configuration can be provided via YAML file or environment variables:

```yaml
# config.yaml
version: "1.0.0"
role: "agent"  # "agent" or "sync"

server:
  url: "http://control:8000"
  api_token: "your-token"
  ws_protocol: "ws"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  name: "proxy-01"
  hostname: "backup-server-01"

kopia:
  path: "/usr/bin/kopia"
  cache_path: "/var/lib/hyperfilelens/cache"

mount:  # Sync Proxy only
  enabled: false
  nfs:
    server: "nas.example.com"
    path: "/data"
    target: "/mnt/nas"

logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
```

### Proxy Installation

```bash
# Install as Agent Proxy
curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash -s -- \
  --role agent \
  --server https://control.hyperfilelens.com \
  --token your-api-token

# Install as Sync Proxy
curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash -s -- \
  --role sync \
  --server https://control.hyperfilelens.com \
  --token your-api-token
```

### Proxy Commands

```bash
# Start proxy
./hyperfilelens-proxy --config /opt/hyperfilelens/config.yaml

# Start with environment variables
SERVER_URL=http://control:8000 API_TOKEN=xxx PROXY_ROLE=agent ./hyperfilelens-proxy

# Show version
./hyperfilelens-proxy --version
```

### Proxy Workflow

#### 1. Registration Flow
```
安装 → 注册 → 获取 proxy_id → 心跳
```

#### 2. Backup Task Flow
```
控制端创建任务
 ↓
通过 WS 下发
 ↓
Proxy 接收
 ↓
Connect Repo
 ↓
kopia snapshot
 ↓
上报结果
```

#### 3. NAS Scenario (Sync Proxy)
```
挂载 NAS
 ↓
kopia snapshot /mnt/nas
```

### Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| ✅ 一个程序，多角色 | Simplified deployment, single codebase |
| ✅ Agent 不挂载 NAS | Security, simplified source-side |
| ✅ NAS 由 Sync Proxy 挂载 | Centralized management |
| ✅ S3 不走 mount | Performance, use Kopia native S3 support |
| ✅ 默认 Direct 模式 | Agent → Repository directly |

## Coding Standards

### Backend (Python)
- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Write docstrings for all modules, classes, and public functions
- Use Django REST Framework conventions

### Frontend (TypeScript/Vue)
- Use Composition API with `<script setup>`
- Follow Vue 3 best practices
- Use TypeScript for type safety
- Component naming: PascalCase
- CSS: Use Tailwind CSS utility classes

### Proxy (Go)
- Follow Go standard formatting (gofmt)
- Use meaningful variable names
- Handle errors explicitly
- Write unit tests for core functions

### Git Commits
Follow Conventional Commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

Example: `feat(backup): add incremental backup support`

## API Design

### RESTful Conventions
- Use nouns for resources: `/api/v1/backup/tasks/`
- Use HTTP methods appropriately:
  - GET: Retrieve resources
  - POST: Create resources
  - PUT/PATCH: Update resources
  - DELETE: Remove resources
- Use pagination for list endpoints
- Return consistent error formats

### Response Format
```json
{
  "id": "uuid",
  "name": "resource-name",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Error Format
```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": {}
}
```

## Testing

### Backend Tests
```bash
cd backend
pytest                    # Run all tests
pytest path/to/test.py   # Run specific test file
```

### Frontend Tests
```bash
cd frontend
pnpm run test           # Unit tests
pnpm run test:e2e      # E2E tests
```

### Proxy Tests
```bash
cd proxy
go test ./...           # Run all tests
go test -v ./...        # Verbose output
```

## Database Migrations

```bash
# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate

# Create SQL script
python manage.py sqlmigrate app_name migration_name
```

## Celery Tasks

Tasks are defined in `tasks.py` within each app. Periodic tasks are registered in `periodic_tasks.py`.

```python
@shared_task
def my_task(param):
    # Task implementation
    pass
```

## WebSocket (Django Channels)

WebSocket consumers handle real-time communication with proxies:

- `nodes/consumers.py`: Proxy connection management
- `nodes/routing.py`: WebSocket URL routing

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `register` | Proxy → Control | Proxy registration |
| `heartbeat` | Proxy → Control | Periodic health check |
| `backup_task` | Control → Proxy | Backup task dispatch |
| `restore_task` | Control → Proxy | Restore task dispatch |
| `task_completed` | Proxy → Control | Task completion report |
| `task_failed` | Proxy → Control | Task failure report |
| `list_snapshots` | Control → Proxy | Request snapshot list |
| `mount` | Control → Proxy | Mount snapshot request |

## Docker Deployment

### Production Build
```bash
docker-compose up -d --build
```

### Development Build
```bash
docker-compose -f docker-compose.dev.yml up -d --build
```

## Environment Variables

### Control Plane
| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| REDIS_URL | Redis connection string | Yes |
| SECRET_KEY | Django secret key | Yes |
| DEBUG | Enable debug mode | No |
| ALLOWED_HOSTS | Allowed hostnames | Yes (prod) |

### Gateway
| Variable | Description | Required |
|----------|-------------|----------|
| KOPIA_MOUNT_PATH | Path for Kopia mounts | No |
| REPO_PATH | Default repository path | No |

### Proxy
| Variable | Description | Required |
|----------|-------------|----------|
| SERVER_URL | Control plane URL | Yes |
| API_TOKEN | Authentication token | Yes |
| PROXY_ROLE | Proxy role: "agent" or "sync" | No (default: agent) |
| PROXY_ID | Unique proxy identifier | No (auto-generated) |
| CONFIG_PATH | Path to config file | No |
| KOPIA_PATH | Path to Kopia binary | No |

## Common Issues

### Database Connection
Ensure PostgreSQL is running and credentials are correct in `.env`.

### Celery Not Processing Tasks
- Check Redis is running
- Verify Celery worker is started
- Check task registration

### Frontend Build Fails
- Clear node_modules: `rm -rf node_modules`
- Reinstall: `pnpm install`

### Proxy Connection Issues
- Check control plane URL is correct
- Verify API token is valid
- Check network connectivity
- Review proxy logs: `journalctl -u hyperfilelens-proxy -f`

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Vue 3 Documentation](https://vuejs.org/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Go Documentation](https://golang.org/doc/)
- [Kopia Documentation](https://kopia.io/docs/)
