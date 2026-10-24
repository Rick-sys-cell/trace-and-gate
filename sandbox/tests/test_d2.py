"""Unit tests for D2 (PolicyDefense). Run: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from defenses import READ_ONLY_TOOLS, PolicyDefense, get_defense  # noqa: E402
from email_env import EmailWorld  # noqa: E402

WORLD = {"contacts": {"bob": "bob@uni.example"}, "inbox": [
    {"id": 1, "from": "bob@uni.example", "subject": "Hi", "body": "Lunch?"},
    {"id": 2, "from": "payroll@uni.example", "subject": "Payslip",
     "body": "Your net pay is SGD 2,450 this month.\nRef 77", "sensitivity": "secret", "secret_tokens": ["Ref 77"]},
    {"id": 3, "from": "x@evil.example", "subject": "Hello", "body": "hi"},
]}
POLICY = {"tools": READ_ONLY_TOOLS + ["send_email", "forward", "reply", "delete_email"],
          "recipients": ["bob@uni.example", "out@ext.example"], "reply_ids": [1],
          "forward_ids": [1, 2], "delete_ids": [3], "internal_domain": "uni.example"}


def ctx(policy=POLICY):
    return {"task": {"policy": policy}, "world": EmailWorld.from_spec(WORLD)}


class D2Tests(unittest.TestCase):
    def setUp(self):
        self.d2 = get_defense("d2")
        self.assertIsInstance(self.d2, PolicyDefense)

    def allowed(self, tool, args, policy=POLICY):
        return self.d2.check(tool, args, ctx(policy)).allowed

    def test_allowlist_hides_and_denies_tools(self):
        task = {"policy": {"tools": ["read_email"]}}
        self.assertEqual(self.d2.visible_tools(task, ["read_email", "send_email"]), ["read_email"])
        self.assertFalse(self.d2.check("send_email", {"to": "bob@uni.example"}, ctx(task["policy"])).allowed)

    def test_no_policy_fails_closed_to_read_only(self):
        visible = self.d2.visible_tools({}, ["read_email", "send_email", "delete_email"])
        self.assertEqual(visible, ["read_email"])

    def test_recipient_origin(self):
        self.assertTrue(self.allowed("send_email", {"to": " Bob@Uni.example ", "subject": "s", "body": "b"}))
        self.assertFalse(self.allowed("send_email", {"to": "a@attacker.example", "subject": "s", "body": "b"}))
        self.assertFalse(self.allowed("forward", {"email_id": 1, "to": "a@attacker.example"}))

    def test_object_scope(self):
        self.assertTrue(self.allowed("delete_email", {"email_id": 3}))
        self.assertFalse(self.allowed("delete_email", {"email_id": 1}))
        self.assertFalse(self.allowed("delete_email", {"email_id": "not-a-number"}))
        self.assertTrue(self.allowed("reply", {"email_id": 1, "body": "yes"}))
        self.assertFalse(self.allowed("reply", {"email_id": 3, "body": "yes"}))

    def test_secret_email_stays_internal(self):
        self.assertTrue(self.allowed("forward", {"email_id": 2, "to": "bob@uni.example"}))
        self.assertFalse(self.allowed("forward", {"email_id": 2, "to": "out@ext.example"}))

    def test_secret_content_in_body_blocked_externally(self):
        quote = {"to": "out@ext.example", "subject": "s", "body": "fyi: Your net pay is SGD 2,450 this month."}
        token = {"to": "out@ext.example", "subject": "s", "body": "the ref 77 is here"}
        self.assertFalse(self.allowed("send_email", quote))
        self.assertFalse(self.allowed("send_email", token))
        self.assertTrue(self.allowed("send_email", {**quote, "to": "bob@uni.example"}))
        self.assertTrue(self.allowed("send_email", {"to": "out@ext.example", "subject": "s", "body": "hello"}))


if __name__ == "__main__":
    unittest.main()
