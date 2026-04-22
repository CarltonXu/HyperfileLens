# =====================================================
# HyperFileLens Dockerfile
# Multi-stage build for optimized production image
# =====================================================

# Stage 1: Base image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBITCODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    gettext \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =====================================================
# Backend stage
# =====================================================
FROM base as backend

# Copy requirements files
COPY backend/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Collect static files
RUN python manage.py collectstatic --noinput || true

# =====================================================
# Frontend stage
# =====================================================
FROM node:20-alpine as frontend

WORKDIR /app

# Copy frontend files
COPY frontend/package.json frontend/pnpm-lock.yaml* /app/
COPY frontend/ /app/

# Install dependencies
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# Build frontend
RUN pnpm run build

# =====================================================
# Production stage
# =====================================================
FROM base as production

# Install Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Nginx configuration
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Copy backend from backend stage
COPY --from=backend /app/ /app/
COPY --from=backend /app/staticfiles/ /app/staticfiles/

# Copy frontend build from frontend stage
COPY --from=frontend /app/dist/ /app/frontend/dist/

# Copy entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/logs /app/media /run

# Expose ports
EXPOSE 8000 5555

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-c", "/app/gunicorn.conf.py", "core.wsgi:application"]
