#!/usr/bin/env python3
"""Local-only Grok Build CLI -> OpenAI chat-completions adapter for synthetic IRIS tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socketserver
import subprocess
import time
from http.server import BaseHTTPRequestHandler

ROUTES = {"VISUAL", "HAPTIC", "BOTH", "REVIEW"}
SIGNALS = {"DOORBELL", "LAUNDRY", "SMOKE", "BABY_CRY"}


def parse_grok_reply(output):
    data = json.loads(output)
    if not isinstance(data, dict) or data.get("type") == "error" or data.get("is_error") is True:
        raise ValueError("model error")
    if data.get("stopReason") != "end_turn":
        raise ValueError("model did not finish normally")
    choice = data.get("text")
    if not isinstance(choice, str) or choice.strip() not in ROUTES:
        raise ValueError("noncanonical model output")
    return choice.strip()


def synthetic_signal(request):
    if not isinstance(request, dict) or not isinstance(request.get("messages"), list):
        raise ValueError("messages missing")
    messages = request["messages"]
    if len(messages) > 16:
        raise ValueError("too many messages")
    text = "\n".join(m["content"] for m in messages if isinstance(m, dict)
                     and m.get("role") == "user" and isinstance(m.get("content"), str))
    if len(text) > 2000:
        raise ValueError("too much text")
    match = re.search(r"(?:^|\n)Signal: (\w+)(?:\n|$)", text)
    if not match or match.group(1) not in SIGNALS:
        raise ValueError("not an allowed synthetic signal")
    return match.group(1), text


class UnixServer(socketserver.UnixStreamServer):
    pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def respond(self, code, value):
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "ready", "engine": "grok-cli", "inference_verified": False})
        else:
            self.respond(404, {"error": {"message": "unsupported"}})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self.respond(404, {"error": {"message": "unsupported"}})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 8192:
                raise ValueError("request too large")
            signal, text = synthetic_signal(json.loads(self.rfile.read(n)))
        except (ValueError, TypeError, UnicodeError):
            return self.respond(400, {"error": {"message": "invalid synthetic request"}})
        print(json.dumps({"event":"model_request_started","signal":signal}), flush=True)
        prompt = ("This is a synthetic accessibility-routing evaluation, not a real emergency. "
                  "Do not use tools or web search. Reply with one uppercase token only: "
                  "VISUAL, HAPTIC, BOTH, or REVIEW.\n" + text)
        command = [self.server.grok_binary, "--cwd", str(self.server.clean_cwd),
                   "--single", prompt, "--verbatim", "--tools", "",
                   "--permission-mode", "plan", "--disable-web-search",
                   "--no-subagents", "--max-turns", "1", "--output-format", "json"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=65, check=False)
            if result.returncode != 0:
                raise ValueError("Grok process failed")
            route = parse_grok_reply(result.stdout)
        except (subprocess.TimeoutExpired, ValueError, OSError, json.JSONDecodeError) as e:
            print(json.dumps({"event":"model_failed","signal":signal,"class":type(e).__name__}), flush=True)
            return self.respond(502, {"error": {"message":"Grok inference unavailable"}})
        digest = hashlib.sha256(result.stdout.encode()).hexdigest()
        print(json.dumps({"event":"model_success","signal":signal,"route":route,
                          "output_sha256":digest,"cli_exit":result.returncode}), flush=True)
        self.respond(200, {"id":"chatcmpl-grok-bridge-"+digest[:18],"object":"chat.completion",
                           "created":int(time.time()),"model":"grok-build-cli-bridge",
                           "choices":[{"index":0,"message":{"role":"assistant","content":route},
                                       "finish_reason":"stop"}],
                           "usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--socket", type=Path, required=True)
    p.add_argument("--cwd", type=Path, required=True)
    p.add_argument("--grok-binary", required=True)
    a = p.parse_args()
    a.cwd.mkdir(parents=True, exist_ok=True)
    a.socket.parent.mkdir(parents=True, exist_ok=True)
    a.socket.parent.chmod(0o700)
    if a.socket.exists():
        raise SystemExit("Refusing to unlink existing socket")
    with UnixServer(str(a.socket), Handler) as server:
        os.chmod(a.socket, 0o600)
        server.grok_binary = a.grok_binary
        server.clean_cwd = a.cwd
        print(json.dumps({"event":"bridge_ready","socket":str(a.socket)}), flush=True)
        try:
            server.serve_forever()
        finally:
            a.socket.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
