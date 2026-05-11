from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, execute_step, save_dag, update_step
from hivemind.protocol import (
    approved_decision_for_step,
    build_execution_intent,
    cast_vote,
    check_intent,
    create_proof,
    decide_intent,
    load_votes,
    save_intent,
)


class LedgerProtocolTest(unittest.TestCase):
    def _root_run_dag(self, intent: str = "implementation"):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        paths = create_run(root, "protocol test")
        dag = build_dag(paths.run_id, "protocol test", intent)
        save_dag(root, dag)
        return tmp, root, paths, dag

    def test_prepare_only_intent_decides_without_extra_votes(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)

        intent = build_execution_intent(root, dag, "planner", execute=False)
        save_intent(root, intent)
        vote = check_intent(root, paths.run_id, intent.intent_id)
        decision = decide_intent(root, paths.run_id, intent.intent_id)

        self.assertEqual(vote.voter_role, "policy-gate")
        self.assertEqual(decision.decision, "prepare_only")
        self.assertEqual(decision.missing_voters, [])

    def test_provider_execute_requires_quorum(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)

        intent = build_execution_intent(root, dag, "planner", execute=True)
        save_intent(root, intent)
        check_intent(root, paths.run_id, intent.intent_id)
        first = decide_intent(root, paths.run_id, intent.intent_id)
        self.assertEqual(first.decision, "needs_vote")
        self.assertIn("verifier", first.missing_voters)

        cast_vote(root, paths.run_id, intent.intent_id, voter_role="verifier", vote="approve")
        second = decide_intent(root, paths.run_id, intent.intent_id)
        self.assertEqual(second.decision, "needs_vote")
        self.assertIn("independent-reviewer", second.missing_voters)

        cast_vote(root, paths.run_id, intent.intent_id, voter_role="independent-reviewer", vote="approve")
        final = decide_intent(root, paths.run_id, intent.intent_id)
        self.assertIn(final.decision, {"approved", "approved_with_conditions"})
        self.assertIsNotNone(approved_decision_for_step(root, paths.run_id, "planner"))

    def test_executor_cannot_approve_itself(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)

        intent = build_execution_intent(root, dag, "executor", execute=True)
        save_intent(root, intent)
        with self.assertRaises(ValueError):
            cast_vote(root, paths.run_id, intent.intent_id, voter_role="codex-executor", vote="approve")

    def test_irreversible_intent_requires_user(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)

        step = dag.by_id("executor")
        step.reversibility = 0.1
        step.reversibility_source = "declared"
        intent = build_execution_intent(root, dag, "executor", execute=True)
        save_intent(root, intent)
        check_intent(root, paths.run_id, intent.intent_id)
        decision = decide_intent(root, paths.run_id, intent.intent_id)

        self.assertEqual(intent.authority_class, "provider_bypass_irreversible")
        self.assertEqual(decision.decision, "ask_user")

    def test_execute_gate_blocks_provider_without_decision(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)
        for sid in ("context", "diff_review", "barrier_context"):
            update_step(dag, sid, status="completed")

        result = execute_step(root, dag, "planner", execute=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "protocol_gate")

    def test_execute_gate_uses_approved_decision(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)
        for sid in ("context", "diff_review", "barrier_context"):
            update_step(dag, sid, status="completed")

        intent = build_execution_intent(root, dag, "planner", execute=True)
        save_intent(root, intent)
        check_intent(root, paths.run_id, intent.intent_id)
        cast_vote(root, paths.run_id, intent.intent_id, voter_role="verifier", vote="approve")
        cast_vote(root, paths.run_id, intent.intent_id, voter_role="independent-reviewer", vote="approve")
        decision = decide_intent(root, paths.run_id, intent.intent_id)
        self.assertIn(decision.decision, {"approved", "approved_with_conditions"})

        def fake_external(root_arg, agent, role, run_id=None, execute=False):
            out = root_arg / ".runs" / run_id / "agents" / agent / f"{role}_result.yaml"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("status: completed\nconfidence: 0.9\n", encoding="utf-8")
            return out

        with patch("hivemind.harness.invoke_external_agent", side_effect=fake_external):
            result = execute_step(root, dag, "planner", execute=True)

        self.assertTrue(result["ok"], result)
        self.assertNotEqual(result["status"], "protocol_gate")

    def test_create_proof_records_artifact_hashes(self) -> None:
        tmp, root, paths, dag = self._root_run_dag()
        self.addCleanup(tmp.cleanup)

        intent = build_execution_intent(root, dag, "planner", execute=False)
        save_intent(root, intent)
        stdout_path = paths.run_dir / "agents" / "claude" / "stdout.txt"
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text("hello\n", encoding="utf-8")
        stdout_rel = stdout_path.relative_to(root).as_posix()

        proof = create_proof(
            root,
            paths.run_id,
            intent.intent_id,
            status="completed",
            stdout_path=stdout_rel,
            artifacts_created=[stdout_rel],
        )

        self.assertIn(stdout_rel, proof.artifact_hashes)
        self.assertTrue(proof.artifact_hashes[stdout_rel].startswith("sha256:"))

    def test_cli_protocol_intent_check_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "run", "protocol cli", "-q"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = run.stdout.strip()
            subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "plan", "dag", "--intent", "implementation"],
                text=True,
                capture_output=True,
                check=True,
            )
            intent = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "protocol",
                    "intent",
                    "planner",
                    "--execute",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(intent.stdout)
            self.assertEqual(data["run_id"], run_id)
            self.assertEqual(data["step_id"], "planner")
            self.assertEqual(data["bypass_mode"], "execute")

            check = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "protocol",
                    "check",
                    data["intent_id"],
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            vote = json.loads(check.stdout)
            self.assertEqual(vote["voter_role"], "policy-gate")
            self.assertTrue(load_votes(root, run_id, data["intent_id"]))


if __name__ == "__main__":
    unittest.main()
