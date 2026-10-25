"""OllamaChat helpers that need no model: unload() payload and failure handling."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import llm  # noqa: E402


class FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"{}"


class UnloadTests(unittest.TestCase):
    def test_unload_posts_keep_alive_zero_to_chat(self):
        sent = []

        def fake_urlopen(req, timeout):
            sent.append((req.full_url, req.get_method(), json.loads(req.data)))
            return FakeResp()

        with mock.patch.object(llm.urllib.request, "urlopen", fake_urlopen):
            self.assertTrue(llm.OllamaChat("qwen3:8b", "http://gw:11434").unload())
        self.assertEqual(sent, [("http://gw:11434/api/chat", "POST",
                                 {"model": "qwen3:8b", "messages": [], "keep_alive": 0})])

    def test_unload_failure_is_not_fatal(self):
        def dead(req, timeout):
            raise urllib.error.URLError("down")

        with mock.patch.object(llm.urllib.request, "urlopen", dead):
            self.assertFalse(llm.OllamaChat("qwen3:8b", "http://gw:11434").unload())


if __name__ == "__main__":
    unittest.main()
