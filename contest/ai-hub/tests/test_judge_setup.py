"""Offline process-level tests for cold-start and repeatable judge setup.

No Docker, IRIS, credentials or outbound network calls in these tests.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

MOCK_DOCKER = r'''#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
base = pathlib.Path(os.environ["MOCK_DIR"])
scenario = os.environ.get("MOCK_SCENARIO", "cold")
with (base / "calls").open("a") as f:
    f.write(" ".join(args) + "\n")
if args[:2] == ["image", "inspect"]:
    sys.exit(0)  # local EAP tag already loaded
if args[:2] == ["compose", "up"]:
    sys.exit(0)
if args and args[0] == "inspect":
    if ".State.Status" in args[2]:
        print("running")
    else:
        counter = base / "health_calls"
        n = int(counter.read_text()) if counter.exists() else 0
        counter.write_text(str(n + 1))
        if scenario == "unhealthy":
            print("unhealthy")
        elif scenario == "never_ready":
            print("starting")
        elif scenario == "cold" and n < 2:
            print("starting")
        else:
            print("healthy")
    sys.exit(0)
if args and args[0] == "exec":
    if scenario == "repeat":
        print("ANVIL INTEROP PRODUCTION ALREADY RUNNING; CLASSES NOT RECOMPILED")
    elif scenario == "install_failed":
        print("START FAILED: native installation rejected")
    else:
        print("ANVIL INTEROP PRODUCTION STARTED")
    sys.exit(0)
raise SystemExit("unsupported fake docker invocation: " + repr(args))
'''


class JudgeSetupTests(unittest.TestCase):
    def execute(self, scenario):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            docker = base / "docker"
            docker.write_text(MOCK_DOCKER)
            docker.chmod(0o755)
            for name, body in (
                ("setfacl", "#!/bin/sh\nexit 0\n"),
                ("sleep", "#!/bin/sh\nexit 0\n"),
                ("seq", "#!/bin/sh\nprintf '1\\n2\\n3\\n' \n"),
            ):
                target = base / name
                target.write_text(body)
                target.chmod(0o755)
            env = dict(os.environ, PATH=f"{temp}:{os.environ['PATH']}",
                       MOCK_DIR=temp, MOCK_SCENARIO=scenario,
                       OPENAI_API_KEY="fake-do-not-contact-provider")
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/setup.sh")],
                text=True, capture_output=True, timeout=10, env=env,
            )
            calls = (base / "calls").read_text().splitlines()
            return result, calls

    def test_cold_start_waits_for_health_before_native_install(self):
        result, calls = self.execute("cold")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Production started with freshly compiled classes", result.stdout)
        self.assertGreaterEqual(sum("Health.Status" in line for line in calls), 3)
        self.assertEqual(sum(line.startswith("exec ") for line in calls), 1)
        self.assertLess(next(i for i, line in enumerate(calls) if line.startswith("compose up")),
                        next(i for i, line in enumerate(calls) if line.startswith("exec ")))

    def test_refuses_unhealthy_production_without_running_install(self):
        result, calls = self.execute("unhealthy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("startup failed", result.stderr)
        self.assertFalse(any(line.startswith("exec ") for line in calls))

    def test_refuses_timeout_without_running_install(self):
        result, calls = self.execute("never_ready")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not become healthy", result.stderr)
        self.assertFalse(any(line.startswith("exec ") for line in calls))

    def test_existing_production_is_not_recompiled(self):
        result, calls = self.execute("repeat")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Existing production preserved", result.stdout)
        self.assertEqual(sum(line.startswith("exec ") for line in calls), 1)

    def test_native_install_failure_stays_failure(self):
        result, calls = self.execute("install_failed")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Installation/production start failed", result.stderr)
        self.assertEqual(sum(line.startswith("exec ") for line in calls), 1)


if __name__ == "__main__":
    unittest.main()
