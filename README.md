# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)
[![Go](https://img.shields.io/badge/Go-1.21+-green.svg)](https://go.dev/)

**English** | [中文](README.zh-CN.md)

HyperFileLens is an AI-powered data protection and file intelligence platform for backup and archive data. It uses Kopia for snapshot-based backup and recovery, and adds platform-managed indexing, smart search, recovery exports, and Gateway-based AI insights.

## Architecture

```text
┌────────────────────────────── HyperFileLens Control Plane ──────────────────────────────┐
│                                                                                          │
│  Frontend (Vue 3) ───── HTTP ───── Backend (Django + DRF + Channels + Celery)             │
│                                            │                                             │
│                                            ├── PostgreSQL                                │
│                                            ├── Redis / Channel Layer / Celery Broker      │
│                                            └── Platform configuration and audit records   │
│                                                                                          │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ WebSocket
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
             Proxy Agent              Sync Proxy Agent            Gateway Agent
              (Go)                         (Go)                    (Python)
       local filesystem backup       NAS/NFS/SMB collection   snapshot indexing and AI
                    │                        │                        │
                    └────────────── Kopia snapshots / repositories ───┘
```

### Main components

| Component | Runtime | Role |
| --- | --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS | Web console for backup, recovery, exports, settings, and AI insights |
| Backend Control Plane | Django 5, DRF, Channels, Celery | REST API, WebSocket orchestration, scheduling, audit, policy, persistence |
| Proxy Agent | Go 1.21+, Kopia CLI | Executes backup and recovery tasks on source or collector nodes |
| Gateway Agent | Python 3.11+, Kopia CLI | Indexes snapshots and runs AI summary/search tasks near repository data |
| Database | PostgreSQL 15+ | Persistent metadata |
| Broker / Realtime | Redis 7+ | Celery broker/cache and Django Channels layer |
| Backup engine | Kopia | Snapshot creation, repository access, restore/export operations |

## Current capabilities

- Backup tasks for local filesystem, NAS/NFS/SMB collection through Sync Proxy, and S3-compatible repositories.
- Snapshot listing, browsing, sync, retention alignment, no-change snapshot visualization, timeline/grid views.
- Recovery tasks with selected-path restore.
- Recovery Exports for packaging selected snapshot files and downloading/share links.
- Gateway-based snapshot indexing, smart search, file category insights, large file analysis, duplicate candidates, cold data, growth trend, and AI summary.
- Platform-side AI Provider configuration under `Settings -> AI Insights`; the API key is stored encrypted and sent to Gateway only when an AI task is dispatched.
- Multi-tenant foundation, license/quota checks, audit logs, alerts, and system settings.

## Quick deployment with Docker Compose

### 1. Prerequisites

- Linux host with Docker and Docker Compose plugin.
- Open inbound ports for the console and API, by default:
  - Frontend: `5001`
  - Backend API/WebSocket: `8000`

### 2. Configure environment

```bash
git clone <your-repository-url> HyperFileLens
cd HyperFileLens
cp env.sample .env
```

Edit `.env` for your host:

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=false
ALLOWED_HOSTS=10.147.18.11,localhost,127.0.0.1,control
CSRF_TRUSTED_ORIGINS=http://10.147.18.11:5001,http://10.147.18.11:8000
CORS_ALLOWED_ORIGINS=http://10.147.18.11:5001,http://10.147.18.11:8000
POSTGRES_PASSWORD=replace-with-a-strong-password
BACKEND_PORT=8000
FRONTEND_PORT=5001
```

### 3. Start the platform

```bash
docker compose up -d --build
```

The default compose stack starts:

- PostgreSQL
- Redis
- Backend Control Plane with Daphne ASGI server
- Celery worker
- Celery beat
- Frontend static server with `/api/*` proxying to the backend

Create an administrator:

```bash
docker compose exec control python manage.py createsuperuser
```

Access:

```text
Frontend: http://<host-ip>:5001
Backend API: http://<host-ip>:8000/api/v1/
API docs: http://<host-ip>:8000/api/docs/
```

### 4. Common operations

```bash
docker compose ps
docker compose logs -f control
docker compose logs -f celery-worker
docker compose restart control
docker compose down
```

## Optional agents

Agents normally run on separate machines: Proxy on source/collector nodes, Gateway on index/AI nodes. The compose file also provides optional local profiles for lab deployments.

### Gateway Agent

Use this when the control-plane host should also run a Gateway Agent.

1. Create a Gateway in the web UI.
2. Copy the generated `gateway_id` and install token into `.env`:

```env
GATEWAY_SERVER_URL=http://control:8000
GATEWAY_WS_PROTOCOL=ws
GATEWAY_ID=<gateway-id>
GATEWAY_INSTALL_TOKEN=<install-token>
GATEWAY_NAME=gateway-01
```

3. Start it:

```bash
docker compose --profile gateway up -d --build gateway-agent
```

For a remote Gateway host, install Python 3, Kopia, and run:

```bash
cd gateway/agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

SERVER_URL=http://<control-plane-ip>:8000 \
GATEWAY_ID=<gateway-id> \
INSTALL_TOKEN=<install-token> \
GATEWAY_NAME=gateway-01 \
KOPIA_PATH=/usr/bin/kopia \
python client.py
```

### Proxy Agent / Sync Proxy

Use Proxy Agent on source servers for local filesystem backup. Use Sync Proxy on collector nodes for NAS/NFS/SMB collection.

```bash
cd proxy
go build -o hyperfilelens-proxy .
```

Example `config.yaml`:

```yaml
version: "1.0.0"
role: "agent" # or "sync"

server:
  url: "http://<control-plane-ip>:8000"
  api_token: "<proxy-api-token>"
  ws_protocol: "ws"

kopia:
  path: "kopia"
  cache_path: "/var/lib/hyperfilelens/cache"

storage:
  temp_directory: "/var/lib/hyperfilelens/tmp"
```

Run:

```bash
./hyperfilelens-proxy --config config.yaml
```

For a local lab Proxy in compose:

```env
PROXY_SERVER_URL=http://control:8000
PROXY_API_TOKEN=<proxy-api-token>
PROXY_ROLE=agent
PROXY_SOURCE_PATH=/data
```

```bash
docker compose --profile proxy up -d --build proxy-agent
```

## AI Provider configuration

AI model configuration is managed from the web UI:

```text
Settings -> AI Insights
```

Supported modes:

- Local fallback: rule-based summary, no external model required.
- OpenAI-compatible providers: OpenAI, OpenRouter, DeepSeek, LiteLLM, vLLM, internal model gateways.
- Advanced JSON: custom fields and `config.headers` for provider-specific request headers.

The control plane stores the API key encrypted. Gateway receives the provider configuration only for the task being executed.

## Development setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

Run workers:

```bash
celery -A core worker -l info
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev --host 0.0.0.0
```

### Proxy

```bash
cd proxy
go test ./...
go build -o hyperfilelens-proxy .
```

### Gateway Agent

```bash
cd gateway/agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python client.py
```

## Project layout

```text
HyperFileLens/
├── backend/                 # Django control plane
│   ├── backup_tasks/        # Backup task orchestration and snapshots
│   ├── recovery_tasks/      # Restore tasks and recovery exports
│   ├── repository/          # Kopia repository configuration
│   ├── source_resources/    # Local/NAS/S3 source definitions
│   ├── nodes/               # Proxy WebSocket and proxy management
│   ├── gateways/            # Gateway WebSocket and gateway management
│   ├── insights/            # Snapshot index and insight persistence
│   ├── ai_query/            # AI Insights APIs and AI Provider config
│   └── system_settings/     # Global settings, SMTP, AI Provider route alias
├── frontend/                # Vue 3 web console
├── proxy/                   # Go Proxy / Sync Proxy agent
├── gateway/
│   ├── agent/               # Python WebSocket Gateway Agent
│   └── app/                 # Legacy FastAPI gateway code kept for reference
├── docker-compose.yml       # Production/lab compose
├── docker-compose.dev.yml   # Development compose
└── env.sample               # Environment template
```

## Important endpoints

| Endpoint | Purpose |
| --- | --- |
| `/api/v1/accounts/` | Authentication and users |
| `/api/v1/proxies/` | Proxy management |
| `/api/v1/gateways/` | Gateway management |
| `/api/v1/source-resources/` | Source resources |
| `/api/v1/repositories/` | Backup repositories |
| `/api/v1/backup-tasks/` | Backup tasks, runs, snapshots |
| `/api/v1/recovery-tasks/` | Recovery tasks and exports |
| `/api/v1/insights/` | Snapshot index, search, insights, AI summary |
| `/api/v1/ai-insights/` | AI Insights dashboard and smart search |
| `/api/v1/system/` | System settings, SMTP, AI Provider config |
| `/ws/node/<proxy_id>/` | Proxy WebSocket |
| `/ws/gateway/<gateway_id>/` | Gateway WebSocket |

## Deployment notes

- Backend must run as ASGI (`daphne core.asgi:application`) because Proxy and Gateway use WebSocket connections.
- The default frontend server proxies `/api/*` and `/static/*` to the backend. In Docker, this proxy target is `control:8000`.
- Do not deploy the old FastAPI Gateway as the primary Gateway service. The current Gateway execution path is the Python WebSocket Gateway Agent.
- For production, put a reverse proxy such as Nginx or Traefik in front of frontend/backend and switch WebSocket URLs to `wss`.

## License

Apache 2.0 License. See [LICENSE](LICENSE).
