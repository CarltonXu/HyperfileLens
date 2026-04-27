#!/bin/bash
#
# HyperFileLens Proxy Cross-Platform Build Script
#

set -e

VERSION=${VERSION:-"1.0.0"}
BUILD_DIR="build"
BINARY_NAME="hyperfilelens-proxy"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

# Platform configurations
PLATFORMS=(
    "linux/amd64"
    "linux/arm64"
    "windows/amd64"
    "darwin/amd64"
    "darwin/arm64"
)

build() {
    local platform=$1
    local os=$(echo $platform | cut -d'/' -f1)
    local arch=$(echo $platform | cut -d'/' -f2)
    local output_name="${BINARY_NAME}-${os}-${arch}"
    
    if [[ "$os" == "windows" ]]; then
        output_name="${output_name}.exe"
    fi
    
    log_info "Building for $platform..."
    
    CGO_ENABLED=0 GOOS=$os GOARCH=$arch go build \
        -ldflags="-s -w -X main.Version=${VERSION}" \
        -o "${BUILD_DIR}/${output_name}" \
        .
    
    # Create archive
    cd "$BUILD_DIR"
    tar -czf "${output_name}.tar.gz" "${output_name}"
    rm -f "${output_name}"
    cd ..
    
    log_info "Created: ${BUILD_DIR}/${output_name}.tar.gz"
}

build_all() {
    log_info "Building HyperFileLens Proxy v${VERSION}..."
    
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    
    for platform in "${PLATFORMS[@]}"; do
        build "$platform"
    done
    
    log_info "All builds completed!"
    ls -la "$BUILD_DIR"
}

build_current() {
    log_info "Building for current platform..."
    go build -o "${BUILD_DIR}/${BINARY_NAME}" .
    log_info "Created: ${BUILD_DIR}/${BINARY_NAME}"
}

case "${1:-all}" in
    all)
        build_all
        ;;
    current)
        build_current
        ;;
    linux-amd64)
        build "linux/amd64"
        ;;
    linux-arm64)
        build "linux/arm64"
        ;;
    *)
        echo "Usage: $0 [all|current|linux-amd64|linux-arm64]"
        exit 1
        ;;
esac
