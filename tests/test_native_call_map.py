"""Hermetic test compiling our own simple C fixture, not vendor code."""
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/map_native_calls.py"
spec = importlib.util.spec_from_file_location("native_call_map", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NativeCallMapTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gcc") and shutil.which("nm") and shutil.which("objdump"),
                         "GNU compiler/binutils unavailable")
    def test_direct_calls_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, binary = root / "fixture.c", root / "fixture.so"
            src.write_text(
                '__attribute__((noinline, visibility("default"))) int leaf(int x) {return x+1;}\n'
                '__attribute__((noinline, visibility("default"))) int branch(int x) {return leaf(x)+3;}\n'
            )
            subprocess.run(["gcc", "-shared", "-fPIC", "-O0", "-o", str(binary), str(src)], check=True)
            result = module.map_native_calls(binary, ["branch", "leaf"])
            self.assertEqual(result["authority"], "NONE")
            self.assertEqual(len(result["sha256"]), 64)
            self.assertTrue(any(e["from"] == "branch" and
                                e["to"].split("@")[0].split("+")[0] == "leaf"
                                for e in result["edges"]))
            self.assertGreater(result["functions"]["branch"]["direct_calls"], 0)
            with self.assertRaisesRegex(ValueError, "Requested symbols missing"):
                module.map_native_calls(binary, ["missing"])

if __name__ == "__main__":
    unittest.main()
