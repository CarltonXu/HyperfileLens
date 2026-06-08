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
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.prod.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" \
    -r requirements.prod.txt

# Copy project
COPY . .

# Create directories for static, media and logs
RUN mkdir -p /app/static /app/staticfiles /app/media /app/logs

# Expose port
EXPOSE 8000

# Run ASGI server so HTTP and WebSocket endpoints are both available.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
