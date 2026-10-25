"""The defenses evaluated on the held-out set must be exactly those tagged defenses-frozen-v1
(24 Oct). Later additions (e.g. the exploratory D1h-L, 25 Oct) may only add code.

Hashes are of each class's / helper's source, taken at the tag."""
import hashlib
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import defenses  # noqa: E402

FROZEN = {
    "NoDefense": "926471b20d67adfe",
    "PolicyDefense": "e635d17858bbc482",
    "ProvenanceDefense": "616986e79cf4af96",
    "ProvenanceHeaderDefense": "43663b30d76a80cf",
    "CombinedDefense": "cb806f64ff67ba3e",
    "CombinedHeaderDefense": "80dc59bd301e0892",
    "DualLLMDefense": "199fa5b188dea8d3",
}


def h(obj) -> str:
    return hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()[:16]


class FrozenTests(unittest.TestCase):
    def test_frozen_classes_unchanged(self):
        changed = [n for n, digest in FROZEN.items() if h(getattr(defenses, n)) != digest]
        self.assertEqual(changed, [])

    def test_frozen_constants_unchanged(self):
        self.assertEqual(defenses.URL_RE.pattern, r"https?://[^\s'\"<>)]+")
        self.assertEqual(defenses.EMAIL_RE.pattern, r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
        self.assertEqual(defenses.MIN_SECRET_LINE, 16)
        self.assertEqual(defenses.USER_DOMAIN, "@uni.example")
        self.assertEqual(sorted(defenses.INTENT), ["create_event", "delete_email", "forward", "reply", "send_email"])

    def test_registry_keeps_frozen_names(self):
        for name, cls in [("b0", "NoDefense"), ("b1", "DualLLMDefense"), ("d1", "ProvenanceDefense"),
                          ("d1h", "ProvenanceHeaderDefense"), ("d2", "PolicyDefense"),
                          ("d1d2", "CombinedDefense"), ("d1hd2", "CombinedHeaderDefense")]:
            self.assertIs(defenses.DEFENSES[name], getattr(defenses, cls))


if __name__ == "__main__":
    unittest.main()
