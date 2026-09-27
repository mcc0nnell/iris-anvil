#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${IRIS_CONTAINER:-iris-anvil-iris}"
PORT="${IRIS_HTTP_PORT:-52773}"
ready=0
for _ in $(seq 1 120); do
  if docker exec "$CONTAINER" iris qlist 2>/dev/null | grep -q '\^running,'; then ready=1; break; fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then echo "IRIS did not become ready in $CONTAINER" >&2; exit 1; fi
docker exec -i "$CONTAINER" iris session IRIS < "$ROOT/scripts/bootstrap_iris.scr"
curl -fsS "http://127.0.0.1:${PORT}/anvil/api/overview" >/dev/null
echo "IRIS Anvil bootstrap complete: http://127.0.0.1:${PORT}/anvil/index.html"
