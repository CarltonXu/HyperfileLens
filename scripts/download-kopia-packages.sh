#!/usr/bin/env bash

set -euo pipefail

KOPIA_VERSION="${KOPIA_VERSION:-0.22.3}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${KOPIA_OUTPUT_DIR:-${ROOT_DIR}/backend/static/downloads/packages/kopia}"
BASE_URL="${KOPIA_DOWNLOAD_BASE_URL:-https://github.com/kopia/kopia/releases/download/v${KOPIA_VERSION}}"

mkdir -p "$OUTPUT_DIR"

download() {
  local filename="$1"
  local url="${BASE_URL}/${filename}"
  local target="${OUTPUT_DIR}/${filename}"

  if [[ -s "$target" ]]; then
    echo "Kopia package exists: $target"
    return
  fi

  echo "Downloading Kopia package: $url"
  curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o "${target}.tmp" "$url"
  mv "${target}.tmp" "$target"
}

download "kopia_${KOPIA_VERSION}_linux_amd64.deb"
download "kopia-${KOPIA_VERSION}.x86_64.rpm"

echo "Kopia packages ready in: $OUTPUT_DIR"
