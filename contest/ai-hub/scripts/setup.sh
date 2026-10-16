#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="iris-ai-hub-community:2026.3.0AI.154.0"
INTERNAL="docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2026.3.0AI.154.0"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  if [[ -n "${AI_HUB_IMAGE_TAR:-}" ]]; then
    docker image load -i "$AI_HUB_IMAGE_TAR"
  fi
  docker image inspect "$INTERNAL" >/dev/null 2>&1 || {
    echo "Missing AI Hub 154 image. Download it from EAP portal and set AI_HUB_IMAGE_TAR." >&2
    exit 1
  }
  docker tag "$INTERNAL" "$IMAGE"
fi
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Warning: OPENAI_API_KEY missing; workflow will BLOCK decisions rather than simulate AI." >&2
fi
mkdir -p inbox archive
if ! command -v setfacl >/dev/null 2>&1; then
  echo "setfacl required to grant UID 51773 access to demo inbox/archive" >&2
  exit 1
fi
setfacl -m u:51773:rwx inbox archive
docker compose up -d
install_output="$(docker exec -i iris-anvil-aihub iris session iris -U USER < scripts/install.scr)"
printf '%s\n' "$install_output"
if [[ "$install_output" != *"ANVIL INTEROP PRODUCTION STARTED"* ]]; then
  echo "Installation/production start failed. Inspect output above." >&2
  exit 1
fi
echo "Production available in local IRIS Management Portal."
