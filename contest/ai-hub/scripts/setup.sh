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
# Compose reports container creation, not IRIS readiness. On a cold AI Hub 154
# start the native terminal may return exit 225 until the health probe passes.
ready=0
for attempt in $(seq 1 90); do
  state="$(docker inspect --format '{{.State.Status}}' iris-anvil-aihub)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' iris-anvil-aihub)"
  if [[ "$state" != "running" || "$health" == "unhealthy" ]]; then
    echo "IRIS startup failed: container=$state health=$health" >&2
    exit 1
  fi
  if [[ "$health" == "healthy" ]]; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "IRIS did not become healthy within the readiness window." >&2
  exit 1
fi
install_output="$(docker exec -i iris-anvil-aihub iris session iris -U USER < scripts/install.scr)"
printf '%s\n' "$install_output"
if [[ "$install_output" == *"ANVIL INTEROP PRODUCTION ALREADY RUNNING; CLASSES NOT RECOMPILED"* ]]; then
  echo "Existing production preserved; stop it explicitly before installing source updates."
elif [[ "$install_output" == *"ANVIL INTEROP PRODUCTION STARTED"* ]]; then
  echo "Production started with freshly compiled classes."
else
  echo "Installation/production start failed. Inspect output above." >&2
  exit 1
fi
echo "Production available in local IRIS Management Portal."
