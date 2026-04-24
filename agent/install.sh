#!/bin/bash
#
# HyperFileLens Agent Installation Script
#
# This script installs and configures the HyperFileLens proxy agent
# on source and target nodes.
#
# Usage:
#   curl -sSL https://get.hyperfilelens.com/install.sh | bash
#   curl -sSL https://get.hyperfilelens.com/install.sh | bash -s -- --type source --server https://control.hyperfilelens.com --token <token>
#

set -e

# Configuration
AGENT_VERSION="1.0.0"
AGENT_HOME="/opt/hyperfilelens"
AGENT_USER="hyperfilelens"
AGENT_SERVICE="hyperfilelens-agent"
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
            echo "  --type TYPE           Agent type: 'source' or 'target'"
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
    if id "$AGENT_USER" &>/dev/null; then
        log_info "User $AGENT_USER already exists"
    else
        useradd -r -s /bin/false -d "$AGENT_HOME" -c "HyperFileLens Agent" "$AGENT_USER"
        log_info "Created user: $AGENT_USER"
    fi
}

download_agent() {
    log_info "Downloading HyperFileLens Agent v${AGENT_VERSION}..."
    
    local download_url="${SERVER_URL:-https://releases.hyperfilelens.com}/agents/${AGENT_VERSION}/hyperfilelens-agent-${AGENT_VERSION}-linux-${ARCH_NAME}.tar.gz"
    
    # Create temporary directory
    local temp_dir=$(mktemp -d)
    local archive_file="$temp_dir/agent.tar.gz"
    
    trap "rm -rf $temp_dir" EXIT
    
    # Download agent
    if curl -fSL -o "$archive_file" "$download_url"; then
        log_info "Downloaded agent from: $download_url"
    else
        log_error "Failed to download agent"
        log_info "Please check your server URL or download the agent manually"
        exit 1
    fi
    
    # Extract agent
    log_info "Extracting agent..."
    mkdir -p "$AGENT_HOME"
    tar -xzf "$archive_file" -C "$AGENT_HOME"
    
    # Set permissions
    chown -R "$AGENT_USER:$AGENT_USER" "$AGENT_HOME"
    
    log_success "Agent extracted to: $AGENT_HOME"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${AGENT_SERVICE}.service << EOF
[Unit]
Description=HyperFileLens Agent
After=network.target

[Service]
Type=simple
User=$AGENT_USER
Group=$AGENT_USER
WorkingDirectory=$AGENT_HOME
ExecStart=$AGENT_HOME/bin/agent start
ExecStop=$AGENT_HOME/bin/agent stop
Restart=on-failure
RestartSec=10

# Environment variables
Environment=AGENT_HOME=$AGENT_HOME
Environment=SERVER_URL=${SERVER_URL:-http://localhost:8000}
Environment=API_TOKEN=${API_TOKEN:-}
Environment=AGENT_TYPE=${AGENT_TYPE:-source}

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hyperfilelens-agent

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log_success "Systemd service created"
}

create_config() {
    log_info "Creating configuration file..."
    
    cat > "$AGENT_HOME/config.yaml" << EOF
# HyperFileLens Agent Configuration
version: "${AGENT_VERSION}"

# Server connection
server:
  url: "${SERVER_URL:-http://localhost:8000}"
  api_token: "${API_TOKEN:-}"
  ws_protocol: "wss"
  reconnect_delay: 5
  heartbeat_interval: 30

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
  kopia_path: "/usr/local/bin/kopia"

# Logging
logging:
  level: "info"
  file: "/var/log/hyperfilelens/agent.log"
  max_size: "100MB"
  max_backups: 5

# Performance
performance:
  worker_threads: 4
  buffer_size: 8192
  compression: true
EOF
    
    chown "$AGENT_USER:$AGENT_USER" "$AGENT_HOME/config.yaml"
    log_success "Configuration file created"
}

start_agent() {
    log_info "Starting HyperFileLens Agent..."
    
    systemctl enable ${AGENT_SERVICE}
    systemctl start ${AGENT_SERVICE}
    
    sleep 2
    
    if systemctl is-active --quiet ${AGENT_SERVICE}; then
        log_success "Agent started successfully"
        systemctl status ${AGENT_SERVICE} --no-pager
    else
        log_error "Failed to start agent"
        log_info "Check logs with: journalctl -u ${AGENT_SERVICE} -f"
        exit 1
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Agent Installation"
    echo "=========================================="
    echo ""
    echo "Agent Type: ${AGENT_TYPE:-source}"
    echo "Server URL: ${SERVER_URL:-http://localhost:8000}"
    echo "Install Path: $AGENT_HOME"
    echo "Log File: /var/log/hyperfilelens/agent.log"
    echo ""
    echo "Useful Commands:"
    echo "  Start agent:    systemctl start ${AGENT_SERVICE}"
    echo "  Stop agent:     systemctl stop ${AGENT_SERVICE}"
    echo "  Restart agent:  systemctl restart ${AGENT_SERVICE}"
    echo "  View logs:      journalctl -u ${AGENT_SERVICE} -f"
    echo "  Check status:   systemctl status ${AGENT_SERVICE}"
    echo ""
    echo "Configuration file: $AGENT_HOME/config.yaml"
    echo ""
    echo "=========================================="
    echo ""
}

# Main installation process
main() {
    echo ""
    echo "=========================================="
    echo "  HyperFileLens Agent Installer"
    echo "  Version: ${AGENT_VERSION}"
    echo "=========================================="
    echo ""
    
    check_root
    detect_os
    detect_arch
    create_log_directory
    check_dependencies
    create_user
    download_agent
    create_config
    create_systemd_service
    start_agent
    
    log_success "Installation completed!"
    print_summary
}

# Run main function
main
