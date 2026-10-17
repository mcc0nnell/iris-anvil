#!/usr/bin/env python3
"""Only inside network-none IRIS lab. Loopback HTTP to host Grok Unix socket."""
import http.client
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UNIX_PATH = "/grokbridge/grok.sock"

class UnixHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(85)
        self.sock.connect(UNIX_PATH)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"proxy-ready"}'
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        self.send_error(404)

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 8192:
                return self.send_error(413)
            payload = self.rfile.read(n)
            conn = UnixHTTPConnection("localhost", timeout=85)
            conn.request("POST", self.path, body=payload, headers={"Content-Type":"application/json"})
            resp = conn.getresponse()
            body = resp.read(16384)
            self.send_response(resp.status)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(body)
            conn.close()
        except (OSError, ValueError, http.client.HTTPException):
            body = b'{"error":{"message":"private Grok bridge unavailable"}}'
            self.send_response(502)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)

server = ThreadingHTTPServer(("127.0.0.1",8389),Handler)
server.serve_forever()
