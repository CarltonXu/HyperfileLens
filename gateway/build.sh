#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/gateway/agent"
DOWNLOADS_DIR="${ROOT_DIR}/backend/static/downloads"
OUTPUT_DIR="${ROOT_DIR}/backend/static/downloads/packages/gateway"
PACKAGE_NAME_PREFIX="hyperfilelens-gateway-linux"

export COPYFILE_DISABLE=1

mkdir -p "${OUTPUT_DIR}"

cp "${SOURCE_DIR}/install.sh" "${DOWNLOADS_DIR}/install-gateway.sh"
chmod 0644 "${DOWNLOADS_DIR}/install-gateway.sh"
echo "Published ${DOWNLOADS_DIR}/install-gateway.sh"

build_package() {
  local arch="$1"
  local package_path="${OUTPUT_DIR}/${PACKAGE_NAME_PREFIX}-${arch}.tar.gz"
  local work_dir

  work_dir="$(mktemp -d)"
  trap 'rm -rf "${work_dir}"' RETURN

  mkdir -p "${work_dir}/agent"
  cp "${SOURCE_DIR}/client.py" "${work_dir}/agent/"
  cp "${SOURCE_DIR}/requirements.txt" "${work_dir}/agent/"
  cp -R "${SOURCE_DIR}/hfl_gateway" "${work_dir}/agent/"
  if [[ -d "${SOURCE_DIR}/wheels/linux-${arch}" ]]; then
    mkdir -p "${work_dir}/agent/wheels/linux-${arch}"
    cp "${SOURCE_DIR}/wheels/linux-${arch}"/*.whl "${work_dir}/agent/wheels/linux-${arch}/"
  fi

  if command -v xattr >/dev/null 2>&1; then
    xattr -cr "${work_dir}" 2>/dev/null || true
  fi
  find "${work_dir}" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "${work_dir}" -name '._*' -delete

  rm -f "${package_path}"
  tar --no-xattrs -C "${work_dir}" -czf "${package_path}" agent 2>/dev/null || \
    tar -C "${work_dir}" -czf "${package_path}" agent
  echo "Built ${package_path}"
}

build_package "amd64"
build_package "arm64"
