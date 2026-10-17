#!/usr/bin/env python3
"""Bounded, read-only x86-64 ELF direct-call mapping via GNU binutils."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SYM = re.compile(r"^([0-9a-f]+)\s+([0-9a-f]+)\s+([A-Za-z])\s+(\S+)$")
INSN = re.compile(r"^\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(call|jmp)\s+(.*?)\s*$")
DIRECT = re.compile(r"^([0-9a-f]+)\s+<([^>]+)>")

def run(*args):
    return subprocess.check_output(list(args), text=True)

def symbol_table(binary):
    result = {}
    for dynamic in (False, True):
        args = ["nm", "-S", "--defined-only"]
        if dynamic:
            args.insert(1, "-D")
        try:
            listing = run(*args, str(binary))
        except subprocess.CalledProcessError:
            continue
        for line in listing.splitlines():
            match = SYM.fullmatch(line.strip())
            if match:
                addr, size, kind, name = match.groups()
                if int(size, 16):
                    result.setdefault(name, {"address": int(addr, 16), "size": int(size, 16), "kind": kind})
        if result:
            break
    return result

def map_native_calls(binary, roots):
    symbols = symbol_table(binary)
    if not symbols:
        raise ValueError("No named, sized functions found in ELF symbol tables")
    missing = [name for name in roots if name not in symbols]
    if missing:
        raise ValueError("Requested symbols missing: " + ", ".join(missing))
    edges, functions = [], {}
    for name in roots:
        sym = symbols[name]
        address, size = sym["address"], sym["size"]
        dis = run("objdump", "-d", "-M", "intel",
                  f"--start-address={address:#x}", f"--stop-address={address + size:#x}", str(binary))
        counts = {"bytes": size, "calls": 0, "direct_calls": 0, "indirect_calls": 0, "external_jumps": 0}
        for line in dis.splitlines():
            inst = INSN.match(line)
            if not inst:
                continue
            pc, op, operands = inst.groups()
            if op == "call":
                counts["calls"] += 1
            direct = DIRECT.match(operands)
            if not direct:
                if op == "call":
                    counts["indirect_calls"] += 1
                continue
            to_address_text, target = direct.groups()
            to_address = int(to_address_text, 16)
            if op == "jmp" and address <= to_address < address + size:
                continue
            if op == "call":
                counts["direct_calls"] += 1
            else:
                counts["external_jumps"] += 1
            edges.append({"from": name, "at": "0x" + pc, "kind": op, "to": target,
                          "target_address": hex(to_address), "via_plt": "@plt" in target})
        functions[name] = counts
    return {
        "schema": "iris-anvil.native-call-map.v1",
        "authority": "NONE",
        "method": "GNU nm + objdump, bounded static x86-64 control transfers",
        "binary_name": binary.name,
        "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "roots": roots, "functions": functions, "edges": edges,
        "limitations": [
            "Static references do not prove a branch executed.",
            "PLT targets may be interposed; indirect calls and computed jumps are unresolved.",
            "No journal durability, crash safety, vulnerability, or full native assurance claim."
        ]
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True, help="locally supplied ELF")
    p.add_argument("--root", action="append", required=True, help="symbol to map (repeat)")
    p.add_argument("--output", type=Path, required=True, help="JSON output")
    args = p.parse_args()
    if not args.binary.is_file():
        p.error("binary does not exist")
    report = map_native_calls(args.binary, list(dict.fromkeys(args.root)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"roots={len(report['roots'])} direct_edges={len(report['edges'])} output={args.output}")

if __name__ == "__main__":
    main()
