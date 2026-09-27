#!/usr/bin/env python3
"""Exercise the real IRIS 2026.2 SysAdmin and Anvil receipt path.

Requires ANVIL_OPERATOR_USER and ANVIL_OPERATOR_PASSWORD for an account with
%Admin_Secure:USE and access to the USER namespace. Mutates only /anvil-demo.
"""

import base64
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("ANVIL_BASE_URL", "http://127.0.0.1:52773").rstrip("/")
USER = os.environ.get("ANVIL_OPERATOR_USER")
PASSWORD = os.environ.get("ANVIL_OPERATOR_PASSWORD")
if not USER or not PASSWORD:
    sys.exit("Set ANVIL_OPERATOR_USER and ANVIL_OPERATOR_PASSWORD first")


def request(path, method="GET", body=None, authorization=None):
    headers = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        message = exc.read(500).decode(errors="replace")
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {message}") from exc


basic = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
overview_status, overview = request("/anvil/api/overview")
assert overview_status == 200 and "2026.2" in overview["version"], overview

_, login = request("/api/admin/login", "POST", {"user": USER, "password": PASSWORD})
bearer = "Bearer " + login["access_token"]
request("/api/admin/info", authorization=bearer)

try:
    request("/anvil/admin/proposals", "POST",
            {"action": "DEPLOY_WEB_APP", "target": "/anvil-demo",
             "payload": "NameSpace=USER|DispatchClass=Other.REST|Enabled=1"}, basic)
except RuntimeError as exc:
    assert "HTTP 403" in str(exc), exc
else:
    raise AssertionError("Out-of-allowlist proposal was accepted")

action = {"action": "DEPLOY_WEB_APP", "target": "/anvil-demo",
          "payload": "NameSpace=USER|DispatchClass=Anvil.REST|Enabled=1",
          "idempotencyKey": "smoke-" + secrets.token_hex(12)}
created, proposal = request("/anvil/admin/proposals", "POST", action, basic)
assert created == 201 and proposal["state"] == "PLANNED", proposal
id_ = proposal["id"]
_, before = request(f"/anvil/admin/proposals/{id_}/verify", authorization=basic)
assert not before["verified"], "A planned proposal must not verify as executed"

app_path = "/api/admin/v2/web-app?name=" + urllib.parse.quote("/anvil-demo", safe="")
put_status, _ = request(app_path, "PUT", {"NameSpace": "USER",
                                            "DispatchClass": "Anvil.REST",
                                            "Enabled": True, "AutheEnabled": 64}, bearer)
assert put_status in (200, 201), put_status
_, readback = request(app_path, authorization=bearer)
app = readback["result"]
assert (app["NameSpace"], app["DispatchClass"], app["Enabled"]) == (
    "USER", "Anvil.REST", True), app

_, executed = request(f"/anvil/admin/proposals/{id_}/execute", "POST", authorization=basic)
assert executed["verified"] and executed["receipt"], executed
_, verified = request(f"/anvil/admin/proposals/{id_}/verify", authorization=basic)
assert verified["verified"] and verified["receipt"] == executed["receipt"], verified
_, replay = request(f"/anvil/admin/proposals/{id_}/execute", "POST", authorization=basic)
assert replay["verified"] and replay["receipt"] == executed["receipt"], replay

for endpoint in ("processes", "tasks"):
    _, observation = request(f"/api/admin/v2/{endpoint}?maxRows=100", authorization=bearer)
    assert isinstance(observation["result"], list), endpoint

print(f"PASS IRIS 2026.2: SysAdmin PUT/GET, independent receipt, replay, "
      f"processes and tasks (proposal #{id_})")
