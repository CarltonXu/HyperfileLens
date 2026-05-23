#!/usr/bin/env bash
#
# HyperFileLens component uninstaller.
#
# Usage:
#   curl -sSL https://hfl.example.com/downloads/uninstall.sh | bash -s -- --component gateway
#   curl -sSL https://hfl.example.com/downloads/uninstall.sh | bash -s -- --component proxy --purge
#   curl -sSL https://hfl.example.com/downloads/uninstall.sh | bash -s -- --component all --purge --remove-user

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPONENT=""
PURGE=false
REMOVE_USER=false
REMOVE_KOPIA=false
YES=false

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
  cat <<'EOF'
HyperFileLens Uninstaller

Options:
  --component proxy|gateway|all  Component to uninstall (required)
  --purge                        Also remove config, data, and logs for the selected component
  --remove-user                  Remove the hyperfilelens system user if unused
  --remove-kopia                 Remove the kopia binary/package if installed
  -y, --yes                      Do not prompt before destructive purge operations
  --help                         Show this help

Default behavior preserves configuration, data, and logs.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --component)
      COMPONENT="$2"
      shift 2
      ;;
    --purge)
      PURGE=true
      shift
      ;;
    --remove-user)
      REMOVE_USER=true
      shift
      ;;
    --remove-kopia)
      REMOVE_KOPIA=true
      shift
      ;;
    -y|--yes)
      YES=true
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    log_error "This script must be run as root."
    exit 1
  fi
}

validate_component() {
  case "$COMPONENT" in
    proxy|gateway|all)
      ;;
    "")
      log_error "--component is required."
      usage
      exit 1
      ;;
    *)
      log_error "Invalid component: $COMPONENT"
      usage
      exit 1
      ;;
  esac
}

confirm_purge() {
  if [[ "$PURGE" != "true" ]] || [[ "$YES" == "true" ]]; then
    return
  fi
  echo ""
  log_warn "Purge mode will remove configuration, data, and logs for component: ${COMPONENT}"
  if [[ -r /dev/tty ]]; then
    read -r -p "Continue? [y/N] " answer < /dev/tty
  else
    log_error "No interactive terminal available for confirmation. Re-run with --yes to confirm purge."
    exit 1
  fi
  case "$answer" in
    y|Y|yes|YES)
      ;;
    *)
      log_info "Canceled."
      exit 0
      ;;
  esac
}

stop_disable_service() {
  local service="$1"
  if systemctl list-unit-files "${service}.service" >/dev/null 2>&1 || [[ -f "/etc/systemd/system/${service}.service" ]]; then
    log_info "Stopping ${service}.service"
    systemctl stop "${service}.service" >/dev/null 2>&1 || true
    log_info "Disabling ${service}.service"
    systemctl disable "${service}.service" >/dev/null 2>&1 || true
  fi
  rm -f "/etc/systemd/system/${service}.service"
}

remove_path() {
  local path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    log_info "Removing ${path}"
    rm -rf "$path"
  fi
}

unmount_under() {
  local base="$1"
  if ! command -v findmnt >/dev/null 2>&1; then
    return
  fi
  if [[ ! -d "$base" ]]; then
    return
  fi
  findmnt -Rnr -o TARGET "$base" 2>/dev/null | sort -r | while read -r target; do
    if [[ -n "$target" ]]; then
      log_info "Unmounting ${target}"
      umount "$target" >/dev/null 2>&1 || fusermount3 -u "$target" >/dev/null 2>&1 || fusermount -u "$target" >/dev/null 2>&1 || true
    fi
  done
}

uninstall_proxy() {
  log_info "Uninstalling HyperFileLens proxy"
  stop_disable_service "hyperfilelens-proxy"
  remove_path "/usr/local/bin/hyperfilelens-proxy"

  if [[ "$PURGE" == "true" ]]; then
    remove_path "/opt/hyperfilelens/config.yaml"
    remove_path "/var/lib/hyperfilelens/cache"
    remove_path "/var/lib/hyperfilelens/tmp"
    remove_path "/var/lib/hyperfilelens/node_id"
    remove_path "/var/log/hyperfilelens/proxy.log"
    remove_path "/var/log/hyperfilelens/install.log"
  else
    log_info "Preserved proxy config/data/logs. Use --purge to remove them."
  fi
}

uninstall_gateway() {
  log_info "Uninstalling HyperFileLens gateway"
  stop_disable_service "hyperfilelens-gateway"
  unmount_under "/mnt/kopia"

  remove_path "/opt/hyperfilelens/gateway"

  if [[ "$PURGE" == "true" ]]; then
    remove_path "/etc/hyperfilelens/gateway"
    remove_path "/var/lib/hyperfilelens/repository"
    remove_path "/var/lib/hyperfilelens/index"
    remove_path "/var/log/hyperfilelens/gateway.log"
  else
    log_info "Preserved gateway config/data/logs. Use --purge to remove them."
  fi
}

remove_empty_common_dirs() {
  rmdir /etc/hyperfilelens 2>/dev/null || true
  rmdir /opt/hyperfilelens 2>/dev/null || true
  rmdir /var/lib/hyperfilelens 2>/dev/null || true
  rmdir /var/log/hyperfilelens 2>/dev/null || true
}

remove_hyperfilelens_user() {
  if [[ "$REMOVE_USER" != "true" ]]; then
    return
  fi
  if id hyperfilelens >/dev/null 2>&1; then
    if pgrep -u hyperfilelens >/dev/null 2>&1; then
      log_warn "User hyperfilelens still has running processes; not removing user."
      return
    fi
    log_info "Removing user hyperfilelens"
    userdel hyperfilelens >/dev/null 2>&1 || true
  fi
}

remove_kopia() {
  if [[ "$REMOVE_KOPIA" != "true" ]]; then
    return
  fi
  log_info "Removing Kopia"
  if command -v apt-get >/dev/null 2>&1; then
    apt-get remove -y kopia >/dev/null 2>&1 || true
  elif command -v yum >/dev/null 2>&1; then
    yum remove -y kopia >/dev/null 2>&1 || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y kopia >/dev/null 2>&1 || true
  fi
  remove_path "/usr/bin/kopia"
  remove_path "/usr/local/bin/kopia"
}

main() {
  require_root
  validate_component
  confirm_purge

  case "$COMPONENT" in
    proxy)
      uninstall_proxy
      ;;
    gateway)
      uninstall_gateway
      ;;
    all)
      uninstall_proxy
      uninstall_gateway
      ;;
  esac

  systemctl daemon-reload >/dev/null 2>&1 || true
  remove_kopia
  remove_hyperfilelens_user
  remove_empty_common_dirs

  log_success "Uninstall completed for component: ${COMPONENT}"
}

main
