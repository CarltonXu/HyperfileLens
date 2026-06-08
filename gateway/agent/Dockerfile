FROM python:3.11-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    fuse3 \
    libfuse3-3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN curl -s https://kopia.io/signing-key | gpg --dearmor -o /usr/share/keyrings/kopia-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kopia-keyring.gpg] https://packages.kopia.io/apt stable main" > /etc/apt/sources.list.d/kopia.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends kopia \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    -i "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST" \
    -r requirements.txt

COPY client.py .

RUN mkdir -p /mnt/kopia /var/lib/hyperfilelens/repository /var/log/hyperfilelens

CMD ["python", "client.py"]
