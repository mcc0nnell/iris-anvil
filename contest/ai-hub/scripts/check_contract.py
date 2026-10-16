#!/usr/bin/env python3
"""Offline structural checks only; do not mistake for IRIS build-154 execution."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src" / "Anvil" / "Interop"
classes = {x.stem: x.read_text() for x in src.glob("*.cls")}
required = {"Agent", "Alert", "Dispatch", "Result", "Policy", "Router", "Inbox", "Deliver", "Production"}
assert required == classes.keys(), f"classes differ: {required ^ classes.keys()}"
assert "##class(%AI.Provider).Create" in classes["Agent"]
assert "##class(%AI.Agent).%New" in classes["Agent"]
assert "agent.Chat(session" in classes["Agent"]
assert 'If (signal="SMOKE")!(signal="BABY_CRY") Quit "BOTH"' in classes["Policy"]
assert '"BLOCKED"' in classes["Policy"] and '"UNAVAILABLE"' in classes["Agent"]
assert "SendRequestSync" in classes["Router"] and "SendRequestSync" in classes["Inbox"]
assert "Extends Ens.BusinessProcess" in classes["Router"]
assert "Extends Ens.BusinessService" in classes["Inbox"]
assert "Extends Ens.BusinessOperation" in classes["Deliver"]
assert "Extends Ens.Production" in classes["Production"]
assert "OPENAI_API_KEY" in classes["Agent"]
assert "2026.3.0AI.154.0" in (ROOT / "compose.yml").read_text()
assert "pull_policy: never" in (ROOT / "compose.yml").read_text()
p=classes["Production"]
m=re.search(r"<Production\b.*?</Production>",p,re.S)
assert m
definition=ET.fromstring(m.group(0))
items={e.attrib["Name"] for e in definition.findall("Item")}
assert items == {"Anvil.Inbox","Anvil.Router","Anvil.VISUAL","Anvil.HAPTIC","Anvil.BOTH","Anvil.REVIEW"}
assert not any("api_key\": \"sk-" in text for text in classes.values())
print("PASS: 14 offline structural/contract checks; LIVE AI HUB 154 NOT TESTED")
