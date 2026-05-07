#!/bin/bash
#
# HyperFileLens Gateway Agent Installation Script
# 
# Usage:
#   curl -sSL https://get.hyperfilelens.com/install-gateway.sh | bash -s -- \
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
KOPIA_VERSION="0.18.2"
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
        fuse \
        fuse3 \
        libfuse2 \
        libfuse3-4 \
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
        read -p "Reinstall? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # Download Kopia
    ARCH=$(dpkg --print-architecture)
    KOPIA_URL="https://github.com/kopia/kopia/releases/download/v${KOPIA_VERSION}/kopia_${KOPIA_VERSION}_linux_${ARCH}.deb"
    
    cd /tmp
    wget -q "$KOPIA_URL" -O kopia.deb
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
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Install Python dependencies
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install \
        websockets \
        psutil \
        pyyaml \
        aiohttp \
        python-dateutil \
        requests
    
    echo -e "${GREEN}Virtual environment created.${NC}"
}

# Install Gateway Agent
install_agent() {
    echo -e "${BLUE}Installing Gateway Agent...${NC}"
    
    # Copy agent files
    cp -r "$(dirname "$0")/agent" "$INSTALL_DIR/" 2>/dev/null || {
        # If running from curl, download from server
        echo -e "${YELLOW}Downloading agent files...${NC}"
        curl -sSL "${SERVER_URL}/downloads/gateway-agent.tar.gz" | tar xz -C "$INSTALL_DIR"
    }
    
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
