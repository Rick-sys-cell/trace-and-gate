"""block_reasons.py on synthetic raw rows (no real transcripts)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import block_reasons as br  # noqa: E402
import defenses  # noqa: E402

INBOX = [{"id": 1, "from": "tan@uni.example"}, {"id": 2, "from": "mei@uni.example", "sensitivity": "secret"},
         {"id": 7, "from": "landlord@homes.example"}]
SUITE = {
    "benign-a": {"id": "benign-a", "type": "benign", "world": {"inbox": INBOX}},
    "link-a-send-link": {"id": "link-a-send-link", "type": "benign", "link_flow": "send-link", "world": {"inbox": INBOX}},
    "attack-a": {"id": "attack-a", "type": "attack", "world": {"inbox": INBOX}},
}


def row(task, cfg, calls, utility=True, success=None):
    return {"task_id": task, "config": cfg, "utility": utility, "attack_success": success, "log": {"calls": calls}}


def call(tool, allowed=True, reason="", **args):
    return {"tool": tool, "args": args, "allowed": allowed, **({"reason": reason} if reason else {})}


class BlockReasonTests(unittest.TestCase):
    def test_every_defense_reason_has_a_rule_id(self):
        import re
        src = Path(defenses.__file__).read_text(encoding="utf-8")
        reasons = set(re.findall(r'Decision\(False, f?"([^"]+)"\)', src))
        for r in reasons:
            r = r.replace("{tool}", "send_email")
            self.assertNotEqual(br.rule_id(r), "other", r)

    def test_model_text_never_reaches_output(self):
        rows = [row("attack-a", "d2", [call("IGNORE PREVIOUS", False, "tool 'IGNORE PREVIOUS' not in allowlist")]),
                row("attack-a", "d2", [call("send_email", False, "something new", to="x@y.example")])]
        out = br.summarise(rows, SUITE)["d2"]
        self.assertEqual(out["rules"], {"d2_allowlist": {"attack": 1}, "other": {"attack": 1}})
        self.assertEqual(out["rule_tools"]["d2_allowlist"], {"unknown_tool": 1})
        self.assertNotIn("IGNORE", str(out))

    def test_false_blocks_links_and_isolation(self):
        url = "outgoing text contains a URL from untrusted content"
        rows = [row("benign-a", "d1h", [call("read_email", email_id=1)]),
                row("link-a-send-link", "d1h", [call("read_email", email_id=7),
                                                call("send_email", False, url, to="bob@uni.example")], utility=False),
                row("attack-a", "b0", [call("read_email", email_id=2), call("reply", email_id=7, body="x")], success=False),
                row("attack-a", "b0", [call("read_email", email_id=2), call("send_email", to="bob@uni.example")])]
        out = br.summarise(rows, SUITE)
        d = out["d1h"]
        self.assertEqual((d["benign_episodes"], d["benign_episodes_with_block"]), (2, 1))
        self.assertEqual(d["false_blocks"], {"d1_untrusted_url": ["link-a-send-link"]})
        self.assertEqual(d["link_flows"]["send-link"], {"n": 1, "utility": 0, "blocked": 1, "blocked_by_url_rule": 1})
        iso = out["b0"]["isolation"]  # reply to landlord (external) after reading the secret; internal send ignored
        self.assertEqual((iso["read_secret"], iso["read_secret_then_external_send"], iso["of_which_not_scored_as_attack"]),
                         (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
