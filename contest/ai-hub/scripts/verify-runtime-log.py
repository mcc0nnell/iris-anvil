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
    # Match *complete lines*, not embedded substrings that merely resemble
    # evidence markers (e.g. FAKE_ANVIL_COMPILE_PASS|Agent).
    lines = text.splitlines()
    if lines.count(prefix + "BEGIN") != 1:
        raise ValueError("missing or duplicate begin marker")
    expected = [f"{prefix}PASS|{name}" for name in CLASSES] if stage == "compile" else [
        f"{prefix}PASS|{'|'.join(case)}" for case in CASES
    ]
    matches = [line for line in lines if line.startswith(prefix + "PASS|")
               or line.startswith(prefix + "FAIL|")]
    if matches != expected:
        raise ValueError(f"unexpected passes/failures, order, or count: {matches!r}")
    summary = f"{prefix}SUMMARY|pass={len(expected)}|fail=0"
    summaries = [line for line in lines if line.startswith(prefix + "SUMMARY|")]
    if summaries != [summary]:
        raise ValueError("missing, duplicate or mismatched complete summary")
    # A success-looking summary cannot overrule explicit IRIS error diagnostics
    # elsewhere in the console output. This is a conservative transcript gate,
    # not a substitute for an authenticated compiler result.
    if re.search(r"\bERROR\s*#\s*\d+\b|<ERROR\b|^\s*ERROR:", text, re.I | re.M):
        raise ValueError("explicit IRIS error diagnostics present")

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
