#!/usr/bin/env python3
"""Require complete, attributable AI Hub compile/policy proof; reject partial logs.

This verifier does not run or attest an IRIS instance. It validates text produced
by compile-only.scr or policy-only.scr in an authorized IRIS runtime session.
"""
import argparse
import re
from pathlib import Path

CLASSES = ("Alert", "Dispatch", "Result", "Policy", "Agent", "Deliver",
           "Router", "Inbox", "Production")
CASES = (
    ("SMOKE", "VISUAL", "BOTH"),
    ("BABY_CRY", "HAPTIC", "BOTH"),
    ("DOORBELL", "VISUAL", "VISUAL"),
    ("LAUNDRY", "HAPTIC", "HAPTIC"),
    ("UNKNOWN", "BOTH", "BLOCKED"),
    ("DOORBELL", "UNAVAILABLE", "BLOCKED"),
    ("DOORBELL", "REVIEW", "REVIEW"),
    ("DOORBELL", "INVALID", "BLOCKED"),
)

def validate(text: str, stage: str) -> None:
    label = "COMPILE" if stage == "compile" else "POLICY"
    prefix = f"ANVIL_{label}_"
    if text.count(prefix + "BEGIN") != 1:
        raise ValueError("missing or duplicate begin marker")
    expected = [f"{prefix}PASS|{name}" for name in CLASSES] if stage == "compile" else [
        f"{prefix}PASS|{'|'.join(case)}" for case in CASES
    ]
    matches = re.findall(rf"ANVIL_{label}_(?:PASS|FAIL)\|[^\r\n]*", text)
    if matches != expected:
        raise ValueError(f"unexpected passes/failures, order, or count: {matches!r}")
    summary = f"{prefix}SUMMARY|pass={len(expected)}|fail=0"
    if text.count(summary) != 1:
        raise ValueError("missing or mismatched complete summary")
    if len(re.findall(rf"ANVIL_{label}_SUMMARY\|", text)) != 1:
        raise ValueError("duplicate summary marker")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("compile", "policy"))
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    try:
        validate(args.log.read_text(errors="replace"), args.stage)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"BLOCKED: {args.stage} runtime evidence incomplete or failed: {exc}\n")
    print(f"PASS: verified {args.stage} log structure and all expected cases (not independent attestation)")

if __name__ == "__main__":
    main()
