# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)
[![Go](https://img.shields.io/badge/Go-1.21+-green.svg)](https://golang.org/)

[English](README.md) | **中文**

HyperFileLens 是一个 AI 驱动的文件智能平台，专为备份和归档数据设计。它将您的备份数据转化为可访问、可分析、可操作的知识资产。

## 架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HyperFileLens MVP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Frontend  │  │   Control   │  │   Gateway   │  │    Proxy    │         │
│  │   (Vue3)    │  │  (Django)   │  │  (FastAPI)  │  │    (Go)     │         │
│  │             │  │             │  │             │  │             │         │
│  │ • 仪表盘    │  │ • 用户管理   │  │ • Kopia     │  │ • Kopia CLI │         │
│  │ • 节点管理   │  │ • 节点管理   │  │   挂载      │  │ • 跨平台    │         │
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
│  │   数据库    │                                    │     消息队列    │      │
│  └─────────────┘                                    └─────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 组件说明

### 控制端 (Django)
- **端口**: 8000
- **功能**: 用户管理、节点管理、任务调度、WebSocket 通信、REST API
- **技术栈**: Django 5.x + Django REST Framework + Django Channels + Celery

### 网关 (FastAPI)
- **端口**: 8001
- **功能**: Kopia 仓库挂载、文件索引、AI 查询
- **技术栈**: FastAPI + uvicorn

### 代理 (Go)
- **功能**: 接收控制端指令、执行 Kopia CLI 备份/恢复操作
- **技术栈**: Go 1.21+ + gorilla/websocket
- **平台支持**: Windows, Linux, macOS

### 前端 (Vue3)
- **端口**: 5000
- **功能**: 仪表盘、节点管理、备份任务、恢复任务、AI 查询
- **技术栈**: Vue 3 + Vite + Pinia + Tailwind CSS + Headless UI

## 技术栈

| 组件 | 技术 |
|------|------|
| 控制端 | Django 5.x, Django REST Framework, Celery, Django Channels |
| 网关 | FastAPI, uvicorn |
| 代理 | Go 1.21+, gorilla/websocket |
| 前端 | Vue 3, Vite, Pinia, Tailwind CSS, Headless UI |
| 数据库 | PostgreSQL 15+ |
| 缓存/消息队列 | Redis 7+ |
| 备份引擎 | Kopia |

## 快速开始

### 环境要求

- Docker & Docker Compose
- Go 1.21+ (Proxy 开发)
- Node.js 20+ & pnpm (前端开发)
- Python 3.11+ (控制端 & 网关开发)

### Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/hyperbdr/hyperfilelens.git
cd hyperfilelens

# 启动所有服务
docker-compose up -d

# 访问应用
# 前端: http://localhost:5000
# 控制端 API: http://localhost:8000/api/v1/
# 网关 API: http://localhost:8001/
```

### 开发模式

```bash
# 启动开发环境
./scripts/start-dev.sh

# 停止所有服务
./scripts/stop.sh
```

### 手动启动

```bash
# 1. 启动后端（控制端）
cd backend
pip install -r requirements.txt
USE_POSTGRES=false python manage.py migrate
USE_POSTGRES=false python manage.py runserver 0.0.0.0:8000

# 2. 启动前端
cd frontend
pnpm install
pnpm build
node server.cjs

# 3. 启动网关
cd gateway
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 4. 启动代理
cd proxy
go run main.go
```

## 默认凭据

- **邮箱**: admin@hyperfilelens.com
- **密码**: admin123

## 功能特性

### 第一阶段：备份与恢复基础

- **源端资源**: NAS, NFS, CIFS, S3, 本地文件系统
- **备份目标**: S3, Azure, GCS, NFS, 本地文件系统
- **恢复选项**: 原位置恢复、新位置恢复、时间点恢复

### 第二阶段：AI 文件智能

- **自然语言查询**: 用自然语言查询备份数据
- **内容分析**: 提取和分析文档内容
- **智能搜索**: 跨所有备份搜索文件

## 项目结构

```
hyperfilelens/
├── backend/              # Django 控制端
│   ├── accounts/         # 用户管理
│   ├── nodes/            # 节点管理 & WebSocket
│   ├── backup_tasks/     # 备份操作
│   ├── recovery_tasks/   # 恢复操作
│   ├── source_resources/ # 源端资源管理
│   ├── repository/       # 备份仓库管理
│   ├── policies/         # 备份策略调度
│   ├── ai_query/         # AI 查询
│   └── audit_log/        # 审计日志
├── gateway/              # FastAPI 网关
│   └── app/
│       ├── main.py       # FastAPI 应用
│       ├── mount.py      # Kopia 挂载操作
│       ├── indexer.py    # 文件索引
│       └── ai.py         # AI 查询处理
├── proxy/                # Go 代理
│   ├── main.go           # 代理入口
│   └── build.sh          # 构建脚本
├── frontend/             # Vue3 前端
│   └── src/
│       ├── views/        # 页面组件
│       ├── stores/       # Pinia 状态管理
│       ├── api/          # API 客户端
│       └── i18n/         # 国际化
├── docker-compose.yml    # Docker Compose 配置
└── scripts/              # 工具脚本
```

## API 端点

### 控制端 (端口 8000)

| 端点 | 描述 |
|------|------|
| `/api/v1/accounts/` | 用户管理 |
| `/api/v1/nodes/` | 节点管理 |
| `/api/v1/source-resources/` | 源端资源 |
| `/api/v1/repository/repositories/` | 备份仓库 |
| `/api/v1/backup-tasks/` | 备份任务 |
| `/api/v1/recovery-tasks/` | 恢复任务 |
| `/ws/node/{node_id}/` | Proxy WebSocket |

### 网关 (端口 8001)

| 端点 | 描述 |
|------|------|
| `/files` | 列出挂载文件 |
| `/snapshots` | 列出快照 |
| `/ai/query` | AI 查询 |

## 许可证

Apache 2.0 许可证 - 详见 [LICENSE](LICENSE)。

## 贡献

欢迎贡献代码！提交 PR 前请阅读贡献指南。
