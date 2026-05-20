# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)
[![Go](https://img.shields.io/badge/Go-1.21+-green.svg)](https://go.dev/)

[English](README.md) | **中文**

HyperFileLens 是一个面向备份和归档数据的 AI 数据保护与文件智能平台。平台使用 Kopia 作为快照备份与恢复引擎，并在此基础上提供快照浏览、恢复导出、索引搜索、文件洞察和基于 Gateway 的 AI 分析能力。

## 架构

```text
┌──────────────────────────── HyperFileLens Control Plane ────────────────────────────┐
│                                                                                      │
│  Frontend (Vue 3) ─── HTTP ─── Backend (Django + DRF + Channels + Celery)             │
│                                      │                                               │
│                                      ├── PostgreSQL                                  │
│                                      ├── Redis / Channel Layer / Celery Broker        │
│                                      └── 平台配置、审计、任务和元数据                 │
│                                                                                      │
└──────────────────────────────────────┬───────────────────────────────────────────────┘
                                       │ WebSocket
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
           Proxy Agent            Sync Proxy Agent        Gateway Agent
             (Go)                      (Go)                 (Python)
      源端本地文件备份            NAS/NFS/SMB 采集       快照索引与 AI 分析
                 │                     │                     │
                 └──────────── Kopia snapshots / repositories ────────────┘
```

### 核心组件

| 组件 | 运行时 | 职责 |
| --- | --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS | Web 控制台，管理备份、恢复、导出、设置和 AI 洞察 |
| Backend Control Plane | Django 5, DRF, Channels, Celery | REST API、WebSocket 编排、调度、审计、策略和持久化 |
| Proxy Agent | Go 1.21+, Kopia CLI | 在源端或采集节点执行备份、恢复任务 |
| Gateway Agent | Python 3.11+, Kopia CLI | 对快照做索引、搜索和 AI Summary |
| Database | PostgreSQL 15+ | 元数据持久化 |
| Broker / Realtime | Redis 7+ | Celery Broker、缓存和 Django Channels Layer |
| Backup Engine | Kopia | 快照创建、仓库访问、恢复和导出 |

## 当前能力

- 本地文件系统备份、通过 Sync Proxy 采集 NAS/NFS/SMB、S3 兼容对象存储仓库。
- 快照列表、快照浏览、同步、保留策略对齐、无变化快照展示、时间线/网格视图。
- Recovery Tasks：支持选择快照路径恢复。
- Recovery Exports：支持从快照选择文件打包导出、下载和分享。
- Gateway 快照索引、智能搜索、文件分类、大文件、重复候选、冷数据、增长趋势和 AI 总结。
- 平台侧 AI Provider 配置：在 `Settings -> AI Insights` 配置模型服务，API Key 加密保存，执行任务时临时下发给 Gateway。
- 多租户基础、License/Quota、审计日志、告警和系统设置。

## Docker Compose 快速部署

### 1. 环境要求

- Linux 主机，已安装 Docker 和 Docker Compose plugin。
- 默认开放端口：
  - 前端：`5001`
  - 后端 API/WebSocket：`8000`

### 2. 配置环境变量

```bash
git clone <your-repository-url> HyperFileLens
cd HyperFileLens
cp env.sample .env
```

编辑 `.env`，至少修改：

```env
SECRET_KEY=替换为足够长的随机字符串
DEBUG=false
ALLOWED_HOSTS=10.147.18.11,localhost,127.0.0.1,control
CSRF_TRUSTED_ORIGINS=http://10.147.18.11:5001,http://10.147.18.11:8000
CORS_ALLOWED_ORIGINS=http://10.147.18.11:5001,http://10.147.18.11:8000
POSTGRES_PASSWORD=替换为强密码
BACKEND_PORT=8000
FRONTEND_PORT=5001
```

### 3. 启动平台

```bash
docker compose up -d --build
```

默认启动：

- PostgreSQL
- Redis
- Backend Control Plane，使用 Daphne ASGI，支持 HTTP 和 WebSocket
- Celery Worker
- Celery Beat
- Frontend 静态服务，自动把 `/api/*` 代理到后端

创建管理员：

```bash
docker compose exec control python manage.py createsuperuser
```

访问地址：

```text
前端：http://<服务器IP>:5001
后端 API：http://<服务器IP>:8000/api/v1/
API 文档：http://<服务器IP>:8000/api/docs/
```

### 4. 常用命令

```bash
docker compose ps
docker compose logs -f control
docker compose logs -f celery-worker
docker compose restart control
docker compose down
```

## 可选 Agent 部署

通常建议 Agent 部署在独立机器上：Proxy 部署在源端或采集节点，Gateway 部署在索引/AI 节点。`docker-compose.yml` 也提供了可选 profile，方便实验环境把 Agent 跑在同一台机器上。

### Gateway Agent

当控制平面主机也需要作为 Gateway 使用时：

1. 在 Web 页面创建 Gateway。
2. 将生成的 `gateway_id` 和 install token 写入 `.env`：

```env
GATEWAY_SERVER_URL=http://control:8000
GATEWAY_WS_PROTOCOL=ws
GATEWAY_ID=<gateway-id>
GATEWAY_INSTALL_TOKEN=<install-token>
GATEWAY_NAME=gateway-01
```

3. 启动 Gateway Agent：

```bash
docker compose --profile gateway up -d --build gateway-agent
```

远程 Gateway 主机可以直接运行 Python Agent：

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

Proxy Agent 用于源端本地文件系统备份；Sync Proxy 用于 NAS/NFS/SMB 采集。

```bash
cd proxy
go build -o hyperfilelens-proxy .
```

示例 `config.yaml`：

```yaml
version: "1.0.0"
role: "agent" # 或 "sync"

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

启动：

```bash
./hyperfilelens-proxy --config config.yaml
```

实验环境也可以通过 compose 启动本地 Proxy：

```env
PROXY_SERVER_URL=http://control:8000
PROXY_API_TOKEN=<proxy-api-token>
PROXY_ROLE=agent
PROXY_SOURCE_PATH=/data
```

```bash
docker compose --profile proxy up -d --build proxy-agent
```

## AI Provider 配置

AI 模型配置在 Web 页面中完成：

```text
Settings -> AI Insights
```

支持：

- Local fallback：本地规则总结，不需要外部模型。
- OpenAI-compatible Provider：OpenAI、OpenRouter、DeepSeek、LiteLLM、vLLM、内部模型网关。
- Advanced JSON：可以配置自定义字段和 `config.headers`，用于 OpenRouter 等需要额外请求头的第三方转发平台。

控制面会加密保存 API Key。Gateway 只在执行 AI 任务时收到本次 Provider 配置，不在本地持久化密钥。

## 开发环境

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

启动 Worker：

```bash
celery -A core worker -l info
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 前端

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

## 项目结构

```text
HyperFileLens/
├── backend/                 # Django 控制面
│   ├── backup_tasks/        # 备份任务编排和快照
│   ├── recovery_tasks/      # 恢复任务和恢复导出
│   ├── repository/          # Kopia 仓库配置
│   ├── source_resources/    # Local/NAS/S3 源资源
│   ├── nodes/               # Proxy WebSocket 和 Proxy 管理
│   ├── gateways/            # Gateway WebSocket 和 Gateway 管理
│   ├── insights/            # 快照索引和洞察持久化
│   ├── ai_query/            # AI Insights API 和 AI Provider 配置
│   └── system_settings/     # 全局设置、SMTP、AI Provider 系统设置路由
├── frontend/                # Vue 3 Web 控制台
├── proxy/                   # Go Proxy / Sync Proxy Agent
├── gateway/
│   ├── agent/               # Python WebSocket Gateway Agent
│   └── app/                 # 旧 FastAPI Gateway 代码，仅保留参考
├── docker-compose.yml       # 生产/实验环境 Compose
├── docker-compose.dev.yml   # 开发环境 Compose
└── env.sample               # 环境变量模板
```

## 重要端点

| 端点 | 用途 |
| --- | --- |
| `/api/v1/accounts/` | 认证和用户 |
| `/api/v1/proxies/` | Proxy 管理 |
| `/api/v1/gateways/` | Gateway 管理 |
| `/api/v1/source-resources/` | 源资源 |
| `/api/v1/repositories/` | 备份仓库 |
| `/api/v1/backup-tasks/` | 备份任务、运行记录、快照 |
| `/api/v1/recovery-tasks/` | 恢复任务和恢复导出 |
| `/api/v1/insights/` | 快照索引、搜索、洞察、AI Summary |
| `/api/v1/ai-insights/` | AI Insights 看板和智能搜索 |
| `/api/v1/system/` | 系统设置、SMTP、AI Provider 配置 |
| `/ws/node/<proxy_id>/` | Proxy WebSocket |
| `/ws/gateway/<gateway_id>/` | Gateway WebSocket |

## 部署注意事项

- 后端必须以 ASGI 方式运行，也就是 `daphne core.asgi:application`，否则 Proxy/Gateway 的 WebSocket 不能工作。
- 默认前端服务会把 `/api/*` 和 `/static/*` 代理到后端。Docker 中代理目标是 `control:8000`。
- 当前 Gateway 执行链路是 Python WebSocket Gateway Agent，不再以旧 FastAPI Gateway 作为主路径部署。
- 生产环境建议在前端和后端前面放 Nginx/Traefik，并将 WebSocket 切换到 `wss`。

## 许可证

Apache 2.0 License，详见 [LICENSE](LICENSE)。
