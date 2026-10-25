"""agentdojo_analyse.py on a synthetic summary and progress file (needs matplotlib, which the host has)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analyse  # noqa: E402
import agentdojo_analyse as aa  # noqa: E402

try:
    import matplotlib  # noqa: F401
except ImportError:
    matplotlib = None


def cfg(asr, util):
    return {"asr": asr, "asr_ci95": [max(asr - 0.05, 0), asr + 0.05], "utility": util,
            "utility_ci95": [util - 0.1, util + 0.1], "utility_under_attack": util}


def summary(user_tasks, aborted=False, run_id="agentdojo_x"):
    return {"run_id": run_id, "user_tasks": user_tasks, "aborted": aborted, "code_version": "abc",
            "configs": {"b0": cfg(0.3, 0.6), "b1": cfg(0.0, 0.4), "d1hd2": cfg(0.0, 0.55)}}


def row(cfg_, kind, u, i, utility, success=None, errors=0, blocked=0):
    return {"config": cfg_, "kind": kind, "user_task": u, "injection_task": i, "utility": utility,
            "attack_success": success, "blocked": blocked, "calls": 3, "llm_errors": errors, "seconds": 1.0}


@unittest.skipIf(matplotlib is None, "matplotlib not installed")
class AgentDojoAnalyseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = analyse.RESULTS
        analyse.RESULTS = Path(self.tmp.name)

    def tearDown(self):
        analyse.RESULTS = self.old
        self.tmp.cleanup()

    def write(self, name, s):
        (analyse.RESULTS / name).write_text(json.dumps(s), encoding="utf-8")

    def test_full_run_gives_analysis_and_three_figures_and_spike_is_ignored(self):
        self.write("agentdojo_summary_20261025-075248.json", summary(4, run_id="agentdojo_spike"))
        self.write("agentdojo_summary_20261025-075616.json", summary(40))
        self.write("agentdojo_summary_20261026-000000.json", summary(4, run_id="agentdojo_spike2"))  # later spike
        rows = [row("b0", "utility", "u1", None, True), row("b0", "utility", "u2", None, False, errors=1),
                row("b0", "attack", "u1", "i1", False, True), row("b0", "attack", "u2", "i1", True, False),
                row("d1hd2", "utility", "u1", None, True), row("d1hd2", "utility", "u2", None, True, blocked=1),
                row("d1hd2", "attack", "u1", "i1", True, False, blocked=2),
                row("d1hd2", "attack", "u2", "i1", False, False, errors=1)]
        (analyse.RESULTS / "progress").mkdir()
        (analyse.RESULTS / "progress" / "agentdojo_x.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        self.assertEqual(aa.main(), 0)
        names = sorted(p.name for p in (analyse.RESULTS / "figures").iterdir())
        self.assertEqual(names, ["fig1_asr_vs_utility_agentdojo.png", "fig1_asr_vs_utility_col_agentdojo.png",
                                 "fig1_asr_vs_utility_slide_agentdojo.png"])
        out = json.loads((analyse.RESULTS / "analysis_agentdojo.json").read_text(encoding="utf-8"))
        b0u = out["configs"]["b0"]["utility"]
        self.assertEqual((b0u["timed_out_episodes"], b0u["utility_without_timeouts"]["k"],
                          b0u["utility_without_timeouts"]["n"]), (1, 1, 1))
        self.assertEqual(out["configs"]["b0"]["attack"]["asr"]["k"], 1)
        self.assertEqual(out["configs"]["d1hd2"]["attack"]["episodes_with_block"], 1)
        self.assertEqual(out["attack_successes"]["b0"], [["u1", "i1"]])
        m = out["mcnemar"]["b0_vs_d1hd2"]
        self.assertEqual((m["utility"]["d1hd2_only"], m["utility"]["b0_only"]), (1, 0))
        self.assertEqual((m["attack"]["d1hd2_only"], m["attack"]["b0_only"]), (1, 1))

    def test_nothing_for_aborted_or_missing_run(self):
        self.assertEqual(aa.main(), 1)
        self.write("agentdojo_summary_20261025-075616.json", summary(40, aborted=True))
        self.assertEqual(aa.main(), 1)
        self.assertFalse((analyse.RESULTS / "figures").exists())


if __name__ == "__main__":
    unittest.main()
