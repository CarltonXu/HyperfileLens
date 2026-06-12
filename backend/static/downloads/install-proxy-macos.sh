#!/bin/bash
#
# HyperFileLens Proxy macOS Installation Script
#
# Usage:
#   curl -sSL https://hfl.example.com/downloads/install-proxy-macos.sh | sudo bash -s -- \
#     --proxy-id <uuid> --role agent --server https://control.example.com --token <install_token>
#

set -e

VERSION="1.0.0"
PROXY_HOME="/Library/Application Support/HyperFileLens"
PROXY_SERVICE="com.hyperfilelens.proxy"
LOG_DIR="/Library/Logs/HyperFileLens"
LOG_FILE="${LOG_DIR}/install.log"

PROXY_ID=""
ROLE="agent"
SERVER_URL=""
INSTALL_TOKEN=""
NAME=""
SKIP_KOPIA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --proxy-id) PROXY_ID="$2"; shift 2 ;;
        --role) ROLE="$2"; shift 2 ;;
        --server) SERVER_URL="$2"; shift 2 ;;
        --token) INSTALL_TOKEN="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --skip-kopia) SKIP_KOPIA=true; shift ;;
        --help)
            echo "Usage: $0 --proxy-id ID --role agent --server URL --token TOKEN [--name NAME] [--skip-kopia]"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$PROXY_ID" || -z "$INSTALL_TOKEN" || -z "$SERVER_URL" ]]; then
    echo "Error: --proxy-id, --server and --token are required"
    exit 1
fi

if [[ "$ROLE" != "agent" && "$ROLE" != "sync" ]]; then
    echo "Invalid role: $ROLE. Must be 'agent' or 'sync'"
    exit 1
fi

SERVER_URL="${SERVER_URL%/}"

log_info() { echo "[INFO] $1" | tee -a "$LOG_FILE"; }
log_success() { echo "[SUCCESS] $1" | tee -a "$LOG_FILE"; }
log_error() { echo "[ERROR] $1" | tee -a "$LOG_FILE"; }
log_warn() { echo "[WARN] $1" | tee -a "$LOG_FILE"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with sudo"
        exit 1
    fi
}

detect_system() {
    OS="macos"
    OS_VERSION="$(sw_vers -productVersion 2>/dev/null || echo "")"
    HOSTNAME="$(hostname)"
    INTERNAL_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")"
    CPU_CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo "1")"
    MEMORY_TOTAL="$(sysctl -n hw.memsize 2>/dev/null || echo "0")"
    DISK_TOTAL="$(df -k / | awk 'NR==2 {print $2 * 1024}' 2>/dev/null || echo "0")"
    log_info "Detected macOS ${OS_VERSION}"
}

install_kopia() {
    if [[ "$SKIP_KOPIA" == "true" ]]; then
        log_info "Skipping Kopia installation"
        return
    fi

    if command -v kopia >/dev/null 2>&1; then
        log_info "Kopia already installed: $(kopia --version 2>/dev/null || echo installed)"
        return
    fi

    if command -v brew >/dev/null 2>&1; then
        log_info "Installing Kopia with Homebrew"
        brew install kopia || log_warn "Kopia installation failed. Install it manually if backup tasks need it."
    else
        log_warn "Homebrew is not installed. Install Kopia manually from https://kopia.io/docs/installation/"
    fi
}

download_proxy() {
    log_info "Downloading HyperFileLens proxy..."

    ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64) ARCH="amd64" ;;
        arm64) ARCH="arm64" ;;
        *) log_error "Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    PACKAGE_URL="${SERVER_URL}/downloads/packages/proxy/hyperfilelens-proxy-darwin-${ARCH}.tar.gz"
    LEGACY_URL="${SERVER_URL}/downloads/packages/proxy/hyperfilelens-proxy-darwin-${ARCH}"
    TMP_DIR="$(mktemp -d)"

    if curl -sSL --fail "$PACKAGE_URL" | tar xz -C "$TMP_DIR"; then
        if [[ -f "$TMP_DIR/hyperfilelens-proxy" ]]; then
            install -m 0755 "$TMP_DIR/hyperfilelens-proxy" /usr/local/bin/hyperfilelens-proxy
        elif [[ -f "$TMP_DIR/hyperfilelens-proxy-darwin-${ARCH}" ]]; then
            install -m 0755 "$TMP_DIR/hyperfilelens-proxy-darwin-${ARCH}" /usr/local/bin/hyperfilelens-proxy
        else
            log_error "Proxy package does not contain hyperfilelens-proxy binary"
            exit 1
        fi
    elif curl -sSL --fail "$LEGACY_URL" -o /usr/local/bin/hyperfilelens-proxy; then
        chmod +x /usr/local/bin/hyperfilelens-proxy
    else
        log_error "Failed to download proxy package from $PACKAGE_URL"
        exit 1
    fi

    rm -rf "$TMP_DIR"
    log_success "Proxy binary installed"
}

register_proxy() {
    log_info "Registering proxy with control server..."

    KOPIA_VERSION=""
    if command -v kopia >/dev/null 2>&1; then
        KOPIA_VERSION="$(kopia --version 2>/dev/null | head -1 || echo "")"
    fi

    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${SERVER_URL}/api/v1/proxies/register/" \
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

    HTTP_BODY="$(printf '%s\n' "$HTTP_RESPONSE" | sed '$d')"
    HTTP_STATUS="$(printf '%s\n' "$HTTP_RESPONSE" | tail -n 1)"

    if [[ "$HTTP_STATUS" != "200" ]]; then
        log_error "Registration failed (HTTP $HTTP_STATUS): $HTTP_BODY"
        exit 1
    fi

    API_TOKEN="$(echo "$HTTP_BODY" | sed -n 's/.*"api_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    if [[ -z "$API_TOKEN" ]]; then
        log_error "Failed to get API token from server: $HTTP_BODY"
        exit 1
    fi

    log_success "Registration successful"
}

create_config() {
    mkdir -p "$PROXY_HOME" "$LOG_DIR"

    cat > "${PROXY_HOME}/config.yaml" << EOF
version: "${VERSION}"
role: "${ROLE}"

server:
  url: "${SERVER_URL}"
  api_token: ""
  ws_protocol: "$(echo "$SERVER_URL" | grep -q '^https' && echo 'wss' || echo 'ws')"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  id: "${PROXY_ID}"
  name: "${NAME:-$HOSTNAME}"
  hostname: "${HOSTNAME}"
  install_token: "${INSTALL_TOKEN}"

kopia:
  path: "$(command -v kopia || echo /usr/local/bin/kopia)"
  cache_path: "${PROXY_HOME}/cache"

mount:
  enabled: false

logging:
  level: "info"
  file: "${LOG_DIR}/proxy.log"
EOF

    chmod 600 "${PROXY_HOME}/config.yaml"
    log_success "Configuration created at ${PROXY_HOME}/config.yaml"
}

create_service() {
    log_info "Creating launchd service..."

    cat > "/Library/LaunchDaemons/${PROXY_SERVICE}.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PROXY_SERVICE}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/hyperfilelens-proxy</string>
    <string>--config</string>
    <string>${PROXY_HOME}/config.yaml</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROXY_HOME}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/proxy.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/proxy.err.log</string>
  <key>ProcessType</key>
  <string>Background</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key>
    <string>${PROXY_HOME}</string>
    <key>XDG_CACHE_HOME</key>
    <string>${PROXY_HOME}/cache</string>
    <key>KOPIA_CACHE_DIR</key>
    <string>${PROXY_HOME}/cache</string>
    <key>CONFIG_PATH</key>
    <string>${PROXY_HOME}/config.yaml</string>
  </dict>
</dict>
</plist>
EOF

    chmod 644 "/Library/LaunchDaemons/${PROXY_SERVICE}.plist"
    launchctl bootout system "/Library/LaunchDaemons/${PROXY_SERVICE}.plist" >/dev/null 2>&1 || true
    launchctl bootstrap system "/Library/LaunchDaemons/${PROXY_SERVICE}.plist"
    launchctl enable "system/${PROXY_SERVICE}"
    log_success "launchd service created (HOME / XDG_CACHE_HOME / KOPIA_CACHE_DIR injected)"
}

main() {
    mkdir -p "$LOG_DIR"
    check_root
    detect_system
    install_kopia
    download_proxy
    create_config
    create_service
    log_success "HyperFileLens proxy installed"
    echo "Status: sudo launchctl print system/${PROXY_SERVICE}"
    echo "Logs: tail -f ${LOG_DIR}/proxy.log"
}

main
