#!/bin/bash
#
# HyperFileLens Proxy Installation Script
#
# This script installs the HyperFileLens proxy with role-based configuration.
#
# Usage:
#   curl -sSL https://get.hyperfilelens.com/install.sh | bash -s -- \
#     --proxy-id <uuid> \
#     --role agent \
#     --server https://control.example.com \
#     --token <install_token>
#
# Flow:
#   1. Install dependencies (Kopia, mount tools for sync)
#   2. Call /api/v1/proxies/register/ with proxy_id and install_token
#   3. Receive api_token from server
#   4. Save configuration with api_token
#   5. Start proxy service
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
PROXY_ID=""
ROLE="agent"
SERVER_URL=""
INSTALL_TOKEN=""
NAME=""
SKIP_KOPIA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --proxy-id)
            PROXY_ID="$2"
            shift 2
            ;;
        --role)
            ROLE="$2"
            shift 2
            ;;
        --server)
            SERVER_URL="$2"
            shift 2
            ;;
        --token)
            INSTALL_TOKEN="$2"
            shift 2
            ;;
        --name)
            NAME="$2"
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
            echo "  --proxy-id ID     Proxy ID (UUID from management console)"
            echo "  --role ROLE       Proxy role: 'agent' (source) or 'sync' (collector)"
            echo "  --server URL      Control server URL"
            echo "  --token TOKEN     Install token (one-time use)"
            echo "  --name NAME       Proxy name (optional)"
            echo "  --skip-kopia      Skip Kopia installation"
            echo "  --help            Show this help"
            echo ""
            echo "Example:"
            echo "  $0 --proxy-id abc-123 --role agent --server https://ctrl.example.com --token xyz789"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$PROXY_ID" ]]; then
    echo -e "${RED}Error: --proxy-id is required${NC}"
    exit 1
fi

if [[ -z "$INSTALL_TOKEN" ]]; then
    echo -e "${RED}Error: --token is required${NC}"
    exit 1
fi

if [[ -z "$SERVER_URL" ]]; then
    echo -e "${RED}Error: --server is required${NC}"
    exit 1
fi

# Validate role
if [[ "$ROLE" != "agent" && "$ROLE" != "sync" ]]; then
    echo -e "${RED}Invalid role: $ROLE. Must be 'agent' or 'sync'${NC}"
    exit 1
fi

# Remove trailing slash from server URL
SERVER_URL="${SERVER_URL%/}"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }

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
        OS_VERSION=$VERSION_ID
    else
        OS="unknown"
        OS_VERSION=""
    fi
    log_info "Detected OS: $OS $OS_VERSION"
}

get_system_info() {
    # Get hostname
    HOSTNAME=$(hostname)
    
    # Get internal IP
    INTERNAL_IP=$(hostname -I | awk '{print $1}')
    
    # Get CPU cores
    CPU_CORES=$(nproc 2>/dev/null || echo "1")
    
    # Get total memory in bytes
    MEMORY_TOTAL=$(awk '/MemTotal/ {print $2*1024}' /proc/meminfo 2>/dev/null || echo "0")
    
    # Get total disk space in bytes (root partition)
    DISK_TOTAL=$(df -B1 / | awk 'NR==2 {print $2}' 2>/dev/null || echo "0")
    
    log_info "System: $CPU_CORES cores, $((MEMORY_TOTAL/1024/1024))MB RAM, $((DISK_TOTAL/1024/1024/1024))GB disk"
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
        KOPIA_VERSION=$(kopia --version 2>/dev/null || echo "unknown")
        log_info "Kopia already installed: $KOPIA_VERSION"
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
            log_warn "Please install Kopia manually from: https://kopia.io/docs/installation/"
            ;;
    esac
    
    if command -v kopia &> /dev/null; then
        log_success "Kopia installed: $(kopia --version)"
    fi
}

download_proxy() {
    log_info "Downloading HyperFileLens proxy..."
    
    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        *) log_error "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    # Download binary (in real scenario, this would download from releases)
    # For now, we assume the binary is already available or built locally
    if [[ ! -f "/usr/local/bin/hyperfilelens-proxy" ]]; then
        log_warn "Proxy binary not found. Please ensure it's installed."
        # In production:
        # curl -sSL "${SERVER_URL}/downloads/proxy-linux-${ARCH}" -o /usr/local/bin/hyperfilelens-proxy
        # chmod +x /usr/local/bin/hyperfilelens-proxy
    fi
}

register_proxy() {
    log_info "Registering proxy with control server..."
    
    # Get Kopia version if installed
    KOPIA_VERSION=""
    if command -v kopia &> /dev/null; then
        KOPIA_VERSION=$(kopia --version 2>/dev/null | head -1 || echo "")
    fi
    
    # Build registration payload
    REGISTER_URL="${SERVER_URL}/api/v1/proxies/register/"
    
    log_info "Calling: $REGISTER_URL"
    
    # Make registration request
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$REGISTER_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"proxy_id\": \"$PROXY_ID\",
            \"install_token\": \"$INSTALL_TOKEN\",
            \"hostname\": \"$HOSTNAME\",
            \"internal_ip\": \"$INTERNAL_IP\",
            \"os\": \"$OS\",
            \"os_version\": \"$OS_VERSION\",
            \"version\": \"$VERSION\",
            \"kopia_version\": \"$KOPIA_VERSION\",
            \"cpu_cores\": $CPU_CORES,
            \"memory_total\": $MEMORY_TOTAL,
            \"disk_total\": $DISK_TOTAL,
            \"capabilities\": {}
        }" 2>> "$LOG_FILE")
    
    HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n -1)
    HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n 1)
    
    if [[ "$HTTP_STATUS" != "200" ]]; then
        log_error "Registration failed (HTTP $HTTP_STATUS)"
        log_error "Response: $HTTP_BODY"
        exit 1
    fi
    
    # Parse response
    API_TOKEN=$(echo "$HTTP_BODY" | grep -o '"api_token":"[^"]*"' | cut -d'"' -f4)
    RETURNED_PROXY_ID=$(echo "$HTTP_BODY" | grep -o '"proxy_id":"[^"]*"' | cut -d'"' -f4)
    RETURNED_NAME=$(echo "$HTTP_BODY" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    RETURNED_ROLE=$(echo "$HTTP_BODY" | grep -o '"role":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -z "$API_TOKEN" ]]; then
        log_error "Failed to get API token from server"
        log_error "Response: $HTTP_BODY"
        exit 1
    fi
    
    log_success "Registration successful!"
    log_info "Proxy ID: $RETURNED_PROXY_ID"
    log_info "Name: $RETURNED_NAME"
    log_info "Role: $RETURNED_ROLE"
}

create_config() {
    log_info "Creating configuration..."
    
    mkdir -p "$PROXY_HOME"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Mount dependencies for sync role
    if [[ "$ROLE" == "sync" ]]; then
        MOUNT_TOOLS=""
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
    
    # Create config file with the api_token we received
    cat > "$PROXY_HOME/config.yaml" << EOF
# HyperFileLens Proxy Configuration
# Auto-generated by installation script
# DO NOT edit api_token manually

version: "${VERSION}"
role: "${ROLE}"

server:
  url: "${SERVER_URL}"
  api_token: "${API_TOKEN}"
  ws_protocol: "$(echo $SERVER_URL | grep -q 'https' && echo 'wss' || echo 'ws')"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  id: "${PROXY_ID}"
  name: "${NAME:-$HOSTNAME}"
  hostname: "${HOSTNAME}"

kopia:
  path: "/usr/bin/kopia"
  cache_path: "/var/lib/hyperfilelens/cache"

mount:
  enabled: $([[ "$ROLE" == "sync" ]] && echo "true" || echo "false")

logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
EOF
    
    # Secure the config file (contains api_token)
    chmod 600 "$PROXY_HOME/config.yaml"
    chown -R "$PROXY_USER:$PROXY_USER" "$PROXY_HOME"
    chown -R "$PROXY_USER:$PROXY_USER" "$(dirname "$LOG_FILE")"
    
    log_success "Configuration created at $PROXY_HOME/config.yaml"
}

create_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${PROXY_SERVICE}.service << EOF
[Unit]
Description=HyperFileLens Proxy (${ROLE})
Documentation=https://docs.hyperfilelens.com
After=network-online.target
Wants=network-online.target

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

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${PROXY_HOME} /var/lib/hyperfilelens /var/log/hyperfilelens

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${PROXY_SERVICE}
    log_success "Service created"
}

start_service() {
    log_info "Starting proxy service..."
    systemctl start ${PROXY_SERVICE}
    
    sleep 2
    
    if systemctl is-active --quiet ${PROXY_SERVICE}; then
        log_success "Service started successfully"
    else
        log_error "Service failed to start"
        journalctl -u ${PROXY_SERVICE} --no-pager -n 20
        exit 1
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Proxy Installed"
    echo "=========================================="
    echo ""
    echo "  Proxy ID:   ${PROXY_ID}"
    echo "  Role:       ${ROLE}"
    echo "  Server:     ${SERVER_URL}"
    echo "  Config:     ${PROXY_HOME}/config.yaml"
    echo ""
    echo "  Commands:"
    echo "    Start:    systemctl start ${PROXY_SERVICE}"
    echo "    Stop:     systemctl stop ${PROXY_SERVICE}"
    echo "    Status:   systemctl status ${PROXY_SERVICE}"
    echo "    Logs:     journalctl -u ${PROXY_SERVICE} -f"
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
    
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log_info "Proxy ID: $PROXY_ID"
    log_info "Role: $ROLE"
    log_info "Server: $SERVER_URL"
    echo ""
    
    check_root
    detect_os
    get_system_info
    create_user
    install_kopia
    download_proxy
    register_proxy
    create_config
    create_service
    start_service
    
    log_success "Installation completed!"
    print_summary
}

main
