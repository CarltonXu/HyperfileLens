# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)
[![Go](https://img.shields.io/badge/Go-1.21+-green.svg)](https://golang.org/)

**English** | [中文](README.zh-CN.md)

HyperFileLens is an AI-powered file intelligence platform for backup and archive data. It transforms your backup data into accessible, analyzable, and actionable knowledge assets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HyperFileLens MVP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Frontend  │  │   Control   │  │   Gateway   │  │    Proxy    │         │
│  │   (Vue3)    │  │  (Django)   │  │  (FastAPI)  │  │    (Go)     │         │
│  │             │  │             │  │             │  │             │         │
│  │ • Dashboard │  │ • 用户管理   │  │ • Kopia     │  │ • Kopia CLI │         │
│  │ • 节点管理   │  │ • 节点管理   │  │   Mount     │  │ • 跨平台    │         │
│  │ • 备份任务   │  │ • 任务调度   │  │ • 文件索引   │  │ • 执行备份   │         │
│  │ • 恢复任务   │  │ • WebSocket │  │ • AI 查询   │  │ • 执行恢复   │         │
│  │ • AI 查询   │  │ • REST API  │  │             │  │             │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│         ┌─────────────────────────┴─────────────────────────┐               │
│         │                                                     │               │
│  ┌──────┴──────┐                                    ┌────────┴────────┐      │
│  │ PostgreSQL  │                                    │      Redis      │      │
│  │   Database  │                                    │     Broker      │      │
│  └─────────────┘                                    └─────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Control Plane (Django)
- **Port**: 8000
- **Functions**: 用户管理、节点管理、任务调度、WebSocket 通信、REST API
- **Tech**: Django 5.x + Django REST Framework + Django Channels + Celery

### Gateway (FastAPI)
- **Port**: 8001
- **Functions**: Kopia 仓库挂载、文件索引、AI 查询
- **Tech**: FastAPI + uvicorn

### Proxy (Go)
- **Functions**: 接收控制端指令、执行 Kopia CLI 备份/恢复操作
- **Tech**: Go 1.21+ + gorilla/websocket
- **Platforms**: Windows, Linux, macOS

### Frontend (Vue3)
- **Port**: 5000
- **Functions**: Dashboard、节点管理、备份任务、恢复任务、AI 查询
- **Tech**: Vue 3 + Vite + Pinia + Tailwind CSS + Headless UI

## Tech Stack

| Component | Technology |
|-----------|------------|
| Control | Django 5.x, Django REST Framework, Celery, Django Channels |
| Gateway | FastAPI, uvicorn |
| Proxy | Go 1.21+, gorilla/websocket |
| Frontend | Vue 3, Vite, Pinia, Tailwind CSS, Headless UI |
| Database | PostgreSQL 15+ |
| Cache/Broker | Redis 7+ |
| Backup Engine | Kopia |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Go 1.21+ (for Proxy development)
- Node.js 20+ & pnpm (for Frontend development)
- Python 3.11+ (for Control & Gateway development)

### Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/hyperbdr/hyperfilelens.git
cd hyperfilelens

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5000
# Control API: http://localhost:8000/api/v1/
# Gateway API: http://localhost:8001/
```

### Development Mode

```bash
# Start development environment
./scripts/start-dev.sh

# Stop all services
./scripts/stop.sh
```

### Manual Start

```bash
# 1. Start Backend (Control)
cd backend
pip install -r requirements.txt
USE_POSTGRES=false python manage.py migrate
USE_POSTGRES=false python manage.py runserver 0.0.0.0:8000

# 2. Start Frontend
cd frontend
pnpm install
pnpm build
node server.cjs

# 3. Start Gateway
cd gateway
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 4. Start Proxy
cd proxy
go run main.go
```

## Default Credentials

- **Email**: admin@hyperfilelens.com
- **Password**: admin123

## Features

### Phase 1: Backup & Recovery Foundation

- **Source Resources**: NAS, NFS, CIFS, S3, Local Filesystem
- **Backup Targets**: S3, Azure, GCS, NFS, Local Filesystem
- **Recovery Options**: Original location, New location, Point-in-time

### Phase 2: AI File Intelligence

- **Natural Language Queries**: Ask questions about your backup data
- **Content Analysis**: Extract and analyze document content
- **Smart Search**: Search files across all backups

## Project Structure

```
hyperfilelens/
├── backend/              # Django Control Plane
│   ├── accounts/         # User management
│   ├── nodes/            # Node management & WebSocket
│   ├── backup_tasks/     # Backup operations
│   ├── recovery_tasks/   # Recovery operations
│   ├── source_resources/ # Source resources management
│   ├── repository/       # Backup repository management
│   ├── policies/         # Backup policy scheduling
│   ├── ai_query/         # AI-powered queries
│   └── audit_log/        # Audit logging
├── gateway/              # FastAPI Gateway
│   └── app/
│       ├── main.py       # FastAPI application
│       ├── mount.py      # Kopia mount operations
│       ├── indexer.py    # File indexing
│       └── ai.py         # AI query handler
├── proxy/                # Go Proxy
│   ├── main.go           # Proxy entry point
│   └── build.sh          # Build script
├── frontend/             # Vue3 Frontend
│   └── src/
│       ├── views/        # Page components
│       ├── stores/       # Pinia stores
│       ├── api/          # API client
│       └── i18n/         # Internationalization
├── docker-compose.yml    # Docker Compose config
└── scripts/              # Utility scripts
```

## API Endpoints

### Control Plane (Port 8000)

| Endpoint | Description |
|----------|-------------|
| `/api/v1/accounts/` | User management |
| `/api/v1/nodes/` | Node management |
| `/api/v1/source-resources/` | Source resources |
| `/api/v1/repository/repositories/` | Backup repositories |
| `/api/v1/backup-tasks/` | Backup tasks |
| `/api/v1/recovery-tasks/` | Recovery tasks |
| `/ws/node/{node_id}/` | WebSocket for Proxy |

### Gateway (Port 8001)

| Endpoint | Description |
|----------|-------------|
| `/files` | List mounted files |
| `/snapshots` | List snapshots |
| `/ai/query` | AI-powered query |

## License

Apache 2.0 License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.
