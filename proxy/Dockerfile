# Build stage
FROM golang:1.21-alpine AS builder

ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=$GOPROXY

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum* ./

# Download dependencies
RUN go mod download || go mod tidy

# Copy source code
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o proxy .

# Runtime stage
FROM alpine:3.19

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache ca-certificates curl bash nfs-utils cifs-utils && \
    curl -L https://github.com/kopia/kopia/releases/download/v0.15.0/kopia_0.15.0_linux_x64.tar.gz | tar xz -C /usr/local/bin kopia && \
    chmod +x /usr/local/bin/kopia

# Copy binary from builder
COPY --from=builder /app/proxy /usr/local/bin/hyperfilelens-proxy

# Create directories
RUN mkdir -p /data /var/lib/hyperfilelens /var/log/hyperfilelens

# Copy default config
COPY config.example.yaml /opt/hyperfilelens/config.yaml

# Environment variables
ENV SERVER_URL=http://control:8000
ENV API_TOKEN=""
ENV PROXY_ROLE=agent
ENV CONFIG_PATH=/opt/hyperfilelens/config.yaml

ENTRYPOINT ["/usr/local/bin/hyperfilelens-proxy"]
CMD ["--config", "/opt/hyperfilelens/config.yaml"]
