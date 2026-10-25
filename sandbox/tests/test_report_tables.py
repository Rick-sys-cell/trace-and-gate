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
                                             "benign": {"other_only": 2, "d1hd2_only": 2, "p": 1.0}}}}))
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
        self.assertIn("PENDING", md)  # dev, qwen, AgentDojo... missing here
        self.assertEqual(sorted(out["sources"]), ["block_reasons_links", "heldout"])


if __name__ == "__main__":
    unittest.main()
