import unittest

from hivemind.local_workers import WORKERS, add_no_think, choose_model, ollama_generate_payload, requires_no_think


class LocalWorkerRoutingTest(unittest.TestCase):
    def test_intent_router_uses_fast_model_and_short_timeout(self) -> None:
        self.assertEqual(choose_model("intent_router"), "qwen3:1.7b")
        self.assertEqual(choose_model("intent_router", "fast"), "qwen3:1.7b")
        self.assertEqual(WORKERS["intent_router"].timeout_seconds, 60)

    def test_qwen3_ollama_payload_disables_thinking_at_top_level(self) -> None:
        payload = ollama_generate_payload("qwen3:1.7b", "Return JSON.")

        self.assertEqual(payload["think"], False)
        self.assertTrue(payload["prompt"].startswith("/no_think\n"))
        self.assertNotIn("think", payload["options"])

    def test_non_thinking_model_payload_keeps_prompt(self) -> None:
        payload = ollama_generate_payload("phi4-mini", "Return JSON.")

        self.assertNotIn("think", payload)
        self.assertEqual(payload["prompt"], "Return JSON.")

    def test_no_think_helpers_are_idempotent(self) -> None:
        self.assertTrue(requires_no_think("qwen3-coder:30b"))
        self.assertFalse(requires_no_think("qwen2.5-coder:7b"))
        self.assertEqual(add_no_think("/no_think\nReturn JSON."), "/no_think\nReturn JSON.")


if __name__ == "__main__":
    unittest.main()
