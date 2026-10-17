"""Offline tests for the runtime-evidence verifier; no IRIS image needed."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "runtime_log_verifier", HERE / "scripts" / "verify-runtime-log.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RuntimeLogVerifierTests(unittest.TestCase):
    @staticmethod
    def good(stage):
        label = stage.upper()
        names = mod.CLASSES if stage == "compile" else [
            "|".join(case) for case in mod.CASES
        ]
        return "\n".join(
            [f"ANVIL_{label}_BEGIN"]
            + [f"ANVIL_{label}_PASS|{name}" for name in names]
            + [f"ANVIL_{label}_SUMMARY|pass={len(names)}|fail=0", ""]
        )

    def test_compile_complete(self):
        mod.validate(self.good("compile"), "compile")

    def test_policy_complete(self):
        mod.validate(self.good("policy"), "policy")

    def test_rejects_missing_class(self):
        text = self.good("compile").replace("ANVIL_COMPILE_PASS|Agent\n", "")
        with self.assertRaises(ValueError):
            mod.validate(text, "compile")

    def test_rejects_failed_class(self):
        text = self.good("compile").replace(
            "ANVIL_COMPILE_PASS|Agent", "ANVIL_COMPILE_FAIL|Agent|ERROR"
        )
        with self.assertRaises(ValueError):
            mod.validate(text, "compile")

    def test_rejects_failed_policy(self):
        text = self.good("policy").replace(
            "ANVIL_POLICY_PASS|SMOKE|VISUAL|BOTH",
            "ANVIL_POLICY_FAIL|SMOKE|VISUAL|VISUAL|expected=BOTH",
        )
        with self.assertRaises(ValueError):
            mod.validate(text, "policy")

    def test_rejects_bad_summary(self):
        for stage in ("compile", "policy"):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                mod.validate(self.good(stage).replace("|fail=0", "|fail=1"), stage)

    def test_rejects_duplicate_and_incomplete_output(self):
        for stage in ("compile", "policy"):
            with self.subTest(stage=stage):
                text = self.good(stage)
                for sample in (text + text, text.split("SUMMARY")[0], ""):
                    with self.assertRaises(ValueError):
                        mod.validate(sample, stage)

if __name__ == "__main__":
    unittest.main()
