#!/usr/bin/env python3
"""Execute ONE genuine AI Hub 154 -> Grok -> IRIS governed-receipt proof.

No image distribution, external notification, production mutation or fake model.
An isolated Docker container and temporary private Unix bridge are removed on exit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "iris-ai-hub-community:2026.3.0AI.154.0"
MARK = "ANVIL_GOLDEN_STATE|"
DETAIL = "Synthetic front-door visitor; accessible local demonstration only"


def command(*args, input_text=None, timeout=45):
    result = subprocess.run(
        args, input=input_text, text=True, capture_output=True, timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{args[0]} returned {result.returncode}: {result.stderr[-500:]}")
    return result.stdout


def state_from_irissession(output):
    if re.search(r"ERROR\s*#\s*\d+|<SYNTAX>|<UNDEFINED>|<CLASS DOES NOT EXIST>", output, re.I):
        raise RuntimeError("IRIS state query emitted diagnostic")
    records = [line[len(MARK):] for line in output.splitlines() if line.startswith(MARK)]
    if len(records) != 1:
        raise ValueError("missing or duplicated native state marker")
    state = json.loads(records[0])
    if not isinstance(state, dict) or state.get("status") not in ("PENDING", "COMPLETE"):
        raise ValueError("invalid native state result")
    return state


def bridge_successes(log):
    records = []
    for line in log.read_text(errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("event") == "model_success":
            if entry.get("route") not in ("VISUAL", "HAPTIC", "BOTH", "REVIEW"):
                raise ValueError("bridge reported noncanonical decision")
            records.append(entry)
    return records


def bridge_attempt_count(log):
    attempts = 0
    for line in log.read_text(errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("event") == "model_request_started":
            attempts += 1
    return attempts


def require_good_state(data, event_id):
    if data.get("status") != "COMPLETE" or data.get("event_id") != event_id:
        raise ValueError("receipt for selected event not complete")
    if data.get("signal") != "DOORBELL":
        raise ValueError("wrong synthetic signal in stored receipt")
    for key in ("pending_cleared", "queue_payload_ok", "outbox_matches",
                "policy_matches", "receipt_matches"):
        if data.get(key) not in (True, 1):
            raise ValueError("native persisted-state check failed: " + key)
    if data.get("queue_count") != 1:
        raise ValueError("native replay has unexpected queue cardinality")
    if data.get("failed_inbound_headers") != 0:
        raise ValueError("IRIS logged a failed inbound Alert for this event")
    if not isinstance(data.get("inbound_header_count"), int) or data["inbound_header_count"] < 1:
        raise ValueError("no attributable native IRIS inbound message header")
    if data.get("proposal") not in ("VISUAL", "HAPTIC", "BOTH", "REVIEW"):
        raise ValueError("noncanonical saved model proposal")
    if data.get("route") != data.get("proposal"):
        raise ValueError("doorbell policy incorrectly changed route")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-dir", type=Path, required=True,
                        help="new absolute private evidence directory, outside repository")
    parser.add_argument("--grok-binary", type=Path,
                        default=Path.home() / ".local/bin/grok")
    args = parser.parse_args()
    if not args.lab_dir.is_absolute() or args.lab_dir.exists():
        parser.error("--lab-dir must be a new absolute directory")
    if not args.grok_binary.is_file():
        parser.error("authenticated Grok binary unavailable")
    if command("git", "-C", str(ROOT), "status", "--porcelain").strip():
        parser.error("checkout is dirty; commit or discard changes before collecting provenance")
    lab = args.lab_dir
    lab.mkdir(mode=0o700, parents=True)
    lab.chmod(0o700)
    for sub in ("run", "clean-cwd", "evidence", "inbox", "archive"):
        (lab / sub).mkdir()
    # Traversable only inside the private lab; IRIS UID can archive synthetic files.
    for sub in ("inbox", "archive"):
        (lab / sub).chmod(0o777)
    container = "anvil-golden-" + secrets.token_hex(5)
    event_id = "golden-doorbell-" + secrets.token_hex(6)
    manifest = {
        "schema": "iris-anvil-contest-golden-path-v1",
        "image": IMAGE,
        "source_commit": command("git", "-C", str(ROOT), "rev-parse", "HEAD").strip(),
        "event_id": event_id,
        "synthetic": True,
        "network": "none; no published Docker ports; localhost proxy to private host Unix socket",
        "result": "INCOMPLETE",
        "boundaries": [
            "one real model decision; native deterministic policy separately verified",
            "local IRIS queue and receipt only; no external notification",
            "not SIGKILL recovery, unattended supervision, or signed attestation",
        ],
    }
    bridge = None
    started = False
    log = lab / "evidence" / "bridge.log"
    try:
        command("docker", "image", "inspect", IMAGE)
        image_id = command("docker", "image", "inspect", "--format", "{{.Id}}", IMAGE).strip()
        manifest["image_id"] = image_id
        with log.open("w") as writer:
            bridge = subprocess.Popen([
                sys.executable, "-u", str(ROOT / "tools/grok/bridge.py"),
                "--socket", str(lab / "run/grok.sock"),
                "--cwd", str(lab / "clean-cwd"),
                "--grok-binary", str(args.grok_binary),
            ], stdout=writer, stderr=subprocess.STDOUT)
            for _ in range(50):
                if (lab / "run/grok.sock").is_socket():
                    break
                if bridge.poll() is not None:
                    raise RuntimeError("host Grok bridge exited")
                time.sleep(0.1)
            else:
                raise TimeoutError("private Grok socket not ready")
            command(
                "docker", "run", "-d", "--rm", "--name", container,
                "--network", "none",
                "-e", "OPENAI_API_KEY=synthetic-local-bridge",
                "-e", "AI_HUB_OPENAI_BASE_URL=http://127.0.0.1:8389/v1/",
                "-e", "ANVIL_GOLDEN_EVENT_ID=" + event_id,
                "--mount", f"type=bind,src={ROOT / 'src'},dst=/opt/iris-anvil/src,readonly",
                "--mount", f"type=bind,src={lab / 'inbox'},dst=/opt/iris-anvil/inbox",
                "--mount", f"type=bind,src={lab / 'archive'},dst=/opt/iris-anvil/archive",
                "--mount", f"type=bind,src={lab / 'run'},dst=/grokbridge,readonly",
                IMAGE, "--check-caps", "false", timeout=60,
            )
            started = True
            for _ in range(60):
                healthy = command("docker", "inspect", "--format",
                                  "{{.State.Health.Status}}", container).strip()
                if healthy == "healthy":
                    break
                if healthy == "unhealthy":
                    raise RuntimeError("IRIS container unhealthy")
                time.sleep(1)
            else:
                raise TimeoutError("IRIS container did not become healthy")
            command("docker", "cp", str(ROOT / "tools/grok/container_proxy.py"),
                    container + ":/tmp/anvil-container-proxy.py")
            command("docker", "exec", "-d", "-u", "0", container, "python3", "-u",
                    "/tmp/anvil-container-proxy.py")
            for _ in range(30):
                probe = subprocess.run([
                    "docker", "exec", container, "python3", "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8389/health',timeout=2)",
                ], capture_output=True, timeout=8)
                if probe.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("container-only model bridge proxy unavailable")

            def native(script, dest, timeout=45):
                raw = command("docker", "exec", "-i", container, "iris",
                              "session", "iris", "-U", "USER",
                              input_text=(ROOT / "scripts" / script).read_text(),
                              timeout=timeout)
                (lab / "evidence" / dest).write_text(raw)
                return raw

            native("compile-only.scr", "compile.log")
            command(sys.executable, str(ROOT / "scripts/verify-runtime-log.py"),
                    "compile", str(lab / "evidence/compile.log"))
            native("policy-only.scr", "policy.log")
            command(sys.executable, str(ROOT / "scripts/verify-runtime-log.py"),
                    "policy", str(lab / "evidence/policy.log"))
            installation = native("install.scr", "production-start.log", timeout=90)
            if "ANVIL INTEROP PRODUCTION STARTED" not in installation:
                raise RuntimeError("native interoperability production did not start")
            manifest["native_compiled_classes"] = 9
            manifest["native_policy_cases"] = 8

            def stage(suffix):
                path = lab / "inbox" / (event_id + "-" + suffix + ".json")
                with path.open("x") as f:
                    json.dump({"event_id": event_id, "signal": "DOORBELL",
                               "detail": DETAIL}, f, separators=(",", ":"))
                    f.write("\n")

            stage("first")
            first = None
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                state = state_from_irissession(native("golden-state.scr", "state-current.log"))
                if state["status"] == "COMPLETE":
                    first = state
                    break
                time.sleep(2)
            if first is None:
                raise TimeoutError("no persisted receipt within 120 seconds")
            require_good_state(first, event_id)
            (lab / "evidence/first-state.json").write_text(json.dumps(first, indent=2) + "\n")
            first_calls = bridge_successes(log)
            if len(first_calls) != 1 or bridge_attempt_count(log) != 1 or first_calls[0]["route"] != first["proposal"]:
                raise RuntimeError("one attributable Grok model decision not confirmed")
            stage("replay")
            # The adapter can retain source files. Count distinct IRIS inbound
            # message headers for THIS event; a file's presence is not proof.
            second = None
            for _ in range(40):
                observed = state_from_irissession(native("golden-state.scr", "state-replay.log"))
                if observed.get("inbound_header_count", 0) >= 2:
                    second = observed
                    break
                time.sleep(2)
            if second is None:
                raise TimeoutError("no second IRIS inbound Alert header for identical replay")
            require_good_state(second, event_id)
            if second["inbound_header_count"] < first["inbound_header_count"] + 1:
                raise RuntimeError("native inbound message count did not increase")
            changed = [k for k in first if k != "inbound_header_count" and second.get(k) != first[k]]
            if changed:
                raise RuntimeError("replay changed persisted receipt/policy/queue: " + repr(changed))
            if len(bridge_successes(log)) != 1 or bridge_attempt_count(log) != 1:
                raise RuntimeError("idempotent replay unexpectedly invoked the model")
            (lab / "evidence/replay-state.json").write_text(json.dumps(second, indent=2) + "\n")
            manifest.update({
                "result": "PASS", "model": "authenticated Grok CLI via native AI Hub Chat",
                "model_proposal": first["proposal"], "deterministic_route": first["route"],
                "receipt": first["receipt"], "model_success_calls": 1,
                "new_model_calls_on_identical_replay": 0, "queue_count": 1,
                "native_inbound_headers": second["inbound_header_count"],
                "failed_native_inbound_headers": second["failed_inbound_headers"],
                "model_invocation_attempts": bridge_attempt_count(log),
            })
    except Exception as ex:
        manifest["error_class"] = type(ex).__name__
        manifest["error"] = str(ex)[:500]
        raise
    finally:
        if started:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=25)
        if bridge is not None:
            bridge.terminate()
            try:
                bridge.wait(timeout=8)
            except subprocess.TimeoutExpired:
                bridge.kill()
                bridge.wait()
        manifest["container_removed"] = not started or subprocess.run(
            ["docker", "inspect", container], capture_output=True).returncode != 0
        proofs = sorted((lab / "evidence").glob("*"))
        manifest["evidence_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in proofs
            if p.is_file()
        }
        (lab / "evidence/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps({
            "status": manifest["result"], "event_id": event_id,
            "proposal": manifest.get("model_proposal"),
            "route": manifest.get("deterministic_route"),
            "receipt": manifest.get("receipt"),
            "evidence": str(lab / "evidence/manifest.json"),
            "error": manifest.get("error"),
        }, sort_keys=True))


if __name__ == "__main__":
    main()
