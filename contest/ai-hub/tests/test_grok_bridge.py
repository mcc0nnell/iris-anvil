"""Offline-only protocol-contract checks for the optional Grok bridge."""
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "grok" / "bridge.py"
spec = importlib.util.spec_from_file_location("grok_bridge_test_module", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class GrokBridgeTests(unittest.TestCase):
    def test_canonical_grok_responses(self):
        for token in sorted(mod.ROUTES):
            with self.subTest(token=token):
                self.assertEqual(
                    mod.parse_grok_reply(json.dumps({"text":token, "stopReason":"end_turn"})),
                    token,
                )

    def test_reject_invalid_model_output(self):
        bad = [
            {"text":"BOTH.", "stopReason":"end_turn"},
            {"text":"both", "stopReason":"end_turn"},
            {"text":"BOTH", "stopReason":"tool_use"},
            {"type":"error", "text":"BOTH", "stopReason":"end_turn"},
            {"text":None, "stopReason":"end_turn"},
            {"text":"VISUAL and HAPTIC", "stopReason":"end_turn"},
        ]
        for obj in bad:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                mod.parse_grok_reply(json.dumps(obj))

    def test_allowed_synthetic_input(self):
        for signal in sorted(mod.SIGNALS):
            result, body = mod.synthetic_signal({
                "messages":[{"role":"user", "content":f"Signal: {signal}\nDetail: Testing"}],
            })
            self.assertEqual(result, signal)
            self.assertIn("Signal: ", body)

    def test_reject_unknown_signal(self):
        for body in ("Signal: UNKNOWN\nDetail: Test", "hello", "Signal: DOORBELLX\nDetail: Test"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                mod.synthetic_signal({"messages":[{"role":"user","content":body}]})

    def test_reject_oversized_input(self):
        with self.assertRaises(ValueError):
            mod.synthetic_signal({"messages":[{"role":"user","content":"Signal: DOORBELL\n"+("X"*2001)}]})

if __name__ == "__main__":
    unittest.main()
