#!/usr/bin/env python3
"""Fail-closed consistency checker for IRIS lab debugger and terminal traces."""
import argparse
import hashlib
import json
import re
from pathlib import Path

FRAME = re.compile(r"^#\d+\s+0x[0-9a-fA-F]+\s+in\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
HIT = re.compile(r"^PHASE_HIT\|([A-Za-z_][A-Za-z0-9_]*)\|(\d\d:\d\d:\d\d\.\d+)$")
READY = re.compile(r"PHASE_READY\|(\d+)\|\d+,\d+")
MARKERS = (
    "PHASE_READY|", "PHASE_START|", "PHASE_SET|",
    "PHASE_COMMIT|", "PHASE_VERIFIED|0|phase", "PHASE_CLEAN|0"
)
FATAL = ("ptrace: No such process", "Error in sourced command file",
         "Operation not permitted", "The program is not being run")

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(session, debugger, runtime_binary):
    terminal = Path(session).read_text()
    trace = Path(debugger).read_text()
    positions = [terminal.find(mark) for mark in MARKERS]
    if any(terminal.count(mark) != 1 for mark in MARKERS) or positions != sorted(positions):
        raise ValueError("Missing, duplicated, or misordered required phase markers")
    pids = READY.findall(terminal)
    if len(pids) != 1:
        raise ValueError("Exactly one worker PID is required")
    pid = pids[0]
    if f"[Inferior 1 (process {pid}) exited normally]" not in trace:
        raise ValueError("Debugger did not observe normal exit of session worker")
    if any(error in trace for error in FATAL):
        raise ValueError("Debugger reported fatal instrumentation error")
    samples = []
    current = None
    for line in trace.splitlines():
        hit = HIT.match(line)
        if hit:
            current = {"symbol": hit.group(1), "utc": hit.group(2), "frames": []}
            samples.append(current)
        elif current:
            match = FRAME.match(line)
            if match:
                current["frames"].append(match.group(1))
    def contains(symbol, caller):
        return any(s["symbol"] == symbol and caller in s["frames"][1:] for s in samples)
    required = (
        ("gsetjrn", "Cgset"), ("journalset", "gsetjrn"),
        ("journaltran", "journalset"), ("journaltran", "Ctcommit")
    )
    missing = [f"{s} <- {caller}" for s, caller in required if not contains(s, caller)]
    if missing:
        raise ValueError("Required runtime call-frame evidence missing: " + ", ".join(missing))
    return {
        "schema": "iris-anvil.native-execution-observation.v1",
        "authority": "NONE",
        "status": "OBSERVED_EXECUTION_NOT_DURABILITY_PROOF",
        "worker_pid": int(pid),
        "runtime_executable_sha256": sha256(runtime_binary),
        "terminal_sha256": sha256(session),
        "debugger_sha256": sha256(debugger),
        "required_paths_observed": [f"{caller} -> {s}" for s, caller in required],
        "hit_counts": {symbol: sum(s["symbol"] == symbol for s in samples)
                       for symbol in sorted({s["symbol"] for s in samples})},
        "limitations": [
            "Local logs are not independently attested.",
            "Recorded frames do not establish complete causal ordering.",
            "This run does not prove fsync, WIJ flush, durable commit, crash recovery, or security impact.",
            "Synthetic, instrumented execution is not a performance benchmark."
        ]
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--debugger", type=Path, required=True)
    p.add_argument("--runtime-binary", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.session, a.debugger, a.runtime_binary)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("verified native lab observation: worker=%d paths=%d status=%s" %
          (result["worker_pid"], len(result["required_paths_observed"]), result["status"]))

if __name__ == "__main__":
    main()
