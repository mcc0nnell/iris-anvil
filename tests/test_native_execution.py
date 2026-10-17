"""Synthetic tests: no IRIS binary, debugger, or service required."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_native_execution.py"
spec = importlib.util.spec_from_file_location("verify_native_execution", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SESSION = """USER>
PHASE_READY|42|67860,100
USER>
PHASE_START|67860,101
USER>
PHASE_SET|67860,102
USER>
PHASE_COMMIT|67860,103
USER>
PHASE_VERIFIED|0|phase
USER>
PHASE_CLEAN|0
"""
TRACE = """Breakpoint 1 at 0x1234
PHASE_HIT|gsetjrn|14:21:22.001
#0  0x1234 in gsetjrn ()
#1  0x2345 in Cgset ()
PHASE_HIT|journalset|14:21:22.002
#0  0x3456 in journalset ()
#1  0x4567 in gsetjrn ()
PHASE_HIT|journaltran|14:21:22.003
#0  0x5678 in journaltran ()
#1  0x6789 in journalset ()
PHASE_HIT|journaltran|14:21:22.004
#0  0x5678 in journaltran ()
#1  0x9999 in Ctcommit ()
[Inferior 1 (process 42) exited normally]
"""

class VerifierTests(unittest.TestCase):
    def check(self, session=SESSION, debugger=TRACE):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            s, g, b = (d / n for n in ("session.log", "gdb.log", "fixture.bin"))
            s.write_text(session)
            g.write_text(debugger)
            b.write_bytes(b"synthetic fixture only")
            return mod.verify(s, g, b)

    def test_success(self):
        r = self.check()
        self.assertEqual(r["worker_pid"], 42)
        self.assertEqual(r["authority"], "NONE")
        self.assertEqual(len(r["required_paths_observed"]), 4)

    def test_wrong_pid(self):
        with self.assertRaisesRegex(ValueError, "normal exit"):
            self.check(debugger=TRACE.replace("process 42", "process 43"))

    def test_missing_commit_stack(self):
        with self.assertRaisesRegex(ValueError, "Ctcommit"):
            self.check(debugger=TRACE.replace("in Ctcommit", "in unrelated"))

    def test_missing_cleanup(self):
        with self.assertRaisesRegex(ValueError, "phase markers"):
            self.check(session=SESSION.replace("PHASE_CLEAN|0", ""))

    def test_duplicate_phase(self):
        with self.assertRaisesRegex(ValueError, "phase markers"):
            self.check(session=SESSION + "PHASE_START|67860,999\n")

    def test_missing_phase(self):
        with self.assertRaisesRegex(ValueError, "phase markers"):
            self.check(session=SESSION.replace("PHASE_START|", "PHASE_WRONG|"))

    def test_rejects_debugger_error(self):
        with self.assertRaisesRegex(ValueError, "fatal"):
            self.check(debugger=TRACE + "ptrace: No such process\n")

if __name__ == "__main__":
    unittest.main()
