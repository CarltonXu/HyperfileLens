# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)

**English** | [中文](README.zh-CN.md)

HyperFileLens is an AI-powered file intelligence platform for backup and archive data. It transforms your backup data into accessible, analyzable, and actionable knowledge assets.

## Overview

HyperFileLens goes beyond traditional backup solutions by providing:

- **Reliable Backup & Recovery**: Stable file-level backup capabilities for local filesystems, NAS, and NFS
- **AI-Powered Insights**: Query, analyze, and understand your backup data using natural language
- **Centralized Management**: Web-based control plane for policies, schedules, and monitoring
- **Scalable Architecture**: Proxy-based architecture supporting cloud and hybrid deployments

## Features

### Phase 1: Backup & Recovery Foundation

- **Multiple Data Sources**
  - Windows/Linux local directories
  - NFS shared directories
  - NAS file volumes
  
- **Backup Targets**
  - Local filesystem
  - NFS shares
  - Object storage (S3-compatible)
  - Azure Blob Storage
  - Google Cloud Storage

- **Recovery Options**
  - Original location recovery
  - New location recovery
  - Point-in-time recovery

### Phase 2: AI File Intelligence

- **Natural Language Queries**: Ask questions about your backup data
- **Content Analysis**: Extract and analyze document content
- **Sensitive Data Detection**: Identify PII, credentials, and sensitive information
- **Change Detection**: Track file changes over time
- **Smart Summarization**: Generate summaries of backup contents

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HyperFileLens Control                     │
│─────────────────────────────────────────────────────────────│
│ - Unified Management & Task Orchestration                  │
│ - Policy Configuration                                       │
│ - Node Management                                           │
│ - Task Dispatching                                          │
│ - Status Monitoring & Audit                                 │
│ - AI Query Orchestration                                    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
              WebSocket (Control Flow Only)
                              │
┌─────────────────────────────┼─────────────────────────────┐
│                             │                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  │  Source Proxy    │   │  NAS/File Proxy  │   │  Other Proxies   │
│  │  ────────────────│   │  ────────────────│   │  ────────────────│
│  │  Local Filesystem│   │  NAS/NFS Access  │   │  Other Sources   │
│  │  File Scanning   │   │  File Scanning   │   │  File Scanning   │
│  │  Backup Tasks    │   │  Backup Tasks    │   │  Backup Tasks    │
│  │  Recovery Tasks  │   │  Recovery Tasks  │   │  Recovery Tasks  │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘
│                             │
└─────────────────────────────┼─────────────────────────────┘
                              │
                   Direct Data Flow
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Target Gateway                            │
│─────────────────────────────────────────────────────────────│
│ - Receive Source Data Streams                               │
│ - Connect to Backup Repository                              │
│ - Manage Backup Data Writing                                 │
│ - Manage Recovery Data Output                               │
│ - AI Data Access Entry                                      │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         ▼                                         ▼
┌──────────────────┐                   ┌──────────────────┐
│  Backup Archive  │                   │  Recovery Target │
│  ────────────────│                   │  ────────────────│
│  Object Storage  │                   │  Original Path   │
│  Local Filesystem│                   │  New NAS/NFS     │
│  Block Storage   │                   │  New Server      │
└──────────────────┘                   └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cloud AI Capabilities                     │
│─────────────────────────────────────────────────────────────│
│ - External Model API / Token Integration                     │
│ - File Parsing & Content Extraction                          │
│ - OCR / Textualization                                       │
│ - AI Query & Analysis                                        │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend

- **Framework**: Django 5.x with Django REST Framework
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **WebSocket**: Django Channels

### Frontend

- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **State Management**: Pinia
- **Styling**: Tailwind CSS
- **Components**: Headless UI
- **Internationalization**: vue-i18n

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Clone the Repository

```bash
git clone https://github.com/hyperbdr/hyperfilelens.git
cd hyperfilelens
```

### Development Environment

1. Copy the environment configuration:

```bash
cp env.sample .env.dev
```

2. Configure environment variables in `.env.dev`:

```env
POSTGRES_DB=hyperfilelens_dev
POSTGRES_USER=hyperfilelens_dev
POSTGRES_PASSWORD=hyperfilelens_dev
REDIS_PASSWORD=hyperfilelens_dev
SECRET_KEY=your-dev-secret-key
DEBUG=true
```

3. Start services:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

4. Access services:

| Service | URL |
|---------|-----|
| Web UI | http://localhost:8000 |
| API Docs | http://localhost:8000/swagger/ |
| Admin Panel | http://localhost:8000/admin/ |
| Celery Monitor | http://localhost:5555 |
| Frontend Dev | http://localhost:5173 |

### Production Deployment

1. Copy the environment configuration:

```bash
cp env.sample .env
```

2. Configure for production:

```env
POSTGRES_DB=hyperfilelens
POSTGRES_USER=hyperfilelens
POSTGRES_PASSWORD=strong-password-here
REDIS_PASSWORD=strong-password-here
SECRET_KEY=very-long-random-secret-key
DEBUG=false
ALLOWED_HOSTS=your-domain.com
```

3. Build and start:

```bash
docker-compose up -d --build
```

## Project Structure

```
hyperfilelens/
├── backend/                  # Django backend
│   ├── core/                # Project configuration
│   │   ├── settings.py     # Django settings
│   │   ├── urls.py         # URL routing
│   │   ├── celery.py       # Celery configuration
│   │   └── wsgi.py         # WSGI application
│   ├── accounts/            # User management
│   ├── nodes/               # Proxy node management
│   ├── backup_tasks/        # Backup operations
│   ├── recovery_tasks/      # Recovery operations
│   ├── repository/          # Repository management
│   ├── policies/            # Backup policies
│   ├── ai_query/            # AI query processing
│   ├── audit_log/           # Audit logging
│   └── manage.py
├── frontend/                 # Vue.js frontend
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # Reusable components
│   │   ├── views/          # Page components
│   │   ├── stores/         # Pinia stores
│   │   ├── router/        # Vue Router config
│   │   ├── i18n/          # Internationalization
│   │   └── types/         # TypeScript types
│   └── package.json
├── docker/                  # Docker configuration
│   ├── nginx/              # Nginx configuration
│   └── entrypoint.sh       # Container entrypoint
├── scripts/                 # Utility scripts
├── Dockerfile              # Production Dockerfile
├── Dockerfile.dev         # Development Dockerfile
├── docker-compose.yml     # Production compose
├── docker-compose.dev.yml # Development compose
└── README.md
```

## API Documentation

Once the server is running, access the API documentation at:

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

### Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/nodes/` | Manage proxy nodes |
| `/api/v1/backup/tasks/` | Backup operations |
| `/api/v1/recovery/tasks/` | Recovery operations |
| `/api/v1/repository/` | Repository management |
| `/api/v1/policies/` | Policy management |
| `/api/v1/ai/queries/` | AI-powered queries |
| `/api/v1/audit/` | Audit logs |

## Configuration

### Backup Policies

Configure backup schedules and retention:

```python
{
    "name": "Daily Backup",
    "frequency": "daily",
    "schedule_time": "02:00:00",
    "backup_type": "incremental",
    "retention_days": 30,
    "retention_snapshots": 10,
    "compression_enabled": true
}
```

### Repository Configuration

#### Local Filesystem

```python
{
    "repo_type": "local",
    "path": "/data/backup"
}
```

#### S3-Compatible Storage

```python
{
    "repo_type": "s3",
    "path": "my-bucket",
    "config": {
        "endpoint": "https://s3.amazonaws.com",
        "region": "us-east-1",
        "credentials": {
            "access_key_id": "...",
            "secret_access_key": "..."
        }
    }
}
```

## Development

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Frontend

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm run dev

# Build for production
pnpm run build
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
pnpm run test
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [docs.hyperfilelens.io](https://docs.hyperfilelens.io)
- **Issues**: [GitHub Issues](https://github.com/hyperbdr/hyperfilelens/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hyperbdr/hyperfilelens/discussions)

## Roadmap

### Phase 1 (Current)
- [x] Project structure setup
- [x] Backend core modules
- [x] Frontend core UI
- [ ] Node proxy implementation
- [ ] Backup task execution
- [ ] Recovery operations

### Phase 2
- [ ] AI query integration
- [ ] Document parsing (PDF, Office)
- [ ] OCR capabilities
- [ ] Natural language search

### Phase 3
- [ ] Multi-tenant support
- [ ] Advanced analytics
- [ ] Anomaly detection
- [ ] Compliance reporting

---

Built with ❤️ by the HyperBDR Team
