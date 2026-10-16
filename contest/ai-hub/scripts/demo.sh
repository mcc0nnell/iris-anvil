#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
EVENT_ID="demo-$(date +%s)-$$"
# Synthetic event. This demo does NOT send real emergency notifications.
python3 - "$EVENT_ID" <<'PY'
import json,sys,pathlib
event={"event_id":sys.argv[1],"signal":"DOORBELL","detail":"Front entrance visitor; prefer an accessible prompt"}
path=pathlib.Path("inbox")/(sys.argv[1]+".json.tmp")
path.write_text(json.dumps(event)+"\n",encoding="utf-8")
path.rename(path.with_suffix(""))
print("Submitted synthetic event",event["event_id"])
PY
echo "Watch the IRIS production message trace and check ^Anvil.Interop.Receipts / ^Anvil.Interop.Queue in USER."
