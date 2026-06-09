#!/usr/bin/env bash

set -euo pipefail

KOPIA_VERSION="${KOPIA_VERSION:-0.22.3}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${KOPIA_OUTPUT_DIR:-${ROOT_DIR}/backend/static/downloads/packages/kopia}"
LOCAL_PACKAGE_DIR="${KOPIA_LOCAL_PACKAGE_DIR:-${ROOT_DIR}/local-packages/kopia}"
BASE_URL="${KOPIA_DOWNLOAD_BASE_URL:-https://github.com/kopia/kopia/releases/download/v${KOPIA_VERSION}}"
DOWNLOAD_TIMEOUT="${KOPIA_DOWNLOAD_TIMEOUT:-120}"

mkdir -p "$OUTPUT_DIR"

download() {
  local filename="$1"
  local url="${BASE_URL}/${filename}"
  local target="${OUTPUT_DIR}/${filename}"

  if [[ -s "$target" ]]; then
    echo "Kopia package exists: $target"
    return
  fi

  if [[ -s "${LOCAL_PACKAGE_DIR}/${filename}" ]]; then
    echo "Using local Kopia package: ${LOCAL_PACKAGE_DIR}/${filename}"
    cp "${LOCAL_PACKAGE_DIR}/${filename}" "$target"
    return
  fi

  echo "Downloading Kopia package: $url"
  if ! curl -fL \
    --retry 2 \
    --retry-delay 2 \
    --retry-all-errors \
    --connect-timeout 15 \
    --max-time "$DOWNLOAD_TIMEOUT" \
    -o "${target}.tmp" \
    "$url"; then
    rm -f "${target}.tmp"
    echo "Failed to download Kopia package: $url" >&2
    echo "Set KOPIA_DOWNLOAD_BASE_URL to an internal mirror, or place the package at: ${LOCAL_PACKAGE_DIR}/${filename}" >&2
    exit 1
  fi
  mv "${target}.tmp" "$target"
}

download "kopia_${KOPIA_VERSION}_linux_amd64.deb"
download "kopia-${KOPIA_VERSION}-linux-x64.tar.gz"
download "kopia-${KOPIA_VERSION}-macOS-arm64.tar.gz"
download "kopia-${KOPIA_VERSION}-macOS-x64.tar.gz"
download "kopia-${KOPIA_VERSION}-windows-x64.zip"
download "kopia-${KOPIA_VERSION}.x86_64.rpm"

echo "Kopia packages ready in: $OUTPUT_DIR"
