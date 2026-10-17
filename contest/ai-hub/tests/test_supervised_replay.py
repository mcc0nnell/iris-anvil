"""Offline checks for the human-gated recovery operator; native tests separate."""
import importlib.util
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "tools" / "recovery" / "operator.py"
CLASS = BASE / "tools" / "recovery" / "RecoveryReplay.cls"
spec = importlib.util.spec_from_file_location("irisanvil_replay_operator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SupervisedReplayTests(unittest.TestCase):
    def test_marker_requires_exact_single_response(self):
        self.assertEqual(
            mod.parse_result('USER>\nANVIL_OPERATOR_JSON|{"status":"READY"}\n')["status"],
            "READY",
        )
        for raw in (
            'FAKE_ANVIL_OPERATOR_JSON|{"status":"READY"}',
            'ANVIL_OPERATOR_JSON|{"status":"READY"}\nANVIL_OPERATOR_JSON|{"status":"READY"}',
            '<SYNTAX>\nANVIL_OPERATOR_JSON|{"status":"READY"}',
            'ERROR #5002: bad\nANVIL_OPERATOR_JSON|{"status":"READY"}',
            'ANVIL_OPERATOR_JSON|{"status":"QUEUED"}',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                mod.parse_result(raw)

    def test_event_and_digest_reject_command_injection(self):
        for bad in ('', '../../escape', 'id";kill ^Global', ' ' * 6, 'a' * 65):
            with self.subTest(event=bad):
                self.assertIsNone(mod.EVENT_RE.fullmatch(bad))
        for bad in ("bad", "AAA\n", "A" * 44, "x" * 43 + "!"):
            with self.subTest(digest=bad):
                self.assertIsNone(mod.SHA_RE.fullmatch(bad))

    def test_writer_uses_exclusive_atomic_staging(self):
        self.assertIn('os.link(temp, final)', mod.WRITER)
        self.assertIn('os.fsync(f.fileno())', mod.WRITER)
        self.assertIn('suffix=".part"', mod.WRITER)
        self.assertNotIn('os.replace(', mod.WRITER)

    def test_irrespective_of_model_no_reinference_in_operator(self):
        source = CLASS.read_text()
        self.assertIn('Lock +^Anvil.Interop.EventLock(id):1', source)
        self.assertIn('^Anvil.Interop.RecoveryClaim(id)', source)
        self.assertIn('Saved route violates current policy', source)
        self.assertIn('Outbox digest absent or mismatched', source)
        self.assertIn('Conflicting secondary queue entry', source)
        for forbidden in ('agent.Chat(', '.Propose(', 'SendRequestSync(', 'StartProduction('):
            self.assertNotIn(forbidden, source)

    def test_ownership_separate_from_production(self):
        source = (BASE / 'src' / 'Anvil' / 'Interop')
        self.assertFalse((source / 'RecoveryReplay.cls').exists())
        self.assertFalse((source / 'RecoveryAudit.cls').exists())


if __name__ == "__main__":
    unittest.main()
