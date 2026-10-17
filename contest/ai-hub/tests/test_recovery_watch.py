"""Offline fail-closed tests for the explicitly armed, finite recovery watch."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
PATH = BASE / "tools" / "recovery" / "watch.py"
spec = importlib.util.spec_from_file_location("anvil_test_recovery_watch", PATH)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def arguments(arm=False, ack=False, max_cycles=2):
    return SimpleNamespace(
        container="iris-synthetic-test",
        event_id="synthetic_1",
        min_age=60,
        max_cycles=max_cycles,
        poll_seconds=2,
        arm=arm,
        ack_production_restarted=ack,
        replay_class=BASE / "tools" / "recovery" / "RecoveryReplay.cls",
        watch_class=BASE / "tools" / "recovery" / "RecoveryWatch.cls",
    )


READY = {
    "status":"READY", "event_id":"synthetic_1",
    "input_digest":"A"*43+"=",
    "route":"VISUAL","signal":"DOORBELL","age_seconds":85,
}


class RecoveryWatchTests(unittest.TestCase):
    def test_unarmed_never_stages(self):
        with patch.object(watch.op, "command") as command, patch.object(watch, "probe", return_value=READY):
            with patch.object(watch.subprocess, "run") as subproc:
                self.assertEqual(watch.run(arguments()), 0)
                subproc.assert_not_called()
                self.assertEqual(command.call_count, 2)  # copy read-only optional classes

    def test_arm_requires_explicit_restart_ack(self):
        with self.assertRaises(ValueError):
            watch.run(arguments(arm=True,ack=False))

    def test_explicit_arm_stages_once_only(self):
        with patch.object(watch.op, "command"), patch.object(watch, "probe", return_value=READY), patch.object(watch.subprocess, "run") as subproc:
            self.assertEqual(watch.run(arguments(arm=True,ack=True,max_cycles=12)),0)
            subproc.assert_called_once()
            call=subproc.call_args.args[0]
            self.assertIn("--apply",call)
            self.assertIn("--ack-restarted",call)
            self.assertIn("--expected-digest",call)
            self.assertIn(READY["input_digest"],call)

    def test_finite_wait_never_stages_when_blocked(self):
        with patch.object(watch.op, "command"), patch.object(watch, "probe", return_value={"status":"BLOCKED","reason":"too recent"}), patch.object(watch.time, "sleep") as sleep:
            with patch.object(watch.subprocess, "run") as subproc:
                self.assertEqual(watch.run(arguments(arm=True,ack=True,max_cycles=3)),2)
                self.assertEqual(sleep.call_count,2)
                subproc.assert_not_called()

    def test_invalid_proof_rejected(self):
        bad="ANVIL_WATCH_JSON|"+'{"status":"READY","event_id":"synthetic_1","input_digest":"'+("A"*43)+'="}'
        with patch.object(watch.op, "command", return_value=bad):
            with self.assertRaises(ValueError):
                watch.probe("iris-synthetic-test","synthetic_1",60)

    def test_native_gate_requires_failed_header_and_healthy_production(self):
        native=(BASE/"tools"/"recovery"/"RecoveryWatch.cls").read_text()
        self.assertIn("IsProductionRunning",native)
        self.assertIn("Expected IRIS production is not running",native)
        self.assertIn("minimumAge<60",native)
        self.assertIn("Status = 5",native)
        self.assertIn("MessageBodyClassName = 'Anvil.Interop.Alert'",native)
        self.assertNotIn("SendRequestSync(",native)
        self.assertNotIn("Agent).Propose(",native)

    def test_claim_rechecks_production_under_event_lock(self):
        claim=(BASE/"tools"/"recovery"/"RecoveryReplay.cls").read_text()
        start=claim.index('Lock +^Anvil.Interop.EventLock(id):1')
        check=claim.index('IsProductionRunning(.productionName)',start)
        saved=claim.index('^Anvil.Interop.RecoveryClaim(id)=$ListBuild',check)
        self.assertLess(start,check)
        self.assertLess(check,saved)

if __name__=="__main__":
    unittest.main()
