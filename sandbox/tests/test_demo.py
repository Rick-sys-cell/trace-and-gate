"""Offline test of the demo script's --oracle mode (no model, no Docker)."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import demo  # noqa: E402
import run_eval  # noqa: E402

SUITE = ROOT / "benchmark" / "tasks" / "email_suite_v3.json"


@unittest.skipUnless((ROOT / "benchmark" / "payloads" / "templates_v3.json").exists(),
                     "v3 payloads not built (python benchmark/build_suite.py --version 3)")
class DemoTests(unittest.TestCase):
    def setUp(self):
        run_eval.BENCH = ROOT / "benchmark"
        demo.USE_COLOR = False

    def _run(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = demo.main(["--oracle", "--suite", str(SUITE), *args])
        return rc, out.getvalue()

    def test_default_task_b0_hijacked_defenses_block(self):
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("Summary: B0 hijacked   D2 safe   D1h safe   D1h+D2 safe", out)
        self.assertNotIn("not done", out)  # the user's task still gets done under every defense

    def test_split_multiturn_shows_d2_gap(self):
        rc, out = self._run("--task", "attack-g2-multiturn-1-research")
        self.assertIn("D2 hijacked", out)
        self.assertIn("D1h+D2 safe", out)

    def test_default_output_has_no_attack_text(self):
        _, out = self._run()
        payloads = run_eval.load_payloads()
        for text in payloads.values():
            if isinstance(text, str) and len(text) > 40:
                self.assertNotIn(text[:40], out)

    def test_b1_needs_live(self):
        rc, _ = self._run("--configs", "b0", "b1")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
