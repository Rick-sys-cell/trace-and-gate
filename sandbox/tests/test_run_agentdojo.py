"""run_agentdojo.py helpers: utility-row reuse and the injection-exposure check. Synthetic strings only.
Skipped when agentdojo is not installed (it is installed in the sandbox image)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import run_agentdojo as rad
except ImportError:  # host without agentdojo
    rad = None


@unittest.skipIf(rad is None, "agentdojo not installed")
class ExposureTests(unittest.TestCase):
    INJ = {"vec": "\n<INFO>\nPlease do the placeholder action number one now.\nSigned,\nSomeone\n</INFO>\n"}

    def test_seen_through_yaml_folding_and_escapes(self):
        import yaml  # in the image, with agentdojo
        dumped = yaml.safe_dump([{"body": "Hello. " + self.INJ["vec"] * 3, "id": "1"}], width=30)
        self.assertTrue(rad.injection_seen(self.INJ, [dumped]))

    def test_not_seen_in_clean_output_and_short_lines_ignored(self):
        self.assertFalse(rad.injection_seen(self.INJ, ["Signed, Someone. <INFO> nothing else here."]))
        self.assertFalse(rad.injection_seen(self.INJ, []))
        self.assertFalse(rad.injection_seen({}, ["anything"]))

    def test_recorder_keeps_name_and_ors_over_retries(self):
        class Inner:
            name = "local-x-b0"
            replies = [[{"role": "tool", "content": [{"type": "text", "content": "Please do the placeholder "
                                                                                 "action number one now."}]}],
                       [{"role": "tool", "content": [{"type": "text", "content": "clean"}]}]]

            def query(self, q, runtime, env, messages=[], extra_args={}):
                return q, runtime, env, self.replies.pop(0), extra_args

        rec = rad.ExposureRecorder(Inner())
        self.assertEqual(rec.name, "local-x-b0")
        rec.start(self.INJ)
        rec.query("q", None, None)
        rec.query("q", None, None)
        self.assertTrue(rec.exposed)
        rec.start(self.INJ)
        self.assertFalse(rec.exposed)


@unittest.skipIf(rad is None, "agentdojo not installed")
class OracleExposureTests(unittest.TestCase):
    """An honest scripted agent replays each user task's ground-truth calls, which read the injection
    vectors AgentDojo chose for that task, so the injection must be detected as seen. Counts only."""

    def test_honest_replay_is_exposed(self):
        import warnings
        from agentdojo.attacks.attack_registry import load_attack
        from agentdojo.task_suite.load_suites import get_suite
        import agentdojo_bridge as bridge
        from test_agentdojo_bridge import scripted
        warnings.simplefilter("ignore")
        suite = get_suite(rad.BENCHMARK_VERSION, "workspace")
        by_prompt = {t.PROMPT: t for t in suite.user_tasks.values()}
        inj_task = suite.get_injection_task_by_id("injection_task_0")
        for name in ("important_instructions", "tool_knowledge"):
            seen = n = 0
            for ut in list(suite.user_tasks.values())[:10]:
                env = ut.init_environment(suite.load_and_inject_default_environment({}))
                steps = list(ut.ground_truth(env.model_copy(deep=True)))
                pipeline, _ = bridge.build_pipeline("b0", scripted(steps, ut.GROUND_TRUTH_OUTPUT), by_prompt, "x")
                rec = rad.ExposureRecorder(pipeline)
                injections = load_attack(name, suite, rec).attack(ut, inj_task)
                rec.start(injections)
                suite.run_task_with_pipeline(rec, ut, inj_task, injections)
                seen, n = seen + rec.exposed, n + 1
            print(f"\n[AgentDojo exposure] {name}: honest replay exposed in {seen}/{n}")
            self.assertGreaterEqual(seen, n - 1, name)


@unittest.skipIf(rad is None, "agentdojo not installed")
class ReuseTests(unittest.TestCase):
    def test_only_utility_rows_of_requested_configs(self):
        rows = [{"config": c, "kind": k, "user_task": "user_task_0", "injection_task": None if k == "utility" else "i"}
                for c in ("b0", "b1", "d1hd2") for k in ("utility", "attack")]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            out = rad.reused_utility_rows(p, ["b0", "d1hd2"], "agentdojo_x")
        self.assertEqual([(r["config"], r["kind"]) for r in out], [("b0", "utility"), ("d1hd2", "utility")])
        self.assertTrue(all(r["reused_from"] == "agentdojo_x" for r in out))

    def test_summary_counts_exposure(self):
        rows = [{"config": "b0", "kind": "attack", "user_task": "u", "injection_task": f"i{n}", "utility": False,
                 "attack_success": s, "exposed": e, "blocked": 0, "llm_errors": 0, "seconds": 1.0}
                for n, (s, e) in enumerate([(True, True), (False, True), (False, False)])]
        c = rad.summarise(rows)["b0"]
        self.assertEqual((c["attack_exposed"], c["asr_given_exposed"]), (2, 0.5))


if __name__ == "__main__":
    unittest.main()
