#!/usr/bin/env bash

set -euo pipefail

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is required. Install the Docker Compose plugin or docker-compose." >&2
  exit 1
fi

ENV_ARGS=()
if [[ -n "${ENV_FILE:-}" ]]; then
  ENV_ARGS+=(--env-file "$ENV_FILE")
fi

"${COMPOSE[@]}" "${ENV_ARGS[@]}" up -d --build

echo
echo "HyperFileLens services:"
"${COMPOSE[@]}" "${ENV_ARGS[@]}" ps

echo
echo "Initial admin output:"
ADMIN_OUTPUT=$("${COMPOSE[@]}" "${ENV_ARGS[@]}" logs --no-color control-init | awk '/Initial admin/{seen=1} seen{print}')

if [[ -n "$ADMIN_OUTPUT" ]]; then
  echo "$ADMIN_OUTPUT"
else
  echo "No initial admin output found in control-init logs."
  echo "Run: ${COMPOSE[*]} ${ENV_ARGS[*]} logs control-init"
fi
