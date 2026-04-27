FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    fuse3 \
    libfuse3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Kopia
RUN curl -s https://kopia.io/signing-key | gpg --dearmor -o /usr/share/keyrings/kopia-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kopia-keyring.gpg] https://packages.kopia.io/apt stable main" > /etc/apt/sources.list.d/kopia.list \
    && apt-get update \
    && apt-get install -y kopia \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for mount and repo
RUN mkdir -p /mnt/kopia /data/repo

ENV KOPIA_MOUNT_PATH=/mnt/kopia
ENV REPO_PATH=/data/repo
ENV CONTROL_URL=http://localhost:8000

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
