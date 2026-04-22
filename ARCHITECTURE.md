# HyperFileLens

## Product Vision

**HyperFileLens** is an AI-powered file intelligence platform designed for backup and archive data. Its core goal is not just to "backup files" but to enable these historical data to be searched, understood, analyzed, and reutilized, transforming backup data into true enterprise data assets and knowledge assets.

## English Positioning

- **English**: AI-Powered File Intelligence for Backup and Archive Data
- **Chinese**: 面向备份与归档数据的 AI 文件洞察平台

## Product Evolution Roadmap

### Phase 1: Establish File-Level Backup and Recovery Capabilities

The focus of Phase 1 is not AI, but establishing a stable, usable file-level backup system to provide the data foundation for subsequent AI capabilities.

#### Data Sources

Currently supports two main source types:
- Local filesystem (Windows/Linux directories)
- NAS/NFS shared storage
- (Future: Microsoft Exchange Server, Microsoft 365 / Office 365)

#### Target Storage

Plan to use **Kopia** as the underlying backup engine, supporting:
- Object storage
- Local filesystem
- Network filesystem
- Cloud storage services

#### Recovery Scenarios

Two primary recovery methods:
1. **Original Location Recovery**: Restore files to their original location
2. **New Location Recovery**: Restore files to a new location

### Phase 2: Introduce AI File Intelligence Capabilities

After the backup system is stable, Phase 2 realizes HyperFileLens's true value - making backup data not only recoverable but also "understandable."

AI capabilities run on the DR/backup side without affecting the production environment.

Users can ask questions, search, and analyze backup data directly:
- "Find all contracts signed last year"
- "Which directories contain sensitive information (ID cards, phone numbers, bank cards)?"
- "What changes were made to this file compared to three months ago?"
- "Summarize all PDF and Word content in this project directory"

## Overall Product Architecture

```
                        ┌─────────────────────────────────────┐
                        │         HyperFileLens Control        │
                        │-------------------------------------│
                        │ - Unified management & orchestration│
                        │ - Policy configuration              │
                        │ - Node management                   │
                        │ - Task distribution                 │
                        │ - Status monitoring & audit         │
                        │ - AI Query orchestration            │
                        └─────────────────────────────────────┘
                                      ▲
                                      │
                    WebSocket (active upward connection, control flow only)
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│   Source Proxy Node  │   │   NAS/File Proxy     │   │   Other Source Proxy │
│----------------------│   │----------------------│   │----------------------│
│ - Local FS access    │   │ - NAS/NFS access     │   │ - Other file sources │
│ - File scanning      │   │ - File scanning      │   │ - File scanning      │
│ - Backup execution   │   │ - Backup execution   │   │ - Backup execution   │
│ - Recovery execution │   │ - Recovery execution │   │ - Recovery execution │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
             │                        │                        │
             └────────────────────────┴────────────────────────┘
                                      │
                                      │ Data flow (direct connection)
                                      ▼
                        ┌─────────────────────────────────────┐
                        │          Target Gateway              │
                        │-------------------------------------│
                        │ - Receive source data streams       │
                        │ - Connect backup repository/target  │
                        │ - Manage backup data writes         │
                        │ - Manage recovery data output       │
                        │ - AI data access entry (DR side)    │
                        └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
         ┌──────────────────────┐           ┌──────────────────────┐
         │    Backup/Archive    │           │    Recovery Target   │
         │----------------------│           │----------------------│
         │ - Object storage    │           │ - Original location  │
         │ - Local filesystem  │           │ - New location       │
         │ - Block storage     │           │ - New NAS/NFS       │
         └──────────────────────┘           └──────────────────────┘

                                      │
                                      ▼
                        ┌─────────────────────────────────────┐
                        │         Cloud AI Capability Layer   │
                        │-------------------------------------│
                        │ - External model API / Token       │
                        │ - File parsing & content extraction │
                        │ - OCR / Textualization             │
                        │ - DeepAgent / AI Query              │
                        │ - Query, Summary, Analysis         │
                        └─────────────────────────────────────┘
```

## Core Principles

> Phase 1: Enable enterprise data to be safely stored and recovered.
> Phase 2: Enable enterprises to truly understand their backup data.

## Technology Stack

### Backend
- **Framework**: Django REST Framework + Celery
- **Database**: PostgreSQL (recommended), MySQL
- **Cache**: Redis
- **Task Queue**: Celery + Redis
- **Backup Engine**: Kopia

### Frontend
- **Framework**: Vue 3 (Composition API + TypeScript)
- **Build Tool**: Vite
- **UI Components**: Headless UI + Custom Components
- **State Management**: Pinia
- **Router**: Vue Router
- **Styling**: Tailwind CSS
- **i18n**: vue-i18n

### Deployment
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx

## Key Features

### 1. Node Management
- Register/unregister source proxy nodes
- Register/unregister target gateway nodes
- Node status monitoring
- Connection health checks

### 2. Backup Management
- Create/configure backup policies
- Manual and scheduled backup tasks
- Incremental and full backup support
- Backup progress monitoring
- Backup history and versioning

### 3. Recovery Management
- Original location recovery
- New location recovery
- Point-in-time recovery
- Recovery progress monitoring

### 4. Repository Management
- Backup repository configuration
- Storage capacity monitoring
- Repository health status
- Data retention policies

### 5. AI Intelligence (Phase 2)
- File content search and analysis
- OCR for scanned documents
- Sensitive information detection
- Document summarization
- Anomaly detection

## Security Features

- Role-based access control (RBAC)
- API authentication and authorization
- Audit logging
- Data encryption at rest and in transit
- Secure WebSocket connections

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
