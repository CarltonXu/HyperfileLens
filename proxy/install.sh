#!/bin/bash
#
# HyperFileLens Proxy Installation Script
#
# This script installs the HyperFileLens proxy with role-based configuration.
#
# Usage:
#   curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash
#   curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash -s -- --role agent
#   curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash -s -- --role sync --server https://control.example.com --token <token>
#

set -e

VERSION="1.0.0"
PROXY_HOME="/opt/hyperfilelens"
PROXY_USER="hyperfilelens"
PROXY_SERVICE="hyperfilelens-proxy"
LOG_FILE="/var/log/hyperfilelens/install.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
ROLE="agent"
SERVER_URL=""
API_TOKEN=""
SKIP_KOPIA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --role)
            ROLE="$2"
            shift 2
            ;;
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --token)
            API_TOKEN="$2"
            shift 2
            ;;
        --skip-kopia)
            SKIP_KOPIA=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --role ROLE       Proxy role: 'agent' (source) or 'sync' (collector)"
            echo "  --server URL      Control server URL"
            echo "  --token TOKEN     API token for authentication"
            echo "  --skip-kopia      Skip Kopia installation"
            echo "  --help            Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate role
if [[ "$ROLE" != "agent" && "$ROLE" != "sync" ]]; then
    echo -e "${RED}Invalid role: $ROLE. Must be 'agent' or 'sync'${NC}"
    exit 1
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
    log_info "Detected OS: $OS"
}

create_user() {
    if ! id "$PROXY_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$PROXY_HOME" -c "HyperFileLens Proxy" "$PROXY_USER"
        log_info "Created user: $PROXY_USER"
    fi
}

install_kopia() {
    if [[ "$SKIP_KOPIA" == "true" ]]; then
        log_info "Skipping Kopia installation"
        return
    fi
    
    if command -v kopia &> /dev/null; then
        log_info "Kopia already installed: $(kopia --version)"
        return
    fi
    
    log_info "Installing Kopia..."
    
    case $OS in
        ubuntu|debian)
            curl -sSL https://kopia.io/signing-key | gpg --dearmor -o /usr/share/keyrings/kopia-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/kopia-keyring.gpg] https://kopia.io/apt stable main" > /etc/apt/sources.list.d/kopia.list
            apt-get update && apt-get install -y kopia
            ;;
        centos|rhel|rocky|almalinux)
            rpm --import https://kopia.io/signing-key
            cat > /etc/yum.repos.d/kopia.repo << 'EOF'
[kopia]
name=Kopia
baseurl=https://kopia.io/yum
enabled=1
gpgcheck=1
EOF
            yum install -y kopia
            ;;
        *)
            log_error "Please install Kopia manually from: https://kopia.io/docs/installation/"
            ;;
    esac
}

create_config() {
    log_info "Creating configuration..."
    
    mkdir -p "$PROXY_HOME"
    
    # Mount dependencies for sync role
    MOUNT_TOOLS=""
    if [[ "$ROLE" == "sync" ]]; then
        case $OS in
            ubuntu|debian)
                MOUNT_TOOLS="nfs-common cifs-utils"
                ;;
            centos|rhel|rocky|almalinux)
                MOUNT_TOOLS="nfs-utils cifs-utils"
                ;;
        esac
        if [[ -n "$MOUNT_TOOLS" ]]; then
            log_info "Installing mount tools: $MOUNT_TOOLS"
            case $OS in
                ubuntu|debian) apt-get install -y $MOUNT_TOOLS ;;
                *) yum install -y $MOUNT_TOOLS ;;
            esac
        fi
    fi
    
    cat > "$PROXY_HOME/config.yaml" << EOF
# HyperFileLens Proxy Configuration
version: "${VERSION}"
role: "${ROLE}"

server:
  url: "${SERVER_URL:-http://localhost:8000}"
  api_token: "${API_TOKEN:-}"
  ws_protocol: "ws"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  name: ""
  hostname: "$(hostname)"

kopia:
  path: "/usr/bin/kopia"
  cache_path: "/var/lib/hyperfilelens/cache"

mount:
  enabled: $([[ "$ROLE" == "sync" ]] && echo "true" || echo "false")

logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
EOF
    
    chown -R "$PROXY_USER:$PROXY_USER" "$PROXY_HOME"
    log_success "Configuration created"
}

create_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${PROXY_SERVICE}.service << EOF
[Unit]
Description=HyperFileLens Proxy (${ROLE})
After=network.target

[Service]
Type=simple
User=${PROXY_USER}
Group=${PROXY_USER}
WorkingDirectory=${PROXY_HOME}
ExecStart=/usr/local/bin/hyperfilelens-proxy --config ${PROXY_HOME}/config.yaml
Restart=on-failure
RestartSec=10

Environment=CONFIG_PATH=${PROXY_HOME}/config.yaml

StandardOutput=journal
StandardError=journal
SyslogIdentifier=hyperfilelens-proxy

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${PROXY_SERVICE}
    log_success "Service created"
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Proxy Installation"
    echo "=========================================="
    echo ""
    echo "  Role:     ${ROLE}"
    echo "  Server:   ${SERVER_URL:-http://localhost:8000}"
    echo "  Config:   ${PROXY_HOME}/config.yaml"
    echo ""
    echo "  Commands:"
    echo "    Start:   systemctl start ${PROXY_SERVICE}"
    echo "    Stop:    systemctl stop ${PROXY_SERVICE}"
    echo "    Logs:    journalctl -u ${PROXY_SERVICE} -f"
    echo ""
    echo "=========================================="
    echo ""
}

main() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Proxy Installer"
    echo "  Version: ${VERSION}"
    echo "=========================================="
    echo ""
    
    mkdir -p $(dirname "$LOG_FILE")
    
    check_root
    detect_os
    create_user
    install_kopia
    create_config
    create_service
    
    log_success "Installation completed!"
    print_summary
}

main
