#!/usr/bin/env python3
"""Bounded, opt-in recovery watch for ONE synthetic IRIS event. Off by default.

Never restarts IRIS and never invokes an LLM. A saved proposal, current policy,
outbox digest, stale queue, AND matching failed IRIS message are required.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("anvil_recovery_operator", ROOT / "operator.py")
op = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(op)
WATCH_MARK = "ANVIL_WATCH_JSON|"


def probe(container, event, min_age):
    if not op.EVENT_RE.fullmatch(event):
        raise ValueError("Invalid event ID")
    if not 60 <= min_age <= 86400:
        raise ValueError("Minimum age must be between 60 and 86400 seconds")
    script = (
        'zn "USER"\n'
        'set sc=$SYSTEM.OBJ.Load("/tmp/AnvilRecoveryReplay.cls","ck")\n'
        'if \'$SYSTEM.Status.IsOK(sc) {write "WATCH_LOAD_FAILED",! halt}\n'
        'set sc=$SYSTEM.OBJ.Load("/tmp/AnvilRecoveryWatch.cls","ck")\n'
        'if \'$SYSTEM.Status.IsOK(sc) {write "WATCH_LOAD_FAILED",! halt}\n'
        f'set r=##class(Anvil.Interop.RecoveryWatch).Probe("{event}",{min_age})\n'
        f'write "{WATCH_MARK}",r.%ToJSON(),!\n'
        'halt\n'
    )
    raw = op.command(["docker", "exec", "-i", container, "iris", "session", "iris", "-U", "USER"], input_text=script)
    if "WATCH_LOAD_FAILED" in raw or "<SYNTAX>" in raw or "ERROR #" in raw or "<ERROR" in raw:
        raise RuntimeError("IRIS watch load/execution error")
    matches = [x[len(WATCH_MARK):] for x in raw.splitlines() if x.startswith(WATCH_MARK)]
    if len(matches) != 1:
        raise ValueError("Missing/duplicate watch response")
    result = json.loads(matches[0])
    if not isinstance(result, dict) or result.get("status") not in ("BLOCKED", "READY"):
        raise ValueError("Unexpected watch response")
    if result["status"] == "READY" and (
        result.get("event_id") != event or
        not op.SHA_RE.fullmatch(result.get("input_digest", "")) or
        result.get("route") not in ("VISUAL", "HAPTIC", "BOTH", "REVIEW")
    ):
        raise ValueError("Incomplete watch proof")
    return result


def run(args):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,90}", args.container):
        raise ValueError("Invalid container name")
    if not op.EVENT_RE.fullmatch(args.event_id):
        raise ValueError("Invalid event ID")
    if not (60 <= args.min_age <= 86400 and 1 <= args.max_cycles <= 120 and 2 <= args.poll_seconds <= 300):
        raise ValueError("Invalid bounded watch configuration")
    if args.arm and not args.ack_production_restarted:
        raise ValueError("Armed watch requires --ack-production-restarted")
    if not args.arm and args.ack_production_restarted:
        raise ValueError("Do not attest restart for a read-only watch")
    if not args.watch_class.is_file() or not args.replay_class.is_file():
        raise ValueError("Required optional ObjectScript classes missing")
    op.command(["docker", "cp", str(args.replay_class), args.container+":/tmp/AnvilRecoveryReplay.cls"])
    op.command(["docker", "cp", str(args.watch_class), args.container+":/tmp/AnvilRecoveryWatch.cls"])
    for iteration in range(1,args.max_cycles+1):
        result = probe(args.container, args.event_id, args.min_age)
        print(json.dumps({"iteration":iteration,**result},sort_keys=True),flush=True)
        if result["status"] == "READY":
            if not args.arm:
                return 0
            command = [sys.executable, str(ROOT / "operator.py"), "--container", args.container,
                       "--event-id", args.event_id, "--apply", "--ack-restarted",
                       "--expected-digest", result["input_digest"],
                       "--class-file", str(args.replay_class)]
            # Existing operator re-validates the entire candidate under an IRIS event lock.
            subprocess.run(command,check=True,timeout=90)
            print("WATCH_STAGED_ONCE|" + args.event_id, flush=True)
            return 0
        if iteration < args.max_cycles:
            time.sleep(args.poll_seconds)
    print("WATCH_EXHAUSTED_NO_RECOVERY|" + args.event_id,flush=True)
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container",required=True)
    parser.add_argument("--event-id",required=True)
    parser.add_argument("--min-age",type=int,default=120)
    parser.add_argument("--max-cycles",type=int,default=12)
    parser.add_argument("--poll-seconds",type=int,default=10)
    parser.add_argument("--arm",action="store_true",help="permit exactly one automatic replay while this watch is active")
    parser.add_argument("--ack-production-restarted",action="store_true",help="operator confirms production restarted and no worker still owns the request")
    parser.add_argument("--watch-class",type=Path,default=ROOT/"RecoveryWatch.cls")
    parser.add_argument("--replay-class",type=Path,default=ROOT/"RecoveryReplay.cls")
    a=parser.parse_args()
    try:
        raise SystemExit(run(a))
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print("WATCH_FAIL_CLOSED|"+str(exc),file=sys.stderr)
        raise SystemExit(3)
