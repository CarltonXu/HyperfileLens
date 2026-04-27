# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum* ./

# Download dependencies
RUN go mod download || true

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
COPY --from=builder /app/proxy .

# Create directories
RUN mkdir -p /data /logs

ENV CONTROL_URL=ws://control:8000/ws/node/
ENV NODE_ID=proxy-1
ENV LOG_LEVEL=info

ENTRYPOINT ["./proxy"]
