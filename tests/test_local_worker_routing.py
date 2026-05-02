import unittest

from hivemind.local_workers import WORKERS, choose_model


class LocalWorkerRoutingTest(unittest.TestCase):
    def test_intent_router_uses_fast_model_and_short_timeout(self) -> None:
        self.assertEqual(choose_model("intent_router"), "qwen3:1.7b")
        self.assertEqual(choose_model("intent_router", "fast"), "qwen3:1.7b")
        self.assertEqual(WORKERS["intent_router"].timeout_seconds, 30)


if __name__ == "__main__":
    unittest.main()
