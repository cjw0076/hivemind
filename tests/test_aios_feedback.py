import json
import tempfile
import unittest
from pathlib import Path

from hivemind.aios_feedback import (
    aggregate_needs,
    extract_friction,
    has_blocking_friction,
    is_complete,
    write_feedback_packet,
)


class ExtractFrictionTest(unittest.TestCase):
    def test_memoryos_unavailable_adds_low_friction(self) -> None:
        contract = {
            "proposals": {
                "hivemind": {"status": "ok", "providers": ["claude"], "member_count": 1},
                "memoryos": {"status": "unavailable", "accepted_memory_ids": [], "context_items": 0},
                "capabilityos": {"status": "ok", "recommendation_count": 3, "providers": ["claude"], "kinds": ["memory"]},
            },
            "conflicts": [],
        }
        friction = extract_friction(contract)
        memoryos_items = friction["memoryos"]["items"]
        self.assertEqual(len(memoryos_items), 1)
        self.assertEqual(memoryos_items[0]["kind"], "memoryos_unavailable")
        self.assertEqual(memoryos_items[0]["severity"], "low")

    def test_no_accepted_memory_is_medium(self) -> None:
        contract = {
            "proposals": {
                "hivemind": {"status": "ok", "providers": ["claude"], "member_count": 1},
                "memoryos": {"status": "available", "accepted_memory_ids": [], "context_items": 5},
                "capabilityos": {"status": "ok", "recommendation_count": 3, "providers": ["claude"], "kinds": ["memory"]},
            },
            "conflicts": [],
        }
        friction = extract_friction(contract)
        kinds = [item["kind"] for item in friction["memoryos"]["items"]]
        self.assertIn("no_accepted_memory", kinds)

    def test_empty_capability_card_is_medium(self) -> None:
        contract = {
            "proposals": {
                "hivemind": {"status": "ok", "providers": ["claude"], "member_count": 1},
                "memoryos": {"status": "available", "accepted_memory_ids": ["m1"], "context_items": 1},
                "capabilityos": {"status": "ok", "recommendation_count": 0, "providers": [], "kinds": []},
            },
            "conflicts": [],
        }
        friction = extract_friction(contract)
        kinds = [item["kind"] for item in friction["capabilityos"]["items"]]
        self.assertIn("no_capability_card", kinds)
        self.assertTrue(has_blocking_friction(friction))

    def test_provider_mismatch_surfaces_in_hivemind_friction(self) -> None:
        contract = {
            "proposals": {
                "hivemind": {"status": "ok", "providers": ["claude"], "member_count": 1},
                "memoryos": {"status": "available", "accepted_memory_ids": ["m1"], "context_items": 1},
                "capabilityos": {"status": "ok", "recommendation_count": 3, "providers": ["codex"], "kinds": ["impl"]},
            },
            "conflicts": [
                {"kind": "provider_route_mismatch", "severity": "medium", "detail": "claude vs codex"},
            ],
        }
        friction = extract_friction(contract)
        kinds = [item["kind"] for item in friction["hivemind"]["items"]]
        self.assertIn("provider_route_mismatch", kinds)

    def test_aggregate_needs_flattens_per_os(self) -> None:
        contract = {
            "proposals": {
                "hivemind": {"status": "ok", "providers": ["claude"], "member_count": 1},
                "memoryos": {"status": "unavailable", "accepted_memory_ids": [], "context_items": 0},
                "capabilityos": {"status": "unavailable", "recommendation_count": 0, "providers": [], "kinds": []},
            },
            "conflicts": [],
        }
        friction = extract_friction(contract)
        needs = aggregate_needs(friction)
        sources = {item["source"] for item in needs}
        self.assertIn("memoryos", sources)
        self.assertIn("capabilityos", sources)
        for item in needs:
            self.assertTrue(item["need"])


class FeedbackPacketTest(unittest.TestCase):
    def test_packet_skipped_when_outbox_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = {"run_id": "run_x", "contract_id": "asc_x", "goal": "G", "status": "ready", "signed_by": []}
            friction = {"hivemind": {"items": []}, "memoryos": {"items": []}, "capabilityos": {"items": []}}
            result = write_feedback_packet(root, contract, friction, generation=0)
            self.assertFalse(result["written"])
            self.assertEqual(result["reason"], "myworld_outbox_unreachable")

    def test_packet_written_to_overridden_outbox(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hivemind"
            root.mkdir()
            myworld = Path(tmp) / "myworld"
            (myworld / ".aios").mkdir(parents=True)
            os.environ["HIVE_MYWORLD_AIOS_ROOT"] = str(myworld)
            try:
                contract = {"run_id": "run_x", "contract_id": "asc_x", "goal": "G", "status": "ready", "signed_by": ["hivemind"]}
                friction = {
                    "hivemind": {"items": []},
                    "memoryos": {"items": [{"kind": "no_accepted_memory", "severity": "medium", "need": "approve drafts"}]},
                    "capabilityos": {"items": []},
                }
                result = write_feedback_packet(root, contract, friction, generation=2)
                self.assertTrue(result["written"])
                self.assertIn("aios-feedback-run_x-gen02", result["path"])
                packet = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
                self.assertEqual(packet["kind"], "aios_feedback_report")
                self.assertEqual(packet["generation"], 2)
                self.assertEqual(packet["target_repo"], "myworld")
                self.assertEqual(packet["source"], "hivemind")
                self.assertEqual(len(packet["needs"]), 1)
            finally:
                del os.environ["HIVE_MYWORLD_AIOS_ROOT"]


class CompletionSignalTest(unittest.TestCase):
    def test_no_completion_file_means_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = is_complete(Path(tmp), "anything")
            self.assertFalse(result["complete"])
            self.assertEqual(result["reason"], "no_completion_file")

    def test_all_goals_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hivemind").mkdir()
            (root / ".hivemind" / "aios_completion.json").write_text(json.dumps({"all_goals": True}))
            result = is_complete(root, "any goal")
            self.assertTrue(result["complete"])
            self.assertEqual(result["reason"], "all_goals_marked_complete")

    def test_goal_pattern_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hivemind").mkdir()
            (root / ".hivemind" / "aios_completion.json").write_text(
                json.dumps({"goal_patterns": ["json.*validator"]})
            )
            self.assertTrue(is_complete(root, "Build a JSON validator")["complete"])
            self.assertFalse(is_complete(root, "Unrelated task")["complete"])

    def test_invalid_regex_falls_back_to_substring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hivemind").mkdir()
            (root / ".hivemind" / "aios_completion.json").write_text(
                json.dumps({"goal_patterns": ["unbalanced (paren"]})
            )
            self.assertTrue(is_complete(root, "Test with unbalanced (paren in it")["complete"])

    def test_corrupt_completion_file_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hivemind").mkdir()
            (root / ".hivemind" / "aios_completion.json").write_text("not json")
            result = is_complete(root, "any goal")
            self.assertFalse(result["complete"])
            self.assertIn("unreadable", result["reason"])


if __name__ == "__main__":
    unittest.main()
