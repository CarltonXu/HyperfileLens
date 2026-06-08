# HyperFileLens Control Plane (Django)
FROM python:3.11-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    gcc \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Go for building proxy binaries (using GoChina mirror)
RUN curl -sL https://mirrors.aliyun.com/golang/go1.26.3.linux-amd64.tar.gz | tar -C /usr/local -xzf -
ENV PATH=$PATH:/usr/local/go/bin
ENV GOPATH=/root/go
ENV CGO_ENABLED=0

# Install Python dependencies
COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" \
    -r requirements.prod.txt

# Copy project (context is repo root, so backend/* goes to /app/backend/*)
COPY . .

# Create symlink so backend/static points to /app/static (for downloads)
RUN if [ -d "/app/backend/static" ] && [ ! -L "/app/backend/static/downloads" ]; then \
    ln -s /app/static /app/backend/static; \
    fi

# Create directories for static, media and logs
RUN mkdir -p /app/static /app/staticfiles /app/media /app/logs

# Build proxy binaries if source exists
RUN if [ -d "/app/proxy" ]; then \
    cd /app/proxy && \
    ./build.sh all; \
    fi

# Build gateway packages if source exists
RUN if [ -d "/app/gateway" ]; then \
    cd /app/gateway && \
    ./build.sh; \
    fi

# Expose port
EXPOSE 8000

# Run ASGI server so HTTP and WebSocket endpoints are both available.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
