#!/bin/bash
#
# HyperFileLens Gateway Agent Installation Script
# 
# Usage:
#   curl -sSL https://hfl.example.com/downloads/install-gateway.sh | bash -s -- \
#     --server https://control.hyperfilelens.com \
#     --token YOUR_INSTALL_TOKEN

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SERVER_URL=""
INSTALL_TOKEN=""
GATEWAY_NAME=""
GATEWAY_ID=""
KOPIA_VERSION="0.22.3"
INSTALL_DIR="/opt/hyperfilelens/gateway"
CONFIG_DIR="/etc/hyperfilelens/gateway"
LOG_DIR="/var/log/hyperfilelens"
DATA_DIR="/var/lib/hyperfilelens"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --token)
            INSTALL_TOKEN="$2"
            shift 2
            ;;
        --name)
            GATEWAY_NAME="$2"
            shift 2
            ;;
        --gateway-id)
            GATEWAY_ID="$2"
            shift 2
            ;;
        --help)
            echo "HyperFileLens Gateway Agent Installation Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --server URL        Control plane URL (required)"
            echo "  --token TOKEN       Installation token (required)"
            echo "  --name NAME         Gateway name (optional)"
            echo "  --gateway-id ID     Gateway ID (optional)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check requirements
check_requirements() {
    echo -e "${BLUE}Checking requirements...${NC}"
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        echo -e "${RED}Cannot detect OS. /etc/os-release not found.${NC}"
        exit 1
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]]; then
        echo -e "${YELLOW}Warning: This script is designed for Ubuntu/Debian.${NC}"
        echo -e "${YELLOW}Current OS: $PRETTY_NAME${NC}"
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is required but not installed.${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1,2)
    echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"
    
    # Check for required commands
    for cmd in curl tar; do
        if ! command -v $cmd &> /dev/null; then
            echo -e "${YELLOW}Installing $cmd...${NC}"
            apt-get update && apt-get install -y $cmd
        fi
    done
}

# Install system dependencies
install_dependencies() {
    echo -e "${BLUE}Installing system dependencies...${NC}"
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-psutil \
        python3-websockets \
        fuse3 \
        libfuse3-3 \
        nfs-common \
        cifs-utils \
        curl \
        wget \
        tar \
        jq
    
    echo -e "${GREEN}System dependencies installed.${NC}"
}

# Install Kopia
install_kopia() {
    echo -e "${BLUE}Installing Kopia v${KOPIA_VERSION}...${NC}"
    
    if command -v kopia &> /dev/null; then
        CURRENT_VERSION=$(kopia version 2>/dev/null | head -1 || echo "unknown")
        echo -e "${YELLOW}Kopia already installed: $CURRENT_VERSION${NC}"
        echo -e "${GREEN}Using existing Kopia installation.${NC}"
        return
    fi
    
    ARCH=$(dpkg --print-architecture)
    KOPIA_PACKAGE="kopia_${KOPIA_VERSION}_linux_${ARCH}.deb"
    LOCAL_KOPIA_URL="${SERVER_URL}/downloads/packages/kopia/${KOPIA_PACKAGE}"
    FALLBACK_KOPIA_URL="https://github.com/kopia/kopia/releases/download/v${KOPIA_VERSION}/${KOPIA_PACKAGE}"
    
    cd /tmp
    if ! curl -fsSL "$LOCAL_KOPIA_URL" -o kopia.deb; then
        echo -e "${YELLOW}Kopia package not found on control plane, falling back to GitHub.${NC}"
        curl -fsSL "$FALLBACK_KOPIA_URL" -o kopia.deb
    fi
    dpkg -i kopia.deb || apt-get install -f -y
    rm -f kopia.deb
    
    # Verify
    KOPIA_BIN=$(which kopia)
    echo -e "${GREEN}Kopia installed: $(kopia version)${NC}"
}

# Create virtual environment
setup_virtualenv() {
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/repository"
    mkdir -p "$DATA_DIR/index"
    
    # Recreate the venv so it can use the distro Python packages installed by apt.
    rm -rf "$INSTALL_DIR/venv"
    python3 -m venv --system-site-packages "$INSTALL_DIR/venv"
    
    echo -e "${GREEN}Virtual environment created.${NC}"
}

# Install Python dependencies
install_python_dependencies() {
    echo -e "${BLUE}Checking Python dependencies...${NC}"

    ARCH="$(dpkg --print-architecture)"
    WHEEL_DIR="$INSTALL_DIR/agent/wheels/linux-${ARCH}"

    if ! "$INSTALL_DIR/venv/bin/python" - <<'PY'
import psutil
PY
    then
        echo -e "${RED}Missing Python dependency: psutil. Expected python3-psutil from apt.${NC}"
        exit 1
    fi

    if "$INSTALL_DIR/venv/bin/python" - <<'PY'
from importlib import metadata

version = metadata.version("websockets")
major = int(version.split(".", 1)[0])
if major < 12 or major >= 13:
    raise SystemExit(1)
PY
    then
        echo -e "${GREEN}Python dependencies are available from system packages.${NC}"
        return
    fi

    if [[ -d "$WHEEL_DIR" ]]; then
        "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links "$WHEEL_DIR" "websockets>=12,<13"
        "$INSTALL_DIR/venv/bin/python" - <<'PY'
import psutil
import websockets
PY
        echo -e "${GREEN}Python dependencies installed from bundled wheels.${NC}"
        return
    fi

    echo -e "${RED}Missing compatible websockets package and no bundled wheel found for ${ARCH}.${NC}"
    exit 1
}

# Install Gateway Agent
install_agent() {
    echo -e "${BLUE}Installing Gateway Agent...${NC}"
    
    local script_dir=""
    if [[ -n "${BASH_SOURCE[0]:-}" ]] && [[ -f "${BASH_SOURCE[0]}" ]]; then
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi

    if [[ -n "$script_dir" ]] && [[ -f "${script_dir}/agent/client.py" ]]; then
        cp -r "${script_dir}/agent" "$INSTALL_DIR/"
    else
        echo -e "${YELLOW}Downloading agent files...${NC}"
        ARCH="$(dpkg --print-architecture)"
        case "$ARCH" in
            amd64|arm64)
                ;;
            *)
                echo -e "${RED}Unsupported architecture: $ARCH${NC}"
                exit 1
                ;;
        esac
        curl -fsSL "${SERVER_URL}/downloads/packages/gateway/hyperfilelens-gateway-linux-${ARCH}.tar.gz" | tar xz -C "$INSTALL_DIR"
    fi

    if [[ ! -f "$INSTALL_DIR/agent/client.py" ]] || [[ ! -f "$INSTALL_DIR/agent/requirements.txt" ]]; then
        echo -e "${RED}Gateway package is incomplete. Missing agent/client.py or agent/requirements.txt.${NC}"
        exit 1
    fi
    
    # Create config
    if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
        cat > "$CONFIG_DIR/config.yaml" << EOF
# HyperFileLens Gateway Configuration
server:
  url: "${SERVER_URL}"
  api_token: ""
  ws_protocol: "ws"
  reconnect_delay: 5
  heartbeat_interval: 10

gateway:
  id: "${GATEWAY_ID}"
  name: "${GATEWAY_NAME:-$(hostname)}"
  install_token: "${INSTALL_TOKEN}"

kopia:
  path: "/usr/bin/kopia"
  mount_base_path: "/mnt/kopia"
  max_concurrent_mounts: 10
  repository_path: "${DATA_DIR}/repository"
  password: ""

index:
  enabled: true
  index_path: "${DATA_DIR}/index"

logging:
  level: "INFO"
  file: "${LOG_DIR}/gateway.log"
EOF
    fi
    
    echo -e "${GREEN}Gateway Agent installed.${NC}"
}

# Create systemd service
create_service() {
    echo -e "${BLUE}Creating systemd service...${NC}"
    
    cat > /etc/systemd/system/hyperfilelens-gateway.service << EOF
[Unit]
Description=HyperFileLens Gateway Agent
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/agent/client.py
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/gateway.log
StandardError=append:${LOG_DIR}/gateway.log

# Environment
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${CONFIG_DIR}/env

[Install]
WantedBy=multi-user.target
EOF
    
    # Create environment file
    cat > "${CONFIG_DIR}/env" << EOF
SERVER_URL=${SERVER_URL}
INSTALL_TOKEN=${INSTALL_TOKEN}
GATEWAY_ID=${GATEWAY_ID}
GATEWAY_NAME=${GATEWAY_NAME:-$(hostname)}
EOF
    
    systemctl daemon-reload
    systemctl enable hyperfilelens-gateway
    
    echo -e "${GREEN}Service created.${NC}"
}

# Start service
start_service() {
    echo -e "${BLUE}Starting Gateway Agent...${NC}"
    
    systemctl start hyperfilelens-gateway
    sleep 2
    
    if systemctl is-active --quiet hyperfilelens-gateway; then
        echo -e "${GREEN}Gateway Agent started successfully!${NC}"
    else
        echo -e "${RED}Failed to start Gateway Agent.${NC}"
        echo -e "${YELLOW}Check logs: journalctl -u hyperfilelens-gateway -f${NC}"
        exit 1
    fi
}

# Main
main() {
    echo -e "${BLUE}"
    echo "===================================="
    echo " HyperFileLens Gateway Installation"
    echo "===================================="
    echo -e "${NC}"
    
    # Validate arguments
    if [[ -z "$SERVER_URL" ]]; then
        echo -e "${RED}Error: --server is required${NC}"
        exit 1
    fi
    
    if [[ -z "$INSTALL_TOKEN" ]]; then
        echo -e "${RED}Error: --token is required${NC}"
        exit 1
    fi
    
    check_requirements
    install_dependencies
    install_kopia
    setup_virtualenv
    install_agent
    install_python_dependencies
    create_service
    start_service
    
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN} Gateway Agent installed successfully!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo "Configuration: $CONFIG_DIR/config.yaml"
    echo "Logs:          $LOG_DIR/gateway.log"
    echo ""
    echo "Commands:"
    echo "  Status:   systemctl status hyperfilelens-gateway"
    echo "  Start:    systemctl start hyperfilelens-gateway"
    echo "  Stop:     systemctl stop hyperfilelens-gateway"
    echo "  Logs:     journalctl -u hyperfilelens-gateway -f"
    echo ""
}

main
