#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${IRIS_CONTAINER:-iris-anvil-iris}"
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" iris qlist >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec -i "$CONTAINER" iris session IRIS < "$ROOT/scripts/bootstrap_iris.scr"
curl -fsS http://127.0.0.1:52773/anvil/api/overview >/dev/null
echo "IRIS Anvil bootstrap complete: http://127.0.0.1:52773/anvil/index.html"
