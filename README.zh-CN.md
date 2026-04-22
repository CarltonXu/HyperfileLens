# HyperFileLens

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-green.svg)](https://vuejs.org/)

**中文** | [English](README.md)

HyperFileLens 是一款面向备份与归档数据的 AI 文件洞察平台。它能将您的备份数据转化为可访问、可分析、可操作的数字资产。

## 产品概述

HyperFileLens 超越传统备份解决方案，提供：

- **可靠的备份与恢复**：为本地文件系统、NAS 和 NFS 提供稳定的文件级备份能力
- **AI 驱动的洞察**：使用自然语言查询、分析和理解备份数据
- **集中管理**：基于 Web 的控制平面，用于策略配置、调度和监控
- **可扩展架构**：支持云端和混合部署的 Proxy 架构

## 核心功能

### 第一阶段：备份与恢复基础

- **多种数据源**
  - Windows/Linux 本地目录
  - NFS 共享目录
  - NAS 文件卷

- **备份目标**
  - 本地文件系统
  - NFS 共享
  - 对象存储（S3 兼容）
  - Azure Blob Storage
  - Google Cloud Storage

- **恢复选项**
  - 原位置恢复
  - 新位置恢复
  - 时间点恢复

### 第二阶段：AI 文件智能

- **自然语言查询**：用自然语言询问备份数据相关问题
- **内容分析**：提取并分析文档内容
- **敏感数据检测**：识别个人信息、凭据和敏感信息
- **变更检测**：追踪文件随时间的变化
- **智能摘要**：生成备份内容摘要

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    HyperFileLens 控制端                     │
│─────────────────────────────────────────────────────────────│
│ - 统一管控与任务编排                                        │
│ - 策略配置                                                  │
│ - 节点管理                                                  │
│ - 任务下发                                                  │
│ - 状态监控与审计                                            │
│ - AI Query 请求编排                                         │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
              通过 WebSocket 主动向上连接，仅承载控流
                              │
┌─────────────────────────────┼─────────────────────────────┐
│                             │                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  │   源端 Proxy 节点  │   │   NAS/文件源 Proxy│   │   其他源端 Proxy  │
│  │───────────────────│   │───────────────────│   │───────────────────│
│  │ - 本地文件系统接入 │   │ - NAS/NFS 接入    │   │ - 其他文件源接入  │
│  │ - 文件扫描        │   │ - 文件扫描        │   │ - 文件扫描        │
│  │ - 备份任务执行    │   │ - 备份任务执行    │   │ - 备份任务执行    │
│  │ - 恢复任务执行    │   │ - 恢复任务执行    │   │ - 恢复任务执行    │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘
│                             │
└─────────────────────────────┼─────────────────────────────┘
                              │
                    数据流直连
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    目标端 Gateway                           │
│─────────────────────────────────────────────────────────────│
│ - 接收源端数据流                                            │
│ - 对接备份仓库/恢复目标                                     │
│ - 管理备份数据写入                                          │
│ - 管理恢复数据输出                                          │
│ - 承载灾备侧 AI 数据访问入口                                │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         ▼                                         ▼
┌──────────────────┐                   ┌──────────────────┐
│     备份/归档仓库  │                   │      恢复目标端   │
│───────────────────│                   │───────────────────│
│ - 对象存储        │                   │ - 原位置恢复      │
│ - 本地文件系统    │                   │ - 新 NAS / 新 NFS │
│ - 块存储/其他存储 │                   │ - 新服务器        │
└──────────────────┘                   └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    云上 AI 能力层                           │
│─────────────────────────────────────────────────────────────│
│ - 外部模型 API / Token 接入                                  │
│ - 文件解析与内容提取                                         │
│ - OCR / 文本化                                               │
│ - AI Query / AI 分析                                        │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

### 后端

- **框架**: Django 5.x + Django REST Framework
- **任务队列**: Celery + Redis broker
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **WebSocket**: Django Channels

### 前端

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **状态管理**: Pinia
- **样式**: Tailwind CSS
- **组件**: Headless UI
- **国际化**: vue-i18n

## 快速开始

### 环境要求

- Docker & Docker Compose
- Git

### 克隆项目

```bash
git clone https://github.com/hyperbdr/hyperfilelens.git
cd hyperfilelens
```

### 开发环境

1. 复制环境配置文件：

```bash
cp env.sample .env.dev
```

2. 配置环境变量：

```env
POSTGRES_DB=hyperfilelens_dev
POSTGRES_USER=hyperfilelens_dev
POSTGRES_PASSWORD=hyperfilelens_dev
REDIS_PASSWORD=hyperfilelens_dev
SECRET_KEY=your-dev-secret-key
DEBUG=true
```

3. 启动服务：

```bash
docker-compose -f docker-compose.dev.yml up -d
```

4. 访问服务：

| 服务 | 地址 |
|------|------|
| Web UI | http://localhost:8000 |
| API 文档 | http://localhost:8000/swagger/ |
| 管理后台 | http://localhost:8000/admin/ |
| Celery 监控 | http://localhost:5555 |
| 前端开发 | http://localhost:5173 |

### 生产环境部署

1. 复制环境配置文件：

```bash
cp env.sample .env
```

2. 配置生产环境：

```env
POSTGRES_DB=hyperfilelens
POSTGRES_USER=hyperfilelens
POSTGRES_PASSWORD=strong-password-here
REDIS_PASSWORD=strong-password-here
SECRET_KEY=very-long-random-secret-key
DEBUG=false
ALLOWED_HOSTS=your-domain.com
```

3. 构建并启动：

```bash
docker-compose up -d --build
```

## 项目结构

```
hyperfilelens/
├── backend/                  # Django 后端
│   ├── core/                # 项目配置
│   │   ├── settings.py     # Django 设置
│   │   ├── urls.py         # URL 路由
│   │   ├── celery.py       # Celery 配置
│   │   └── wsgi.py         # WSGI 应用
│   ├── accounts/            # 用户管理
│   ├── nodes/               # Proxy 节点管理
│   ├── backup_tasks/        # 备份操作
│   ├── recovery_tasks/      # 恢复操作
│   ├── repository/          # 仓库管理
│   ├── policies/            # 备份策略
│   ├── ai_query/            # AI 查询处理
│   ├── audit_log/           # 审计日志
│   └── manage.py
├── frontend/                 # Vue.js 前端
│   ├── src/
│   │   ├── api/            # API 客户端
│   │   ├── components/     # 可复用组件
│   │   ├── views/          # 页面组件
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── router/        # Vue Router 配置
│   │   ├── i18n/          # 国际化
│   │   └── types/         # TypeScript 类型
│   └── package.json
├── docker/                  # Docker 配置
│   ├── nginx/              # Nginx 配置
│   └── entrypoint.sh       # 容器入口脚本
├── scripts/                 # 工具脚本
├── Dockerfile              # 生产环境 Dockerfile
├── Dockerfile.dev         # 开发环境 Dockerfile
├── docker-compose.yml     # 生产环境编排
├── docker-compose.dev.yml # 开发环境编排
└── README.md
```

## API 文档

服务启动后，访问 API 文档：

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

### 主要 API 端点

| 端点 | 描述 |
|------|------|
| `/api/v1/nodes/` | 管理 Proxy 节点 |
| `/api/v1/backup/tasks/` | 备份操作 |
| `/api/v1/recovery/tasks/` | 恢复操作 |
| `/api/v1/repository/` | 仓库管理 |
| `/api/v1/policies/` | 策略管理 |
| `/api/v1/ai/queries/` | AI 驱动的查询 |
| `/api/v1/audit/` | 审计日志 |

## 配置说明

### 备份策略配置

```python
{
    "name": "每日备份",
    "frequency": "daily",
    "schedule_time": "02:00:00",
    "backup_type": "incremental",
    "retention_days": 30,
    "retention_snapshots": 10,
    "compression_enabled": true
}
```

### 仓库配置

#### 本地文件系统

```python
{
    "repo_type": "local",
    "path": "/data/backup"
}
```

#### S3 兼容存储

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

## 开发指南

### 后端开发

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 执行数据库迁移
python manage.py migrate

# 创建超级管理员
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

### 前端开发

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm run dev

# 生产构建
pnpm run build
```

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
pnpm run test
```

## 贡献指南

欢迎贡献代码！请阅读我们的 [贡献指南](CONTRIBUTING.md) 了解更多细节。

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 获取支持

- **文档**: [docs.hyperfilelens.io](https://docs.hyperfilelens.io)
- **问题反馈**: [GitHub Issues](https://github.com/hyperbdr/hyperfilelens/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/hyperbdr/hyperfilelens/discussions)

## 产品路线图

### 第一阶段（当前）
- [x] 项目结构搭建
- [x] 后端核心模块
- [x] 前端核心 UI
- [ ] Proxy 节点实现
- [ ] 备份任务执行
- [ ] 恢复操作

### 第二阶段
- [ ] AI 查询集成
- [ ] 文档解析（PDF、Office）
- [ ] OCR 能力
- [ ] 自然语言搜索

### 第三阶段
- [ ] 多租户支持
- [ ] 高级分析
- [ ] 异常检测
- [ ] 合规报告

---

由 HyperBDR 团队用 ❤️ 构建
