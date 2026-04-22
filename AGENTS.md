# HyperFileLens Development Guide

## Project Overview

HyperFileLens is an AI-powered file intelligence platform for backup and archive data. This document provides development guidelines and architectural overview for contributors.

## Technology Stack

### Backend
- Python 3.11+
- Django 5.x
- Django REST Framework
- Celery (task queue)
- Redis (broker/cache)
- PostgreSQL 15+
- Django Channels (WebSocket)

### Frontend
- Vue 3.4+
- TypeScript
- Vite
- Pinia (state management)
- Tailwind CSS
- Headless UI
- vue-i18n

## Project Structure

```
hyperfilelens/
├── backend/
│   ├── core/           # Django project configuration
│   ├── accounts/       # User authentication & management
│   ├── nodes/          # Proxy node management & WebSocket
│   ├── backup_tasks/   # Backup operations
│   ├── recovery_tasks/ # Recovery operations
│   ├── repository/     # Storage repository management
│   ├── policies/       # Backup policy scheduling
│   ├── ai_query/       # AI-powered queries
│   └── audit_log/      # Audit logging
├── frontend/
│   ├── src/
│   │   ├── api/       # Axios API client
│   │   ├── components/# Reusable UI components
│   │   ├── views/     # Page components
│   │   ├── stores/    # Pinia stores
│   │   ├── router/    # Vue Router config
│   │   └── i18n/      # Internationalization
│   └── package.json
└── docker/             # Docker configurations
```

## Development Setup

### Prerequisites
- Python 3.11+
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

### Docker Development
```bash
# Copy environment file
cp env.sample .env.dev

# Start all services
docker-compose -f docker-compose.dev.yml up -d
```

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

WebSocket consumers handle real-time communication with proxy nodes:

- `nodes/consumers.py`: Node connection management
- `nodes/routing.py`: WebSocket URL routing

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

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| REDIS_URL | Redis connection string | Yes |
| SECRET_KEY | Django secret key | Yes |
| DEBUG | Enable debug mode | No |
| ALLOWED_HOSTS | Allowed hostnames | Yes (prod) |

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

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Vue 3 Documentation](https://vuejs.org/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Django REST Framework](https://www.django-rest-framework.org/)
