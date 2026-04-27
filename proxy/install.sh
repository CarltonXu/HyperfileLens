#!/bin/bash
#
# HyperFileLens Proxy Installation Script
#
# This script installs and configures the HyperFileLens proxy
# on source and target nodes.
#
# Usage:
#   curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash
#   curl -sSL https://get.hyperfilelens.com/install-proxy.sh | bash -s -- --type source --server https://control.hyperfilelens.com --token <token>
#

set -e

# Configuration
PROXY_VERSION="1.0.0"
PROXY_HOME="/opt/hyperfilelens"
PROXY_USER="hyperfilelens"
PROXY_SERVICE="hyperfilelens-proxy"
LOG_FILE="/var/log/hyperfilelens/install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
AGENT_TYPE=""
SERVER_URL=""
API_TOKEN=""
SKIP_DEPENDENCIES=false
FORCE_REINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            AGENT_TYPE="$2"
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
        --skip-deps)
            SKIP_DEPENDENCIES=true
            shift
            ;;
        --force)
            FORCE_REINSTALL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --type TYPE           Proxy type: 'source' or 'target'"
            echo "  --server URL          Control server URL"
            echo "  --token TOKEN         API token for authentication"
            echo "  --skip-deps           Skip dependency installation"
            echo "  --force               Force reinstallation"
            echo "  --help                Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

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
        VERSION=$VERSION_ID
    elif [[ -f /etc/redhat-release ]]; then
        if grep -q "CentOS" /etc/redhat-release; then
            OS="centos"
        elif grep -q "Red Hat" /etc/redhat-release; then
            OS="rhel"
        fi
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
    else
        OS="unknown"
    fi
    
    log_info "Detected OS: $OS"
}

detect_arch() {
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            ARCH_NAME="amd64"
            ;;
        aarch64|arm64)
            ARCH_NAME="arm64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    log_info "Detected architecture: $ARCH_NAME"
}

check_dependencies() {
    if [[ "$SKIP_DEPENDENCIES" == "true" ]]; then
        log_info "Skipping dependency check"
        return
    fi
    
    log_info "Checking dependencies..."
    
    # Check for required commands
    local missing_deps=()
    
    for cmd in curl tar systemctl; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_deps[*]}"
        log_info "Install them with:"
        case $OS in
            ubuntu|debian)
                echo "  apt-get update && apt-get install -y ${missing_deps[*]}"
                ;;
            centos|rhel|rocky|almalinux)
                echo "  yum install -y ${missing_deps[*]}"
                ;;
            *)
                echo "  Install ${missing_deps[*]} using your package manager"
                ;;
        esac
        exit 1
    fi
    
    log_success "All dependencies satisfied"
}

create_log_directory() {
    mkdir -p $(dirname "$LOG_FILE")
    touch "$LOG_FILE"
    log_info "Log file: $LOG_FILE"
}

create_user() {
    if id "$PROXY_USER" &>/dev/null; then
        log_info "User $PROXY_USER already exists"
    else
        useradd -r -s /bin/false -d "$PROXY_HOME" -c "HyperFileLens Proxy" "$PROXY_USER"
        log_info "Created user: $PROXY_USER"
    fi
}

install_kopia() {
    log_info "Checking Kopia installation..."
    
    if command -v kopia &> /dev/null; then
        KOPIA_VERSION=$(kopia --version 2>/dev/null || echo "unknown")
        log_info "Kopia already installed: $KOPIA_VERSION"
        return
    fi
    
    log_info "Installing Kopia..."
    
    # Install Kopia based on OS
    case $OS in
        ubuntu|debian)
            curl -sSL https://kopia.io/signing-key | gpg --dearmor -o /usr/share/keyrings/kopia-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/kopia-keyring.gpg] https://kopia.io/apt stable main" > /etc/apt/sources.list.d/kopia.list
            apt-get update
            apt-get install -y kopia
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
            log_warning "Could not install Kopia automatically for $OS"
            log_info "Please install Kopia manually from: https://kopia.io/docs/installation/"
            ;;
    esac
    
    if command -v kopia &> /dev/null; then
        log_success "Kopia installed successfully"
    else
        log_warning "Kopia installation may have failed. Please verify manually."
    fi
}

download_proxy() {
    log_info "Downloading HyperFileLens Proxy v${PROXY_VERSION}..."
    
    local download_url="${SERVER_URL:-https://releases.hyperfilelens.com}/proxies/${PROXY_VERSION}/hyperfilelens-proxy-${PROXY_VERSION}-linux-${ARCH_NAME}.tar.gz"
    
    # Create temporary directory
    local temp_dir=$(mktemp -d)
    local archive_file="$temp_dir/proxy.tar.gz"
    
    trap "rm -rf $temp_dir" EXIT
    
    # Download proxy binary
    if curl -fSL -o "$archive_file" "$download_url" 2>/dev/null; then
        log_info "Downloaded proxy from: $download_url"
    else
        # Try local build
        log_warning "Could not download proxy binary, attempting local build..."
        
        # Check if Go is installed
        if ! command -v go &> /dev/null; then
            log_error "Go is not installed. Cannot build proxy locally."
            log_info "Please install Go or download the proxy binary manually."
            exit 1
        fi
        
        # Build locally
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [[ -f "$script_dir/main.go" ]]; then
            log_info "Building proxy from source..."
            mkdir -p "$PROXY_HOME/bin"
            cd "$script_dir"
            go build -o "$PROXY_HOME/bin/hyperfilelens-proxy" .
            log_success "Proxy built successfully"
        else
            log_error "Proxy source not found. Cannot build."
            exit 1
        fi
    fi
    
    if [[ -f "$archive_file" ]]; then
        # Extract proxy
        log_info "Extracting proxy..."
        mkdir -p "$PROXY_HOME"
        tar -xzf "$archive_file" -C "$PROXY_HOME"
    fi
    
    # Set permissions
    chown -R "$PROXY_USER:$PROXY_USER" "$PROXY_HOME"
    chmod +x "$PROXY_HOME/bin/hyperfilelens-proxy" 2>/dev/null || true
    
    log_success "Proxy installed to: $PROXY_HOME"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${PROXY_SERVICE}.service << EOF
[Unit]
Description=HyperFileLens Proxy
After=network.target

[Service]
Type=simple
User=$PROXY_USER
Group=$PROXY_USER
WorkingDirectory=$PROXY_HOME
ExecStart=$PROXY_HOME/bin/hyperfilelens-proxy
Restart=on-failure
RestartSec=10

# Environment variables
Environment=PROXY_HOME=$PROXY_HOME
Environment=SERVER_URL=${SERVER_URL:-http://localhost:8000}
Environment=API_TOKEN=${API_TOKEN:-}
Environment=AGENT_TYPE=${AGENT_TYPE:-source}
Environment=CONFIG_PATH=$PROXY_HOME/config.yaml

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hyperfilelens-proxy

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log_success "Systemd service created"
}

create_config() {
    log_info "Creating configuration file..."
    
    cat > "$PROXY_HOME/config.yaml" << EOF
# HyperFileLens Proxy Configuration
version: "${PROXY_VERSION}"

# Server connection
server:
  url: "${SERVER_URL:-http://localhost:8000}"
  api_token: "${API_TOKEN:-}"
  ws_protocol: "ws"
  reconnect_delay: 5s
  heartbeat_interval: 30s

# Agent settings
agent:
  type: "${AGENT_TYPE:-source}"
  name: ""
  hostname: "$(hostname -f 2>/dev/null || hostname)"
  
# Backup settings (for source nodes)
backup:
  data_path: "/var/lib/hyperfilelens/data"
  temp_path: "/tmp/hyperfilelens"
  max_concurrent_backups: 2
  kopia_path: "/usr/bin/kopia"

# Logging
logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
  max_size: "100MB"
  max_backups: 5

# Performance
performance:
  worker_threads: 4
  buffer_size: 8192
  compression: true
EOF
    
    chown "$PROXY_USER:$PROXY_USER" "$PROXY_HOME/config.yaml"
    log_success "Configuration file created"
}

start_proxy() {
    log_info "Starting HyperFileLens Proxy..."
    
    systemctl enable ${PROXY_SERVICE}
    systemctl start ${PROXY_SERVICE}
    
    sleep 2
    
    if systemctl is-active --quiet ${PROXY_SERVICE}; then
        log_success "Proxy started successfully"
        systemctl status ${PROXY_SERVICE} --no-pager
    else
        log_error "Failed to start proxy"
        log_info "Check logs with: journalctl -u ${PROXY_SERVICE} -f"
        exit 1
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Proxy Installation"
    echo "=========================================="
    echo ""
    echo "Proxy Type: ${AGENT_TYPE:-source}"
    echo "Server URL: ${SERVER_URL:-http://localhost:8000}"
    echo "Install Path: $PROXY_HOME"
    echo "Log File: /var/log/hyperfilelens/proxy.log"
    echo ""
    echo "Useful Commands:"
    echo "  Start proxy:    systemctl start ${PROXY_SERVICE}"
    echo "  Stop proxy:     systemctl stop ${PROXY_SERVICE}"
    echo "  Restart proxy:  systemctl restart ${PROXY_SERVICE}"
    echo "  View logs:      journalctl -u ${PROXY_SERVICE} -f"
    echo "  Check status:   systemctl status ${PROXY_SERVICE}"
    echo ""
    echo "Configuration file: $PROXY_HOME/config.yaml"
    echo ""
    echo "=========================================="
    echo ""
}

# Main installation process
main() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Proxy Installer"
    echo "  Version: ${PROXY_VERSION}"
    echo "=========================================="
    echo ""
    
    check_root
    detect_os
    detect_arch
    create_log_directory
    check_dependencies
    create_user
    install_kopia
    download_proxy
    create_config
    create_systemd_service
    start_proxy
    
    log_success "Installation completed!"
    print_summary
}

# Run main function
main
