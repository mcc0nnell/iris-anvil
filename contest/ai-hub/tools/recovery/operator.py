#!/usr/bin/env python3
"""Human-gated one-shot synthetic event replay; no model calls or silent retries.

Runs on the authorized Docker host. On --apply, a native IRIS lock protects
a one-shot claim before the same saved payload is staged in the inbox.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

EVENT_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
SHA_RE = re.compile(r"[A-Za-z0-9+/]{43}=\Z")
MARK = "ANVIL_OPERATOR_JSON|"
WRITER = r'''
import json, os, sys, tempfile
request = json.load(sys.stdin)
event = request["event_id"]
if not (event and len(event) <= 64 and all(x.isalnum() and x.isascii() or x in "_-" for x in event)):
    raise SystemExit("bad event")
path = "/opt/iris-anvil/inbox"
final = path + "/recovery-" + event + ".json"
fd, temp = tempfile.mkstemp(prefix=".recovery-", suffix=".part", dir=path)
try:
    with os.fdopen(fd,"w") as f:
        json.dump({k:request[k] for k in ("event_id","signal","detail")},f,separators=(",",":"))
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temp, 0o640)
    os.link(temp, final)  # exclusive, cannot overwrite a waiting same-id input
    print("STAGED:" + event)
finally:
    os.unlink(temp)
'''


def command(args, *, input_text=None):
    result = subprocess.run(
        args, input=input_text, text=True, capture_output=True,
        timeout=25, check=False,
    )
    if result.returncode:
        raise RuntimeError("Command failed, no success claimed: " + str(result.returncode)
                           + " " + result.stderr[:180])
    return result.stdout


def parse_result(text):
    if "<ERROR" in text or "ERROR #" in text or "<SYNTAX>" in text:
        raise ValueError("IRIS returned an error diagnostic")
    matches = [line[len(MARK):] for line in text.splitlines() if line.startswith(MARK)]
    if len(matches) != 1:
        raise ValueError("Missing or duplicate complete IRIS recovery response")
    parsed = json.loads(matches[0])
    if not isinstance(parsed, dict) or parsed.get("status") not in ("READY","BLOCKED","CLAIMED","COMPLETED"):
        raise ValueError("Unexpected response")
    return parsed


def iris_call(container, event_id, expected=None):
    # event ID and digest validated before interpolation into ObjectScript.
    if not EVENT_RE.fullmatch(event_id):
        raise ValueError("Invalid event ID")
    if expected is not None and not SHA_RE.fullmatch(expected):
        raise ValueError("Invalid fingerprint")
    stmt = (f'set r=##class(Anvil.Interop.RecoveryReplay).Inspect("{event_id}")'
            if expected is None
            else f'set r=##class(Anvil.Interop.RecoveryReplay).Claim("{event_id}","{expected}")')
    script = (
        'zn "USER"\n'
        'set sc=$SYSTEM.OBJ.Load("/tmp/AnvilRecoveryReplay.cls","ck")\n'
        'if \'$SYSTEM.Status.IsOK(sc) {write "ANVIL_LOAD_FAILED",! halt}\n'
        + stmt + '\n'
        + 'write "' + MARK + '",r.%ToJSON(),!\n'
        + 'halt\n'
    )
    raw = command(["docker","exec","-i",container,"iris","session","iris","-U","USER"],
                  input_text=script)
    if "ANVIL_LOAD_FAILED" in raw:
        raise ValueError("Audit class load failed")
    return parse_result(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--container", required=True, help="authorized isolated IRIS container name")
    ap.add_argument("--event-id", required=True)
    ap.add_argument("--apply", action="store_true", help="claim and stage exactly one replay")
    ap.add_argument("--ack-restarted", action="store_true", help="confirm healthy IRIS production was restarted after the fault")
    ap.add_argument("--expected-digest", help="exact base64 input_digest from a prior dry run")
    ap.add_argument("--class-file", type=Path, default=Path(__file__).with_name("RecoveryReplay.cls"))
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", args.container):
        ap.error("invalid container name")
    if not EVENT_RE.fullmatch(args.event_id):
        ap.error("invalid event ID")
    if args.apply and (not args.ack_restarted or not args.expected_digest):
        ap.error("--apply requires --ack-restarted and --expected-digest")
    if args.apply and not SHA_RE.fullmatch(args.expected_digest):
        ap.error("invalid expected digest")
    if not args.class_file.is_file():
        ap.error("RecoveryReplay.cls missing")
    command(["docker","cp",str(args.class_file),args.container+":/tmp/AnvilRecoveryReplay.cls"])
    candidate = iris_call(args.container, args.event_id)
    # No payload disclosed in plan (only id, route, digest).
    print(json.dumps({k:v for k,v in candidate.items() if k != "detail"},sort_keys=True))
    if not args.apply:
        return 0 if candidate["status"] in ("READY","COMPLETED") else 2
    if candidate["status"] != "READY":
        raise RuntimeError("Not eligible for replay")
    if candidate["input_digest"] != args.expected_digest:
        raise RuntimeError("Replay candidate changed")
    claimed = iris_call(args.container,args.event_id,args.expected_digest)
    if claimed.get("status") != "CLAIMED":
        raise RuntimeError("Replay claim was denied: " + claimed.get("reason","unknown"))
    if any(claimed.get(k) != candidate.get(k) for k in ("event_id","signal","detail","proposal","route","input_digest")):
        raise RuntimeError("Claim differs from inspected candidate; claim retained for review")
    # Important: claim remains durable even if staging fails; explicit reconciliation required.
    out = command(["docker","exec","-i","--user","51773",args.container,"python3","-c",WRITER],
                  input_text=json.dumps({k:claimed[k] for k in ("event_id","signal","detail")}))
    if out.strip() != "STAGED:"+args.event_id:
        raise RuntimeError("Unexpected file staging result; claim remains")
    print("STAGED_ONCE|" + args.event_id + "|proposal=" + claimed["proposal"] + "|route=" + claimed["route"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        print("FAIL_CLOSED: "+str(error), file=sys.stderr)
        raise SystemExit(3)
