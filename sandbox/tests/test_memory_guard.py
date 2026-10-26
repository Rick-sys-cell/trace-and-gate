"""tools/memory_guard.py: flag hysteresis (host only; no Docker or Ollama needed)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import memory_guard as mg  # noqa: E402


class StepTests(unittest.TestCase):
    def test_set_renew_hold_and_clear(self):
        with tempfile.TemporaryDirectory() as d:
            flag = Path(d) / "memory_low.flag"
            step = lambda free, ollama: mg.step(flag, free, ollama, 2.0, 3.0, 7.0)  # noqa: E731
            self.assertFalse(step(8.0, 0.1))   # model unloaded
            self.assertFalse(step(2.5, 5.5))   # freshly loaded qwen3:8b (measured): must not fire
            self.assertTrue(step(1.8, 5.6))    # low free RAM: set
            first = flag.read_text(encoding="ascii")
            self.assertTrue(step(2.6, 5.6))    # between thresholds: held and renewed
            self.assertGreaterEqual(flag.read_text(encoding="ascii"), first)
            self.assertFalse(step(7.9, 0.1))   # runner unloaded the model: cleared
            self.assertTrue(step(4.0, 7.5))    # Ollama grew past its cap with RAM to spare: set
            self.assertFalse(step(8.0, 0.1))
            self.assertFalse(flag.exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows API")
    def test_free_memory_reading(self):
        self.assertGreater(mg.free_gb(), 0)


if __name__ == "__main__":
    unittest.main()
