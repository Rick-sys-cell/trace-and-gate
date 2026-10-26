"""report_tables.py on synthetic result files."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import report_tables as rt  # noqa: E402


def rate(k, n):
    return {"k": k, "n": n, "rate": k / n, "ci95": [0.1, 0.2]}


CFG = {"label": "x", "asr": rate(44, 97), "utility": rate(50, 56), "utility_under_attack": rate(49, 97),
       "mean_seconds": 4.5, "mean_llm_calls": 4.1, "mean_reader_calls": 0.0, "mean_tokens": 2510.0}


class ReportTablesTests(unittest.TestCase):
    def test_tables_and_pending(self):
        with tempfile.TemporaryDirectory() as d:
            rt.RESULTS = Path(d)
            (rt.RESULTS / "analysis_heldout.json").write_text(json.dumps(
                {"run_id": "r1", "model": "m", "runs": 3, "aborted": False, "configs": {"b0": CFG, "d1hd2": CFG},
                 "mcnemar": {"d1hd2_vs_b0": {"attack": {"other_only": 44, "d1hd2_only": 0, "p": 1e-13},
                                             "benign": {"other_only": 2, "d1hd2_only": 2, "p": 1.0}}},
                 "per_run": {"b0": {"run0": {"asr": 0.3, "utility": 0.9}, "run1": {"asr": 0.35, "utility": 0.85}}},
                 "by_source": {"b0": {"team": {"asr": rate(18, 54), "utility_under_attack": rate(10, 54)},
                                      "llmail": {"asr": rate(38, 120), "utility_under_attack": rate(46, 120)}},
                               "d1hd2": {"team": {"asr": rate(0, 54), "utility_under_attack": rate(30, 54)},
                                         "llmail": {"asr": rate(0, 120), "utility_under_attack": rate(58, 120)}}},
                 "by_style": {"b0": {"disguised-link": {"asr": rate(9, 18), "utility_under_attack": rate(3, 18)}}}}))
            (rt.RESULTS / "block_reasons_links.json").write_text(json.dumps({"configs": {"d1h": {
                "benign_episodes": 40, "benign_episodes_with_block": 16, "false_blocks": {"d1_untrusted_url": ["a"]},
                "isolation": {}, "link_flows": {"send-link": {"n": 8, "utility": 0, "blocked": 8,
                                                              "blocked_by_url_rule": 8}}}}}))
            rt.build()
            md = (rt.RESULTS / "final_tables.md").read_text(encoding="utf-8")
            out = json.loads((rt.RESULTS / "final_tables.json").read_text(encoding="utf-8"))
        self.assertIn("| B0 none | 45.4% (44/97) | 10.0–20.0% | 89.3% (50/56)", md)
        self.assertIn("attacks succeeded only under B0 none 44, only under D1h+D2 0", md)
        self.assertIn("| send-link | 0.0% (0/8), blocked 8 |", md)
        self.assertIn("| Team-written | 33.3% (18/54); task done 18.5% (10/54) | 0.0% (0/54); task done 55.6% (30/54) |", md)
        self.assertIn("| LLMail-Inject | 31.7% (38/120)", md)
        self.assertIn("| disguised-link | 50.0% (9/18)", md)
        self.assertIn("Per run (attack success / normal tasks done): B0 none 30.0/90.0, 35.0/85.0", md)
        self.assertIn("PENDING", md)  # dev, qwen, AgentDojo... missing here
        self.assertEqual(sorted(out["sources"]), ["block_reasons_links", "heldout"])


def ad_summary(run_id, attack, exposed=None, **extra):
    c = {"n_utility": 40, "utility": 0.275, "utility_ci95": [0.16, 0.43], "n_attack": 80, "asr": 0.15,
         "asr_ci95": [0.09, 0.24], "utility_under_attack": 0.3, "false_block_episodes": 0, "mean_seconds": 30.0}
    if exposed is not None:
        c.update(attack_exposed=exposed, asr_given_exposed=0.25)
    return {"run_id": run_id, "suite": "workspace v1.2.2", "attack": attack, "user_tasks": 40, "pairs_per_task": 2,
            "model": "qwen3:8b", "agentdojo_version": "0.1.35", "aborted": False, "configs": {"b0": c}, **extra}


class AgentDojoTablesTests(unittest.TestCase):
    def test_one_block_per_attack_first_attack_first_and_spike(self):
        with tempfile.TemporaryDirectory() as d:
            rt.RESULTS = Path(d)
            for name, s in (("agentdojo_summary_20261025-075616.json", ad_summary("a1", "important_instructions")),
                            ("agentdojo_summary_20261026-040133.json", {**ad_summary("sp", "tool_knowledge"),
                                                                         "user_tasks": 24}),
                            ("agentdojo_summary_20261026-090000.json",
                             ad_summary("a2", "tool_knowledge", exposed=48, utility_from="a1"))):
                (rt.RESULTS / name).write_text(json.dumps(s))
            (rt.RESULTS / "analysis_agentdojo_spike.json").write_text(json.dumps({
                "tool_knowledge": {"run_id": "sp", "seed": 3202, "user_tasks": 24, "asr": rate(6, 24),
                                   "timed_out_episodes": 1, "exposed": rate(18, 24), "asr_given_exposed": rate(6, 18)},
                "injecagent": {"run_id": "sp2", "seed": 3202, "user_tasks": 24, "asr": rate(0, 24),
                               "timed_out_episodes": 0}}))
            rt.build()
            md = (rt.RESULTS / "final_tables.md").read_text(encoding="utf-8")
            out = json.loads((rt.RESULTS / "final_tables.json").read_text(encoding="utf-8"))
        self.assertEqual((out["agentdojo"]["run_id"], out["agentdojo_tool_knowledge"]["run_id"]), ("a1", "a2"))
        self.assertLess(md.index("AgentDojo workspace: `important_instructions`"),
                        md.index("AgentDojo workspace: `tool_knowledge`"))
        self.assertIn("no-attack episodes reused from `a1`", md)
        self.assertIn("Injection reached the model in a tool result: B0 none 48/80 (attack success when reached 25.0%)", md)
        self.assertIn("| `tool_knowledge` | 25.0% (6/24) | 75.0% (18/24) | 33.3% (6/18) | 1/24 |", md)
        self.assertIn("| `injecagent` | 0.0% (0/24) | – | – | 0/24 |", md)


class AttackSourceTests(unittest.TestCase):
    def test_source(self):
        import analyse
        self.assertEqual(analyse.source({"id": "attack-heldout-ho-cal-g1-finance-finance", "type": "attack", "goal": "g1"}), "team")
        self.assertEqual(analyse.source({"id": "attack-llmail-llh-01-course", "type": "attack", "goal": "llmail"}), "llmail")
        self.assertEqual(analyse.source({"id": "attack-g1-body-1-club", "type": "attack", "goal": "g1"}), "template")
        self.assertIsNone(analyse.source({"id": "benign-1", "type": "benign"}))


if __name__ == "__main__":
    unittest.main()
