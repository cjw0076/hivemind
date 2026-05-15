import json
import tempfile
import unittest
from pathlib import Path

from hivemind.aios_runtime import (
    CONTRACT_FILENAME,
    KIND,
    SCHEMA_VERSION,
    _check_conflicts,
    _compose_iteration_goal,
    build_aios_contract,
    evolve_aios_contract,
    format_aios_contract,
    format_aios_evolution,
    resume_aios_contract,
)


class AIOSContractBuildTest(unittest.TestCase):
    def test_contract_artifact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = build_aios_contract(root, "Implement and review a small Python feature")

            self.assertEqual(contract["schema_version"], SCHEMA_VERSION)
            self.assertEqual(contract["kind"], KIND)
            self.assertEqual(set(contract["proposals"].keys()), {"hivemind", "memoryos", "capabilityos"})
            self.assertTrue(contract["contract_id"].startswith("asc_"))

            contract_path = root / ".runs" / contract["run_id"] / CONTRACT_FILENAME
            self.assertTrue(contract_path.exists())
            disk_contract = json.loads(contract_path.read_text(encoding="utf-8"))
            self.assertEqual(disk_contract["goal"], "Implement and review a small Python feature")
            self.assertEqual(disk_contract["proposals"]["hivemind"]["status"], "ok")
            self.assertIn("hivemind", disk_contract["signed_by"])

    def test_isolated_root_blocks_execution_at_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = build_aios_contract(root, "Build a JSON validator library")

            self.assertTrue(contract["operator_checkpoint"])
            self.assertEqual(contract["status"], "operator_checkpoint")
            self.assertIsNone(contract["execution"])  # execution gated by checkpoint
            self.assertFalse(contract["force_resumed"])
            conflict_kinds = {c["kind"] for c in contract["conflicts"]}
            self.assertIn("memoryos_unavailable", conflict_kinds)
            self.assertIn("capabilityos_unavailable", conflict_kinds)
            self.assertEqual(contract["signed_by"], ["hivemind"])

    def test_force_override_advances_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = build_aios_contract(root, "Build a JSON validator library", force=True)

            self.assertFalse(contract["operator_checkpoint"])
            self.assertEqual(contract["status"], "ready")
            self.assertTrue(contract["force_resumed"])
            self.assertIsInstance(contract["execution"], dict)

    def test_resume_force_unblocks_previously_checkpointed_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_aios_contract(root, "Build a JSON validator library")
            self.assertTrue(first["operator_checkpoint"])

            resumed = resume_aios_contract(root, first["run_id"], force=True)
            self.assertFalse(resumed["operator_checkpoint"])
            self.assertTrue(resumed["force_resumed"])
            self.assertEqual(resumed["status"], "ready")
            self.assertIsInstance(resumed["execution"], dict)
            self.assertEqual(resumed["run_id"], first["run_id"])

    def test_resume_without_existing_contract_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # create a run via a contract build but delete the contract artifact
            from hivemind.harness import create_run

            paths = create_run(root, user_request="seed run")
            with self.assertRaises(FileNotFoundError):
                resume_aios_contract(root, paths.run_id)

    def test_format_renders_execution_and_force_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = build_aios_contract(root, "Force test goal", force=True)
            text = format_aios_contract(contract)

            self.assertIn("AIOS Contract", text)
            self.assertIn("Goal: Force test goal", text)
            self.assertIn("force-resumed", text)
            self.assertIn("Execution:", text)

    def test_empty_goal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                build_aios_contract(root, "")
            with self.assertRaises(ValueError):
                build_aios_contract(root, "   ")


class AIOSConflictTest(unittest.TestCase):
    def test_provider_route_mismatch_is_flagged(self) -> None:
        hivemind = {"status": "ok", "providers": ["claude"]}
        memoryos = {"status": "available"}
        capabilityos = {"status": "ok", "recommendation_count": 3, "providers": ["codex"]}
        conflicts = _check_conflicts(hivemind, memoryos, capabilityos)
        kinds = {c["kind"]: c["severity"] for c in conflicts}
        self.assertEqual(kinds.get("provider_route_mismatch"), "medium")

    def test_provider_route_match_is_clean(self) -> None:
        hivemind = {"status": "ok", "providers": ["claude", "codex"]}
        memoryos = {"status": "available"}
        capabilityos = {"status": "ok", "recommendation_count": 3, "providers": ["codex"]}
        conflicts = _check_conflicts(hivemind, memoryos, capabilityos)
        self.assertNotIn("provider_route_mismatch", {c["kind"] for c in conflicts})

    def test_empty_capabilityos_is_medium_conflict(self) -> None:
        hivemind = {"status": "ok", "providers": ["claude"]}
        memoryos = {"status": "available"}
        capabilityos = {"status": "ok", "recommendation_count": 0, "providers": []}
        conflicts = _check_conflicts(hivemind, memoryos, capabilityos)
        self.assertIn("capabilityos_empty_recommendation", {c["kind"] for c in conflicts})

    def test_hivemind_empty_plan_is_high_severity(self) -> None:
        hivemind = {"status": "empty", "providers": []}
        memoryos = {"status": "available"}
        capabilityos = {"status": "ok", "recommendation_count": 3, "providers": []}
        conflicts = _check_conflicts(hivemind, memoryos, capabilityos)
        kinds = {c["kind"]: c["severity"] for c in conflicts}
        self.assertEqual(kinds.get("hivemind_empty_plan"), "high")


class AIOSEvolutionTest(unittest.TestCase):
    def test_evolve_stops_immediately_when_completion_signal_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hivemind").mkdir()
            (root / ".hivemind" / "aios_completion.json").write_text(json.dumps({"all_goals": True}))

            summary = evolve_aios_contract(root, "any goal", max_iterations=3)
            self.assertEqual(summary["iterations"], 0)
            self.assertTrue(summary["stop_reason"].startswith("completion_signal:"))
            self.assertIn("artifact", summary)

    def test_evolve_stops_on_operator_checkpoint_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = evolve_aios_contract(root, "isolated build", max_iterations=2, force=False)
            # Isolated tmp dir → first iter checkpoints → loop halts.
            self.assertEqual(summary["iterations"], 1)
            self.assertEqual(summary["stop_reason"], "operator_checkpoint_blocked_evolution")
            self.assertEqual(summary["final_status"], "operator_checkpoint")

    def test_evolve_with_force_runs_to_max_when_friction_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = evolve_aios_contract(root, "isolated build", max_iterations=2, force=True)
            self.assertEqual(summary["iterations"], 2)
            self.assertEqual(summary["stop_reason"], "max_iterations_reached")
            # Each iteration writes an evolution history entry.
            self.assertEqual([h["generation"] for h in summary["history"]], [0, 1])

    def test_compose_iteration_goal_injects_prior_feedback(self) -> None:
        original = "Build a JSON validator"
        feedback = [
            {"source": "memoryos", "kind": "no_accepted_memory", "need": "approve drafts"},
            {"source": "capabilityos", "kind": "no_capability_card", "need": "add card for json-validation"},
        ]
        composed = _compose_iteration_goal(original, feedback)
        self.assertTrue(composed.startswith(original))
        self.assertIn("memoryos/no_accepted_memory", composed)
        self.assertIn("capabilityos/no_capability_card", composed)

    def test_compose_iteration_goal_passthrough_when_no_feedback(self) -> None:
        self.assertEqual(_compose_iteration_goal("goal", []), "goal")

    def test_evolution_invalid_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                evolve_aios_contract(root, "", max_iterations=1)
            with self.assertRaises(ValueError):
                evolve_aios_contract(root, "goal", max_iterations=0)

    def test_format_aios_evolution_renders_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = evolve_aios_contract(root, "isolated build", max_iterations=1, force=True)
            text = format_aios_evolution(summary)
            self.assertIn("AIOS Evolution", text)
            self.assertIn("isolated build", text)
            self.assertIn("History:", text)


if __name__ == "__main__":
    unittest.main()
