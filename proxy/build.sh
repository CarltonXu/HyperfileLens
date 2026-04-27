#!/bin/bash

# HyperFileLens Proxy Build Script
# Builds cross-platform binaries for the proxy

set -e

VERSION=${VERSION:-"1.0.0"}
BUILD_DIR="bin"
BINARY_NAME="hyperfilelens-proxy"

echo "Building HyperFileLens Proxy v${VERSION}..."

# Create build directory
mkdir -p ${BUILD_DIR}

# Get git commit if available
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build flags
LDFLAGS="-s -w -X main.Version=${VERSION} -X main.GitCommit=${GIT_COMMIT} -X main.BuildTime=${BUILD_TIME}"

# Build for multiple platforms
echo ""
echo "Building for Linux amd64..."
GOOS=linux GOARCH=amd64 go build -ldflags "${LDFLAGS}" -o ${BUILD_DIR}/${BINARY_NAME}-linux-amd64 .

echo "Building for Linux arm64..."
GOOS=linux GOARCH=arm64 go build -ldflags "${LDFLAGS}" -o ${BUILD_DIR}/${BINARY_NAME}-linux-arm64 .

echo "Building for Windows amd64..."
GOOS=windows GOARCH=amd64 go build -ldflags "${LDFLAGS}" -o ${BUILD_DIR}/${BINARY_NAME}-windows-amd64.exe .

echo "Building for macOS amd64..."
GOOS=darwin GOARCH=amd64 go build -ldflags "${LDFLAGS}" -o ${BUILD_DIR}/${BINARY_NAME}-darwin-amd64 .

echo "Building for macOS arm64..."
GOOS=darwin GOARCH=arm64 go build -ldflags "${LDFLAGS}" -o ${BUILD_DIR}/${BINARY_NAME}-darwin-arm64 .

echo ""
echo "Build complete! Binaries available in ${BUILD_DIR}/"
echo ""
ls -la ${BUILD_DIR}/

# Create archives
echo ""
echo "Creating release archives..."
cd ${BUILD_DIR}

for bin in ${BINARY_NAME}-*; do
    if [[ -f "$bin" ]]; then
        tar -czf "${bin}.tar.gz" "$bin"
        echo "Created ${bin}.tar.gz"
    fi
done

echo ""
echo "Release packages:"
ls -la *.tar.gz 2>/dev/null || echo "No archives created"
