"""Offline fail-closed tests for the one-shot genuine agent contest demonstration."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/golden-path.py"
spec = importlib.util.spec_from_file_location("anvil_golden", SCRIPT)
golden = importlib.util.module_from_spec(spec)
spec.loader.exec_module(golden)


def good():
    return {
        "status": "COMPLETE", "event_id": "golden-doorbell-abcdef",
        "signal": "DOORBELL", "proposal": "BOTH", "route": "BOTH",
        "receipt": "a", "queue_count": 1, "inbound_header_count": 1,
        "failed_inbound_headers": 0,
        "pending_cleared": True,
        "queue_payload_ok": True, "outbox_matches": True,
        "policy_matches": True, "receipt_matches": True,
    }


class GoldenPathTests(unittest.TestCase):
    def test_parses_one_complete_state(self):
        line = "USER>\nANVIL_GOLDEN_STATE|{\"status\":\"COMPLETE\"}\n"
        self.assertEqual(golden.state_from_irissession(line)["status"], "COMPLETE")

    def test_refuses_spoofed_duplicate_and_missing_markers(self):
        good_line = 'ANVIL_GOLDEN_STATE|{"status":"PENDING"}'
        for transcript in ("FAKE_" + good_line, good_line + "\n" + good_line, ""):
            with self.subTest(transcript=transcript), self.assertRaises(ValueError):
                golden.state_from_irissession(transcript)

    def test_refuses_native_diagnostics_even_after_success(self):
        line = 'ANVIL_GOLDEN_STATE|{"status":"COMPLETE"}\n<UNDEFINED> bad'
        with self.assertRaises(RuntimeError):
            golden.state_from_irissession(line)

    def test_rejects_incomplete_or_mismatched_durable_state(self):
        golden.require_good_state(good(), "golden-doorbell-abcdef")
        for key, value in (
            ("event_id", "other"), ("signal", "SMOKE"),
            ("queue_count", 2), ("inbound_header_count", 0),
            ("failed_inbound_headers", 1),
            ("pending_cleared", False),
            ("queue_payload_ok", False), ("outbox_matches", False),
            ("policy_matches", False), ("receipt_matches", False),
            ("route", "VISUAL"),
        ):
            d = good()
            d[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                golden.require_good_state(d, "golden-doorbell-abcdef")

    def test_observer_does_not_write_project_globals(self):
        source = (ROOT / "scripts/golden-state.scr").read_text()
        for text in ("set ^Anvil.Interop.", "kill ^Anvil.Interop.",
                     "StartProduction(", "Agent).Propose(", "SendRequestSync("):
            self.assertNotIn(text, source.lower() if text == text.lower() else source)


if __name__ == "__main__":
    unittest.main()
