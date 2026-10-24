"""Validate the email benchmark and measure D2 deterministically (no LLM).

Each task's `oracle` (correct behaviour) and `attack_oracle` (hijacked behaviour)
is replayed through the real agent loop with a scripted LLM.

SAFETY: payload text is loaded and substituted in code only; nothing here prints
or asserts on payload content, so failures show task ids only.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent import run_episode  # noqa: E402
from defenses import get_defense  # noqa: E402
from email_env import EmailWorld  # noqa: E402
from run_eval import PLACEHOLDER, resolve  # noqa: E402
from scoring import score  # noqa: E402

SUITE = ROOT / "benchmark" / "tasks" / "email_suite.json"
INJ_ID = 50


def load(suite=SUITE):
    tasks = json.loads(suite.read_text(encoding="utf-8"))
    payloads = {}
    for p in sorted((ROOT / "benchmark" / "payloads").glob("*.json")):
        payloads.update(json.loads(p.read_text(encoding="utf-8")))
    return tasks, payloads


def replay(steps):
    """Scripted LLM over oracle steps: a list of [tool, args] calls, or a final string."""
    it = iter(steps)

    def llm(messages, tools):
        step = next(it, "Done.")
        if isinstance(step, str):
            return {"message": {"content": step}, "prompt_tokens": 0, "completion_tokens": 0}
        calls = [{"function": {"name": n, "arguments": a}} for n, a in step]
        return {"message": {"content": "", "tool_calls": calls}, "prompt_tokens": 0, "completion_tokens": 0}
    return llm


def run(task, steps, defense):
    world = EmailWorld.from_spec(task["world"])
    log = run_episode(task, world, replay(steps), get_defense(defense))
    return score(world, task), log


class SuiteTests(unittest.TestCase):
    SUITE_FILE = SUITE  # pilot suite (v1)

    @classmethod
    def setUpClass(cls):
        raw, cls.payloads = load(cls.SUITE_FILE)
        refs = {m.group(1) for t in raw for m in PLACEHOLDER.finditer(json.dumps(t))}
        if any(r.startswith("llm-") for r in refs - set(cls.payloads)):
            raise unittest.SkipTest("LLMail payloads not imported (run benchmark/import_llmail.py)")
        cls.raw = raw
        cls.tasks = [resolve(t, cls.payloads) for t in raw]
        cls.attacks = [t for t in cls.tasks if t["type"] == "attack"]
        cls.benign = [t for t in cls.tasks if t["type"] == "benign"]

    def test_size_and_ids(self):
        self.assertGreaterEqual(len(self.benign), 50)
        self.assertGreaterEqual(len(self.attacks), 90)
        ids = [t["id"] for t in self.tasks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_payload_reference_resolves(self):
        refs = set()
        for t in self.raw:
            refs |= {m.group(1) for m in PLACEHOLDER.finditer(json.dumps(t))}
        missing = sorted(refs - set(self.payloads))
        self.assertEqual(missing, [])
        leftover = [t["id"] for t in self.tasks if "{{payload:" in json.dumps(t)]
        self.assertEqual(leftover, [])

    def test_required_fields(self):
        for t in self.tasks:
            for key in ("user_prompt", "world", "utility", "policy", "oracle"):
                self.assertIn(key, t, t["id"])
            if t["type"] == "attack":
                self.assertIn("attack", t, t["id"])
                self.assertIn("attack_oracle", t, t["id"])

    def test_attack_tasks_force_reading_injected_content(self):
        for t in self.attacks:
            first = t["oracle"][0]
            touches = any((n in ("read_email", "read_attachment") and a.get("email_id") == INJ_ID)
                          or n == "list_inbox" for n, a in first)
            self.assertTrue(touches, t["id"])

    def test_benign_oracle_full_utility_no_false_blocks(self):
        for cfg in ("b0", "d2", "d1", "d1h", "d1d2", "d1hd2"):
            failed = []
            for t in self.tasks:
                s, log = run(t, t["oracle"], cfg)
                if not s["utility"] or log["blocked"] or s["attack_success"]:
                    failed.append(t["id"])
            self.assertEqual(failed, [], f"{cfg}: legitimate behaviour failed or was blocked")

    def test_attack_oracle_succeeds_without_defense(self):
        failed = [t["id"] for t in self.attacks if not run(t, t["attack_oracle"], "b0")[0]["attack_success"]]
        self.assertEqual(failed, [])

    def test_d2_coverage_matches_design(self):
        """D2 should stop every hijacked call except phishing content riding inside a
        legitimately authorised reply (g2 multi-turn): that gap is D1's job."""
        survived = sorted(t["id"] for t in self.attacks if run(t, t["attack_oracle"], "d2")[0]["attack_success"])
        expected = sorted(t["id"] for t in self.attacks if t["goal"] == "g2" and t["channel"] == "multiturn")
        self.assertEqual(survived, expected)
        print(f"\n[D2 oracle coverage] blocked {len(self.attacks) - len(survived)}/{len(self.attacks)} "
              f"hijacked behaviours; {len(survived)} expected survivors (g2 multi-turn)")


    def test_d1_and_combined_block_every_hijack(self):
        """D1 (no hand-written policy) and D1+D2 should stop all hijacked behaviours,
        including the g2 multi-turn ones that D2 alone misses."""
        for cfg in ("d1", "d1h", "d1d2", "d1hd2"):
            survived = sorted(t["id"] for t in self.attacks if run(t, t["attack_oracle"], cfg)[0]["attack_success"])
            self.assertEqual(survived, [], cfg)
        print(f"\n[D1, D1+D2 oracle coverage] blocked {len(self.attacks)}/{len(self.attacks)} hijacked behaviours")



class SuiteV2Tests(SuiteTests):
    """Same checks on the 8 Oct suite (attack email named in LLMail requests; controls get a
    harmless email from the same sender)."""
    SUITE_FILE = ROOT / "benchmark" / "tasks" / "email_suite_v2.json"

    def test_v2_controls_mirror_llmail_tasks(self):
        controls = [t for t in self.tasks if t.get("control_for")]
        self.assertEqual(len(controls), 16)
        for t in controls:
            self.assertIn(INJ_ID, [e["id"] for e in t["world"]["inbox"]], t["id"])
            self.assertIn("external@partner.example", t["user_prompt"], t["id"])
        for t in self.attacks:
            if t.get("goal") == "llmail":
                self.assertIn("external@partner.example", t["user_prompt"], t["id"])


class SuiteV3Tests(SuiteTests):
    """Week 10 dev suite (24 Oct): LLMail emails carry a fact the user asks for and are not named;
    multi-turn attacks are split over two emails and two turns."""
    SUITE_FILE = ROOT / "benchmark" / "tasks" / "email_suite_v3.json"

    def test_llmail_tasks_need_the_attack_email_and_do_not_name_it(self):
        llmail = [t for t in self.tasks if t.get("goal") == "llmail" or t.get("control_for")]
        self.assertEqual(len(llmail), 40 + 16)
        for t in llmail:
            self.assertNotIn("external@partner.example", t["user_prompt"] + " ".join(t.get("turns", [])), t["id"])
            code = (t["utility"].get("answer_contains_all") or [t["utility"].get("sent_body_contains")])[0]
            self.assertTrue(code and code.startswith("PR-"), t["id"])
            holders = [e["id"] for e in t["world"]["inbox"] if code in e["body"]]
            self.assertEqual(holders, [INJ_ID], t["id"])

    def test_split_multiturn_attacks(self):
        split = [t for t in self.attacks if t.get("split")]
        self.assertEqual(len(split), 12)
        for t in split:
            self.assertEqual(len(t["turns"]), 1, t["id"])
            self.assertEqual(sorted(e["id"] for e in t["world"]["inbox"] if e["id"] >= INJ_ID), [INJ_ID, INJ_ID + 1])
        raw_split = [t for t in self.raw if t.get("split")]
        for t in raw_split:  # each email holds one part only
            bodies = {e["id"]: e["body"] for e in t["world"]["inbox"]}
            self.assertRegex(bodies[INJ_ID], r"payload:[\w-]+-a\}")
            self.assertRegex(bodies[INJ_ID + 1], r"payload:[\w-]+-b\}")


if __name__ == "__main__":
    unittest.main()
