import json
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import ask_router


class FastRouterTest(unittest.TestCase):
    def test_fast_router_uses_heuristic_without_local_llm_start_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = ask_router(root, "smooth operator prompt", complexity="fast")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            events = (plan_path.parent / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(plan["route_source"], "heuristic_fast")
            self.assertNotIn('"type": "agent_started"', events)


if __name__ == "__main__":
    unittest.main()
