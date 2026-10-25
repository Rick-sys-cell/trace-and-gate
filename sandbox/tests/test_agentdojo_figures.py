"""agentdojo_figures.py on a synthetic summary (needs matplotlib, which the host has)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analyse  # noqa: E402
import agentdojo_figures as af  # noqa: E402

try:
    import matplotlib  # noqa: F401
except ImportError:
    matplotlib = None


def cfg(asr, util):
    return {"asr": asr, "asr_ci95": [max(asr - 0.05, 0), asr + 0.05], "utility": util,
            "utility_ci95": [util - 0.1, util + 0.1], "utility_under_attack": util}


def summary(user_tasks, aborted=False):
    return {"run_id": f"agentdojo_{user_tasks}", "user_tasks": user_tasks, "aborted": aborted,
            "configs": {"b0": cfg(0.3, 0.6), "b1": cfg(0.0, 0.4), "d1hd2": cfg(0.0, 0.55)}}


@unittest.skipIf(matplotlib is None, "matplotlib not installed")
class AgentDojoFigureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = analyse.RESULTS
        analyse.RESULTS = Path(self.tmp.name)

    def tearDown(self):
        analyse.RESULTS = self.old
        self.tmp.cleanup()

    def write(self, name, s):
        (analyse.RESULTS / name).write_text(json.dumps(s), encoding="utf-8")

    def test_full_run_gives_three_figures_and_spike_is_ignored(self):
        self.write("agentdojo_summary_20261025-075248.json", summary(4))
        self.write("agentdojo_summary_20261025-075616.json", summary(40))
        self.write("agentdojo_summary_20261026-000000.json", summary(4))  # a later spike must not win
        self.assertEqual(af.main(), 0)
        names = sorted(p.name for p in (analyse.RESULTS / "figures").iterdir())
        self.assertEqual(names, ["fig1_asr_vs_utility_agentdojo.png", "fig1_asr_vs_utility_col_agentdojo.png",
                                 "fig1_asr_vs_utility_slide_agentdojo.png"])

    def test_no_figure_for_aborted_or_missing_run(self):
        self.assertEqual(af.main(), 1)
        self.write("agentdojo_summary_20261025-075616.json", summary(40, aborted=True))
        self.assertEqual(af.main(), 1)
        self.assertFalse((analyse.RESULTS / "figures").exists())


if __name__ == "__main__":
    unittest.main()
