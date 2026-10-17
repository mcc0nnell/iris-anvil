"""Structural guard only; native IRIS execution is verified separately."""
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parents[1]
CLASS = BASE / "tools" / "recovery" / "RecoveryAudit.cls"
SCRIPT = BASE / "scripts" / "recovery-audit.scr"

class RecoveryAuditContractTests(unittest.TestCase):
    def test_optional_audit_is_read_only(self):
        source = CLASS.read_text()
        self.assertIn("Class Anvil.Interop.RecoveryAudit", source)
        for marker in ("PENDING_WITH_OUTBOX", "ORPHAN_OUTBOX",
                       "RECEIPT_WITHOUT_QUEUE", "COMPLETED",
                       "ANVIL_RECOVERY_AUDIT_SUMMARY"):
            self.assertIn(marker, source)
        self.assertIsNone(
            re.search(r"(?im)\b(?:set|kill|merge|zkill)\s+\^Anvil\.Interop\.", source),
            "Recovery audit must not assign or delete project globals",
        )
        for forbidden in ("SendRequestSync(", "Propose(", "StartProduction(", "StopProduction("):
            self.assertNotIn(forbidden, source)

    def test_operator_script_loads_only_audit(self):
        source = SCRIPT.read_text()
        self.assertIn('"/tmp/AnvilRecoveryAudit.cls"', source)
        self.assertIn("##class(Anvil.Interop.RecoveryAudit).Run()", source)
        self.assertNotIn("install.scr", source)

if __name__ == "__main__":
    unittest.main()
