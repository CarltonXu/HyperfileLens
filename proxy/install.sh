#!/bin/bash
#
# HyperFileLens Proxy Installation Script
#
# This script installs the HyperFileLens proxy with role-based configuration.
#
# Usage:
#   curl -sSL https://hfl.example.com/downloads/install-proxy.sh | bash -s -- \
#     --proxy-id <uuid> \
#     --role agent \
#     --server https://control.example.com \
#     --token <install_token>
#
# Flow:
#   1. Install dependencies (Kopia, mount tools for sync)
#   2. Save configuration with proxy_id and install_token
#   3. Start the proxy service; the proxy registers itself on first run
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
KOPIA_PATH="kopia"

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
        KOPIA_PATH=$(command -v kopia)
        KOPIA_VERSION=$("$KOPIA_PATH" --version 2>/dev/null || echo "unknown")
        log_info "Kopia already installed: $KOPIA_VERSION"
        return
    fi
    
    log_info "Installing Kopia..."
    
    # Detect architecture
    KOPIA_ARCH=$(uname -m)
    case $KOPIA_ARCH in
        x86_64) KOPIA_ARCH="amd64" ;;
        aarch64) KOPIA_ARCH="arm64" ;;
        *) log_error "Unsupported architecture for Kopia: $KOPIA_ARCH"; exit 1 ;;
    esac
    
    # Use HyperFileLens control server for offline/internal deployments.
    KOPIA_VERSION="0.22.3"
    KOPIA_DEB="kopia_${KOPIA_VERSION}_linux_${KOPIA_ARCH}.deb"
    KOPIA_URL="${SERVER_URL}/downloads/packages/kopia/${KOPIA_DEB}"
    
    case $OS in
        ubuntu|debian)
            log_info "Downloading Kopia from HyperFileLens control server..."
            if curl -sSL --fail "$KOPIA_URL" -o /tmp/$KOPIA_DEB; then
                dpkg -i /tmp/$KOPIA_DEB || apt-get install -f -y || {
                    rm -f /tmp/$KOPIA_DEB
                    log_error "Failed to install Kopia package: /tmp/$KOPIA_DEB"
                    exit 1
                }
                rm -f /tmp/$KOPIA_DEB
            else
                log_warn "Failed to download Kopia from control server: $KOPIA_URL"
                log_warn "Trying apt fallback..."
                # Fallback to apt if available
                apt-get update && apt-get install -y kopia 2>/dev/null || {
                    log_error "Kopia installation failed. Ensure the control server exposes $KOPIA_URL or install Kopia manually before running this script."
                    exit 1
                }
            fi
            ;;
        centos|rhel|rocky|almalinux)
            log_info "Downloading Kopia RPM from HyperFileLens control server..."
            KOPIA_RPM="kopia-${KOPIA_VERSION}.x86_64.rpm"
            KOPIA_RPM_URL="${SERVER_URL}/downloads/packages/kopia/${KOPIA_RPM}"
            if curl -sSL --fail "$KOPIA_RPM_URL" -o /tmp/$KOPIA_RPM; then
                yum localinstall -y /tmp/$KOPIA_RPM || rpm -i /tmp/$KOPIA_RPM || {
                    rm -f /tmp/$KOPIA_RPM
                    log_error "Failed to install Kopia package: /tmp/$KOPIA_RPM"
                    exit 1
                }
                rm -f /tmp/$KOPIA_RPM
            else
                log_error "Failed to download Kopia from control server: $KOPIA_RPM_URL"
                log_error "Install Kopia manually before running this script, or publish the RPM package on the control server."
                exit 1
            fi
            ;;
        *)
            log_error "Unsupported OS for automatic Kopia installation: $OS"
            log_error "Install Kopia manually from https://kopia.io/docs/installation/ before running this script."
            exit 1
            ;;
    esac
    
    if command -v kopia &> /dev/null; then
        KOPIA_PATH=$(command -v kopia)
        log_success "Kopia installed: $("$KOPIA_PATH" --version)"
    else
        KOPIA_PATH="kopia"
        log_error "Kopia installation failed. Aborting proxy installation."
        exit 1
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
    
    # Detect OS
    OS_TYPE=$(uname -s | tr '[:upper:]' '[:lower:]')
    
    # Build standard package URL. Nginx/Ingress should expose this under the
    # public control-plane URL:
    #   /downloads/packages/proxy/hyperfilelens-proxy-<os>-<arch>.tar.gz
    BINARY_NAME="hyperfilelens-proxy-${OS_TYPE}-${ARCH}"
    PACKAGE_URL="${SERVER_URL}/downloads/packages/proxy/${BINARY_NAME}.tar.gz"
    LEGACY_DOWNLOAD_URL="${SERVER_URL}/downloads/packages/proxy/${BINARY_NAME}"

    log_info "Downloading from: $PACKAGE_URL"

    TMP_DIR="$(mktemp -d)"
    if curl -sSL --fail "$PACKAGE_URL" | tar xz -C "$TMP_DIR"; then
        if [[ -f "$TMP_DIR/hyperfilelens-proxy" ]]; then
            install -m 0755 "$TMP_DIR/hyperfilelens-proxy" /usr/local/bin/hyperfilelens-proxy
        elif [[ -f "$TMP_DIR/${BINARY_NAME}" ]]; then
            install -m 0755 "$TMP_DIR/${BINARY_NAME}" /usr/local/bin/hyperfilelens-proxy
        else
            log_error "Proxy package does not contain hyperfilelens-proxy binary"
            exit 1
        fi
        rm -rf "$TMP_DIR"
        log_success "Proxy package installed: $(/usr/local/bin/hyperfilelens-proxy --version 2>/dev/null || echo 'installed')"
    elif curl -sSL --fail "$LEGACY_DOWNLOAD_URL" -o /usr/local/bin/hyperfilelens-proxy; then
        rm -rf "$TMP_DIR"
        chmod +x /usr/local/bin/hyperfilelens-proxy
        log_success "Proxy binary downloaded: $(/usr/local/bin/hyperfilelens-proxy --version 2>/dev/null || echo 'installed')"
    else
        rm -rf "$TMP_DIR"
        log_error "Failed to download proxy package from $PACKAGE_URL"
        log_error "Please check if the server URL is correct and the package exists"
        exit 1
    fi
}

register_proxy() {
    log_info "Registering proxy with control server..."
    
    # Get Kopia version if installed
    KOPIA_VERSION=""
    if command -v kopia &> /dev/null; then
        KOPIA_PATH=$(command -v kopia)
        KOPIA_VERSION=$("$KOPIA_PATH" --version 2>/dev/null | head -1 || echo "")
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
    
    HTTP_BODY=$(printf '%s\n' "$HTTP_RESPONSE" | sed '$d')
    HTTP_STATUS=$(printf '%s\n' "$HTTP_RESPONSE" | tail -n 1)
    
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
    mkdir -p /var/lib/hyperfilelens/cache /var/lib/hyperfilelens/tmp
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
    
    # Create config file. The proxy daemon registers itself on first run and
    # persists server.api_token after registration succeeds.
    cat > "$PROXY_HOME/config.yaml" << EOF
# HyperFileLens Proxy Configuration
# Auto-generated by installation script

version: "${VERSION}"
role: "${ROLE}"

server:
  url: "${SERVER_URL}"
  api_token: ""
  ws_protocol: "$(echo $SERVER_URL | grep -q 'https' && echo 'wss' || echo 'ws')"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  id: "${PROXY_ID}"
  name: "${NAME:-$HOSTNAME}"
  hostname: "${HOSTNAME}"
  install_token: "${INSTALL_TOKEN}"

kopia:
  path: "${KOPIA_PATH}"
  cache_path: "/var/lib/hyperfilelens/cache"

mount:
  enabled: $([[ "$ROLE" == "sync" ]] && echo "true" || echo "false")

logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
EOF
    
    # Secure the config file (contains the install token until registration)
    chmod 600 "$PROXY_HOME/config.yaml"
    chown -R "$PROXY_USER:$PROXY_USER" "$PROXY_HOME"
    chown -R "$PROXY_USER:$PROXY_USER" /var/lib/hyperfilelens
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
    create_config
    create_service
    start_service
    
    log_success "Installation completed!"
    print_summary
}

main
