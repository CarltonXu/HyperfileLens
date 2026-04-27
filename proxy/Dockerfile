# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod ./

# Download dependencies
RUN go mod download

# Copy source code
COPY *.go ./

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o proxy .

# Runtime stage
FROM alpine:3.19

WORKDIR /app

# Install Kopia and ca-certificates
RUN apk add --no-cache ca-certificates curl bash && \
    curl -L https://github.com/kopia/kopia/releases/download/v0.15.0/kopia_0.15.0_linux_x64.tar.gz | tar xz -C /usr/local/bin kopia && \
    chmod +x /usr/local/bin/kopia

# Copy binary from builder
COPY --from=builder /app/proxy /usr/local/bin/hyperfilelens-proxy

# Create directories
RUN mkdir -p /data /logs /var/lib/hyperfilelens/data /var/log/hyperfilelens

# Create config directory
RUN mkdir -p /opt/hyperfilelens

# Copy default config
COPY config.example.yaml /opt/hyperfilelens/config.yaml

ENV SERVER_URL=http://control:8000
ENV CONTROL_URL=ws://control:8000/ws/node/
ENV NODE_ID=""
ENV API_TOKEN=""
ENV LOG_LEVEL=info
ENV CONFIG_PATH=/opt/hyperfilelens/config.yaml

ENTRYPOINT ["/usr/local/bin/hyperfilelens-proxy"]
