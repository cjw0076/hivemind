import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from hivemind.harness import (
    RunPaths,
    agent_roles_report,
    auto_loop,
    build_debate_memory_draft,
    build_memory_draft,
    build_context_pack_for_role,
    close_debate_front,
    close_gap_loop,
    create_run,
    debate_topic,
    debate_front_status,
    extract_provider_output_disagreements,
    ensure_memoryos_context,
    flow_advance,
    format_git_diff_report,
    git_diff_report,
    invoke_external_agent,
    llm_checker_report,
    local_benchmark_report,
    local_model_profile,
    orchestrate_prompt,
    policy_report,
    set_agent_status,
)
from hivemind.plan_dag import load_dag
from hivemind.workloop import read_execution_ledger
from hivemind.workloop import append_execution_ledger
from hivemind.run_validation import validate_run_artifacts
from unittest.mock import patch


class ProductionHardeningTest(unittest.TestCase):
    def test_public_alpha_docs_state_boundaries_and_module_split_strategy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        public_alpha = (root / "docs" / "HIVE_PUBLIC_ALPHA.md").read_text(encoding="utf-8")
        normalized_public_alpha = " ".join(public_alpha.split())

        self.assertIn("demo quickstart", readme)
        self.assertIn("no provider keys required", readme)
        self.assertIn("docs/HIVE_PUBLIC_ALPHA.md", readme)
        self.assertIn("does not replace provider CLIs", normalized_public_alpha)
        self.assertIn("requires no provider API keys", public_alpha)
        self.assertIn("MemoryOS and CapabilityOS integrations stay optional", public_alpha)
        self.assertIn("Module Split Strategy", public_alpha)
        self.assertIn("Stop condition", public_alpha)

    def test_public_alpha_large_module_guard_names_staged_targets(self) -> None:
        root = Path(__file__).resolve().parents[1]
        public_alpha = (root / "docs" / "HIVE_PUBLIC_ALPHA.md").read_text(encoding="utf-8")
        large_targets = [
            ("hivemind/harness.py", "hivemind/hivemind/harness.py"),
            ("hivemind/plan_dag.py", "hivemind/hivemind/plan_dag.py"),
            ("hivemind/hive.py", "hivemind/hivemind/hive.py"),
        ]

        for stat_rel, doc_rel in large_targets:
            self.assertGreater((root / stat_rel).stat().st_size, 50_000)
            self.assertIn(doc_rel, public_alpha)

    def test_policy_report_writes_default_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = policy_report(root, write=True)

            self.assertEqual(report["status"], "ready", report["issues"])
            self.assertTrue((root / ".hivemind" / "policy.yaml").exists())
            self.assertIn("codex.executor", report["policy"]["roles"])

    def test_agent_roles_include_user_claude_codex_and_local(self) -> None:
        roles = agent_roles_report()["roles"]

        self.assertIn("user.director", roles)
        self.assertIn("claude.planner", roles)
        self.assertIn("codex.executor", roles)
        self.assertIn("local.context", roles)
        self.assertIn("hive.verifier", roles)
        self.assertIn("hive.product_evaluator", roles)
        self.assertIn("persona.actual_user", roles)

    def test_context_build_writes_agent_specific_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "build context pack", project="Hive Mind")
            policy_report(root, write=True)

            report = build_context_pack_for_role(root, "codex.executor", paths.run_id)

            output = root / report["path"]
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("forbidden_scope", text)
            self.assertIn("evolution of Single Human Intelligence", text)

    def test_memoryos_context_bridge_records_trace_and_selected_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            memoryos_root = base / "memoryOS"
            (memoryos_root / "memoryos").mkdir(parents=True)
            (memoryos_root / "memoryos" / "cli.py").write_text("# stub\n", encoding="utf-8")
            paths = create_run(root, "use remembered provider policy", project="Hive Mind")
            pack = {
                "role": "hive",
                "audience": "local",
                "task": "use remembered provider policy",
                "trace_id": "trace_123",
                "decisions": [{"id": "mem_decision_1", "type": "decision", "content": "Hive owns execution authority.", "raw_refs": ["docs/HIVE_WORKING_METHOD.md"]}],
                "constraints": [{"id": "mem_constraint_1", "type": "constraint", "content": "MemoryOS owns accepted memory."}],
                "open_questions": [],
                "recent_actions": [],
                "other": [],
                "feedback_directives": [
                    {
                        "memory_id": "mem_decision_1",
                        "type": "decision",
                        "directive": "Apply accepted decision: Hive owns execution authority.",
                    }
                ],
                "total_accepted": 2,
                "total_available": 2,
                "context_items": 2,
                "token_estimate": 42,
            }

            with patch("hivemind.memory_bridge.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(pack), stderr="")
                report = ensure_memoryos_context(root, paths.run_id)

            self.assertEqual(report["status"], "available")
            self.assertEqual(report["trace_id"], "trace_123")
            self.assertEqual(report["accepted_memory_ids"], ["mem_decision_1", "mem_constraint_1"])
            self.assertEqual(report["feedback_directives_count"], 1)
            state = json.loads(paths.state.read_text(encoding="utf-8"))
            self.assertEqual(state["accepted_memories_used"], ["mem_decision_1", "mem_constraint_1"])
            self.assertEqual(state["memoryos_context"]["trace_id"], "trace_123")
            self.assertEqual(state["memoryos_context"]["feedback_directives_count"], 1)
            self.assertTrue((root / report["artifact"]).exists())
            self.assertTrue((root / report["receipt_artifact"]).exists())
            self.assertEqual(report["kind"], "memoryos_context_receipt")
            self.assertFalse(report["should_abort_hive"])
            self.assertFalse(report["degraded"])
            context_text = paths.context_pack.read_text(encoding="utf-8")
            self.assertIn("MemoryOS Accepted Context", context_text)
            self.assertIn("Feedback Directives", context_text)
            self.assertIn("Apply accepted decision", context_text)
            self.assertIn("trace_123", context_text)
            self.assertIn("Hive owns execution authority.", context_text)
            command = run.call_args.args[0]
            self.assertIn("context", command)
            self.assertIn("build", command)
            self.assertIn("--json", command)

    def test_memoryos_context_bridge_is_nonblocking_when_memoryos_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hivemind"
            root.mkdir()
            paths = create_run(root, "no memoryos sibling", project="Hive Mind")

            report = ensure_memoryos_context(root, paths.run_id)

            self.assertEqual(report["status"], "unavailable")
            self.assertEqual(report["failure_class"], "memoryos_cli_missing")
            self.assertFalse(report["should_abort_hive"])
            self.assertEqual(report["accepted_memory_ids"], [])
            self.assertTrue((root / report["artifact"]).exists())
            self.assertTrue((root / report["receipt_artifact"]).exists())
            self.assertIn("no memoryos sibling", paths.context_pack.read_text(encoding="utf-8"))

    def test_memoryos_context_bridge_can_be_disabled_for_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            memoryos_root = base / "memoryOS"
            (memoryos_root / "memoryos").mkdir(parents=True)
            (memoryos_root / "memoryos" / "cli.py").write_text("# stub\n", encoding="utf-8")
            paths = create_run(root, "disabled memoryos bridge", project="Hive Mind")

            with patch.dict(os.environ, {"HIVE_DISABLE_MEMORYOS": "1"}):
                report = ensure_memoryos_context(root, paths.run_id)

            self.assertEqual(report["status"], "unavailable")
            self.assertIn("disabled", report["reason"].lower())
            self.assertEqual(report["failure_class"], "memoryos_disabled")
            self.assertFalse(report["should_abort_hive"])

    def test_memoryos_context_bridge_failure_writes_nonblocking_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            memoryos_root = base / "memoryOS"
            (memoryos_root / "memoryos").mkdir(parents=True)
            (memoryos_root / "memoryos" / "cli.py").write_text("# stub\n", encoding="utf-8")
            paths = create_run(root, "memoryos failure receipt", project="Hive Mind")

            with patch("hivemind.memory_bridge.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="boom")
                report = ensure_memoryos_context(root, paths.run_id)

            receipt_path = root / report["receipt_artifact"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["failure_class"], "memoryos_nonzero_exit")
            self.assertTrue(report["degraded"])
            self.assertFalse(report["should_abort_hive"])
            self.assertEqual(receipt["failure_class"], "memoryos_nonzero_exit")

    def test_local_model_profile_writes_role_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = local_model_profile(root, write=True)

            self.assertTrue((root / ".hivemind" / "local_model_profile.json").exists())
            self.assertIn("role_assignments", report)
            self.assertIn("models", report)

    def test_policy_fixtures_capture_safe_and_unsafe_danger_modes(self) -> None:
        fixture_root = Path("tests/fixtures/policies")
        safe = yaml.safe_load((fixture_root / "default_policy.yaml").read_text(encoding="utf-8"))
        unsafe = yaml.safe_load((fixture_root / "invalid_danger_mode.yaml").read_text(encoding="utf-8"))

        self.assertFalse(safe["danger_modes"]["allowed"])
        self.assertTrue(unsafe["danger_modes"]["allowed"])

    def test_local_backend_fixtures_use_backend_protocol(self) -> None:
        fixture_root = Path("tests/fixtures/local_backends")
        available = json.loads((fixture_root / "ollama_available.json").read_text(encoding="utf-8"))
        unavailable = json.loads((fixture_root / "no_backend.json").read_text(encoding="utf-8"))

        self.assertEqual(available["protocol"], "hive-local-backend-v1")
        self.assertEqual(available["backends"]["ollama"]["status"], "available")
        self.assertIn("phi4-mini", unavailable["missing_recommended_models"])

    def test_debate_prepare_only_writes_barrier_and_convergence_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "choose safer release gate", participants=["claude", "gemini"], execute=False)

            self.assertEqual(report["barrier"], "all_participants_processed_before_convergence")
            self.assertEqual(report["modes"], {"debate_initial": "cooperative", "debate_review": "adversarial"})
            self.assertTrue((root / ".runs" / report["run_id"] / "debate_convergence.md").exists())
            self.assertTrue((root / ".runs" / report["run_id"] / "disagreements.json").exists())
            self.assertTrue((root / report["artifacts"]["precommit_table"]).exists())
            self.assertTrue((root / report["artifacts"]["precommit_match"]).exists())
            self.assertTrue((root / report["artifacts"]["turn_arbitration"]).exists())
            self.assertTrue(all(round_report["barrier"] == "complete" for round_report in report["rounds"]))

    def test_debate_mode_flags_are_recorded_and_prompted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(
                root,
                "verify release claims only",
                participants=["claude", "gemini"],
                execute=False,
                initial_mode="adversarial",
                review_mode="verification-only",
            )
            run_dir = root / ".runs" / report["run_id"]
            modes = json.loads((run_dir / "artifacts" / "debate_modes.json").read_text(encoding="utf-8"))
            review_prompt = (run_dir / "agents" / "claude" / "debate_review_prompt.md").read_text(encoding="utf-8")
            convergence = (run_dir / "debate_convergence.md").read_text(encoding="utf-8")

            self.assertEqual(report["rounds"][0]["mode"], "adversarial")
            self.assertEqual(report["rounds"][1]["mode"], "verification-only")
            self.assertEqual(modes["roles"]["debate_review"]["mode"], "verification-only")
            self.assertIn("Debate mode: verification-only", review_prompt)
            self.assertIn("concrete evidence, tests, receipts", review_prompt)
            self.assertIn("- debate_review: verification-only", convergence)

    def test_debate_precommit_table_binds_results_to_dispositions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "bind debate outcomes", participants=["claude", "gemini"], execute=False)
            table = json.loads((root / report["artifacts"]["precommit_table"]).read_text(encoding="utf-8"))
            match = json.loads((root / report["artifacts"]["precommit_match"]).read_text(encoding="utf-8"))
            prompt = (root / ".runs" / report["run_id"] / "agents" / "claude" / "debate_initial_prompt.md").read_text(encoding="utf-8")

            self.assertEqual(table["kind"], "PreCommitTable")
            self.assertEqual(len(table["signatures"]), 2)
            self.assertTrue(all(item["signature"].startswith("sig_") for item in table["signatures"]))
            self.assertIn("prepared_without_output", {row["outcome"] for row in table["rows"]})
            self.assertTrue(match["all_matched"])
            self.assertTrue(all(item["outcome"] == "prepared_without_output" for item in match["matches"]))
            self.assertTrue(all(item["disposition"] == "manual_followup_required" for item in match["matches"]))
            self.assertIn("PreCommitTable", prompt)
            self.assertIn("prepared_without_output -> manual_followup_required", prompt)

    def test_debate_turn_arbitration_records_owner_deadline_and_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "arbitrate turns", participants=["claude", "gemini"], execute=False)
            arbitration = json.loads((root / report["artifacts"]["turn_arbitration"]).read_text(encoding="utf-8"))
            prompt = (root / ".runs" / report["run_id"] / "agents" / "claude" / "debate_initial_prompt.md").read_text(encoding="utf-8")

            self.assertEqual(arbitration["kind"], "TurnArbitration")
            self.assertEqual(len(arbitration["turns"]), 4)
            self.assertEqual(arbitration["status"], "needs_manual_followup")
            self.assertEqual(arbitration["next_speaker"], "claude")
            self.assertTrue(all(turn["owner"] in {"claude", "gemini"} for turn in arbitration["turns"]))
            self.assertTrue(all(turn["deadline_seconds"] == 1800 for turn in arbitration["turns"]))
            self.assertTrue(all(turn["timeout_action"] == "escalate_to_user" for turn in arbitration["turns"]))
            self.assertTrue(all(turn["status"] == "manual_followup" for turn in arbitration["turns"]))
            self.assertIn("TurnArbitration", prompt)
            self.assertIn("owner=claude", prompt)

    def test_debate_front_blocks_new_front_until_test_closes_or_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "first front", participants=["claude", "gemini"], execute=False)
            run_id = report["run_id"]
            state = debate_front_status(root, run_id)

            self.assertEqual(state["status"], "awaiting_falsifiable_test")
            self.assertIn("cheap_falsifiable_test", state)
            with self.assertRaisesRegex(RuntimeError, "active debate front is open"):
                debate_topic(root, "second front blocked", run_id=run_id, participants=["claude", "gemini"], execute=False)

            closed = close_debate_front(root, run_id, test="run the smallest release-gate smoke", result="passed", closed_by="user")
            self.assertEqual(closed["status"], "closed")
            self.assertEqual(closed["cheap_falsifiable_test"]["result"], "passed")
            reopened = debate_topic(root, "second front allowed", run_id=run_id, participants=["claude", "gemini"], execute=False)
            self.assertEqual(reopened["front"]["status"], "awaiting_falsifiable_test")

    def test_debate_front_override_records_previous_front(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = debate_topic(root, "override first front", participants=["claude", "gemini"], execute=False)
            second = debate_topic(root, "override second front", run_id=first["run_id"], participants=["claude", "gemini"], execute=False, override_front=True)
            state = debate_front_status(root, first["run_id"])

            self.assertTrue(second["front"]["override_previous"])
            self.assertEqual(state["front_id"], second["front"]["front_id"])
            self.assertEqual(len(state["history"]), 1)
            self.assertEqual(state["history"][0]["close_reason"], "operator_override")

    def test_provider_output_disagreement_extraction_detects_axes(self) -> None:
        records = extract_provider_output_disagreements(
            "run_test",
            "ship or hold release",
            [
                {
                    "role": "debate_review",
                    "participants": [
                        {
                            "participant": "claude",
                            "result_path": ".runs/run_test/agents/claude/debate_review_result.yaml",
                            "output_preview": "Hold the release. This is high risk and weak evidence. Ask user approval before proceeding.",
                        },
                        {
                            "participant": "gemini",
                            "result_path": ".runs/run_test/agents/gemini/debate_review_result.yaml",
                            "output_preview": "Ship it. Low risk, verified by tests, implement the patch now.",
                        },
                    ],
                }
            ],
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"], "provider_output")
        self.assertEqual(records[0]["severity"], "high")
        self.assertIn("conclusion", records[0]["axes"])
        self.assertIn("risk_assessment", records[0]["axes"])
        self.assertIn("evidence", records[0]["axes"])

    def test_debate_memory_draft_requires_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "capture debate only after review", participants=["claude", "gemini"], execute=False)

            with self.assertRaisesRegex(RuntimeError, "require human review"):
                build_memory_draft(root, report["run_id"])
            with self.assertRaisesRegex(RuntimeError, "requires human review"):
                build_debate_memory_draft(root, report["run_id"], reviewed_by="claude")

            out = build_debate_memory_draft(root, report["run_id"], reviewed_by="user", review_note="Operator approved draft extraction.")
            data = json.loads(out.read_text(encoding="utf-8"))
            draft = data["memory_drafts"][0]
            self.assertEqual(draft["source"], "debate_convergence")
            self.assertEqual(draft["reviewed_by"], "user")
            self.assertTrue(draft["memoryos_acceptance_required"])
            self.assertIn("debate_convergence.md", draft["raw_refs"][1])
            review_path = root / ".runs" / report["run_id"] / "artifacts" / "debate_memory_review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["kind"], "debate_memory_human_review")
            self.assertEqual(review["decision"], "approved_for_memory_draft")

    def test_cli_debate_memory_draft_requires_reviewed_by(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "debate",
                    "memory review gate",
                    "--participant",
                    "claude",
                    "--participant",
                    "gemini",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]
            blocked = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "memory", "draft", "--run-id", run_id],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("debate memory drafts require human review", blocked.stderr)

            approved = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "memory",
                    "draft",
                    "--run-id",
                    run_id,
                    "--from-debate",
                    "--reviewed-by",
                    "operator",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(approved.stdout)
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["drafts"][0]["reviewed_by"], "operator")

    def test_gap_closure_writes_learning_operator_loop_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "close hive mind gaps", project="Hive Mind")
            report = close_gap_loop(root, paths.run_id)

            self.assertEqual(report["status"], "ready")
            for name in [
                "memory_context",
                "semantic_verification",
                "handoff_quality",
                "routing_evidence",
                "conflict_set",
                "operator_decisions",
            ]:
                self.assertTrue((root / report["artifacts"][name]).exists(), name)

    def test_prepared_provider_result_uses_expanded_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider schema", project="Hive Mind")

            result_path = invoke_external_agent(root, "claude", "planner", run_id=paths.run_id, execute=False)
            self.assertTrue(result_path.exists())
            report = validate_run_artifacts(paths.run_dir, root)

            self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_llm_checker_adapter_writes_plan_without_requiring_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = llm_checker_report(root, write=True)

            self.assertTrue((root / ".hivemind" / "llm_checker_report.json").exists())
            self.assertIn("github.com/Pavelevich/llm-checker", report["source"]["repo"])
            self.assertIn("recommend", report["commands"])

    def test_local_benchmark_writes_results_and_profile_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "hivemind.harness.benchmark_local_model",
                return_value={
                    "model": "qwen3:1.7b",
                    "role": "json_normalizer",
                    "runtime": "test",
                    "status": "completed",
                    "latency_ms": 123,
                    "json_valid": True,
                    "schema_valid": True,
                    "parsed": {"ok": True, "normalized": {"status": "ok"}, "confidence": 0.75},
                    "raw_response": '{"ok": true, "normalized": {"status": "ok"}, "confidence": 0.75}',
                    "parse_error": "",
                    "error": "",
                },
            ):
                report = local_benchmark_report(root, models=["qwen3:1.7b"], roles=["json_normalizer"], write=True)

            self.assertTrue((root / ".hivemind" / "local_benchmark.json").exists())
            self.assertEqual(report["json_validity"], 1.0)
            self.assertEqual(report["roles_tested"], ["json_normalizer"])
            self.assertEqual(report["results"][0]["latency_ms"], 123)

    def test_auto_loop_dry_run_only_writes_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = prepare_run_until_verification(root)

            report = auto_loop(root, paths.run_id, max_steps=3, execute=False, allowed_actions=["verify"])

            self.assertEqual(report["mode"], "dry_run")
            self.assertEqual(report["status"], "planned")
            self.assertEqual(report["proposed_steps"][0]["action"], "verify")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "dry_run_requires_--execute")
            self.assertTrue((paths.artifacts / "auto_loop_plan.json").exists())
            self.assertIn("not_run", (paths.run_dir / "verification.yaml").read_text(encoding="utf-8"))

    def test_auto_loop_execute_requires_allowlisted_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = prepare_run_until_verification(root)

            blocked = auto_loop(root, paths.run_id, execute=True, allowed_actions=[])
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["blocked_steps"][0]["block_reason"], "action_not_allowlisted")

            executed = auto_loop(root, paths.run_id, execute=True, allowed_actions=["verify"])
            self.assertEqual(executed["executed_steps"][0]["action"], "verify")
            self.assertNotIn("not_run", (paths.run_dir / "verification.yaml").read_text(encoding="utf-8"))
            validation = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(validation["verdict"], "pass", validation["issues"])

    def test_auto_loop_blocks_external_provider_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider should not auto execute", project="Hive Mind")
            (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")
            set_agent_status(paths, "local-context-compressor", "completed")

            report = auto_loop(root, paths.run_id, execute=True, allowed_actions=["verify"])

            self.assertEqual(report["proposed_steps"][0]["action"], "provider-invoke")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "provider_cli_execution_blocked")

    def test_auto_loop_stops_after_failed_local_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "local action failure", project="Hive Mind")
            (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")

            with patch("hivemind.harness.run_worker", side_effect=RuntimeError("local backend unavailable")):
                report = auto_loop(root, paths.run_id, max_steps=3, execute=True, allowed_actions=["local-context"])

            self.assertEqual(len(report["executed_steps"]), 1)
            self.assertEqual(report["executed_steps"][0]["result"], "failed")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "executed_action_failed")
            self.assertEqual(report["status"], "blocked")

    def test_flow_advance_prepares_workflow_barrier_without_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = flow_advance(root, task="한글 입력 버그 고치고 테스트 추가", complexity="fast")
            run_dir = root / ".runs" / report["run_id"]

            self.assertEqual(report["mode"], "prepare_only")
            self.assertEqual(report["status"], "waiting_for_local_context")
            self.assertTrue((run_dir / "routing_plan.json").exists())
            self.assertTrue((run_dir / "society_plan.json").exists())
            self.assertTrue((run_dir / "artifacts" / "workflow_state.json").exists())
            self.assertTrue((run_dir / "agents" / "claude" / "planner_result.yaml").exists())
            self.assertTrue((run_dir / "agents" / "codex" / "executor_result.yaml").exists())
            claude_result = yaml.safe_load((run_dir / "agents" / "claude" / "planner_result.yaml").read_text(encoding="utf-8"))
            self.assertEqual(claude_result["status"], "prepared")
            validation = validate_run_artifacts(run_dir, root)
            self.assertEqual(validation["verdict"], "pass", validation["issues"])

    def test_orchestrate_prompt_creates_dag_lifecycle_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = orchestrate_prompt(root, "한글 입력 버그 고치고 테스트 추가", complexity="fast")
            run_dir = root / ".runs" / report["run_id"]
            dag = load_dag(root, report["run_id"])

            self.assertIsNotNone(dag)
            self.assertTrue((run_dir / "routing_plan.json").exists())
            self.assertTrue((run_dir / "society_plan.json").exists())
            self.assertTrue((run_dir / "plan_dag.json").exists())
            self.assertTrue((run_dir / "artifacts" / "workflow_state.json").exists())
            self.assertEqual(report["workflow"]["scheduler"], "plan_dag")
            self.assertEqual(report["next"]["command"], "hive step run local_context")

    def test_local_simple_task_can_execute_as_bounded_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker_output = {
                "runtime": "ollama",
                "model": "qwen3:1.7b",
                "raw": '{"changed": ["summarized"], "verification": [], "unresolved": [], "memory_update_candidates": [], "needs_followup": false}',
                "parsed": {
                    "changed": ["summarized"],
                    "verification": [],
                    "unresolved": [],
                    "memory_update_candidates": [],
                    "needs_followup": False,
                },
            }

            with patch("hivemind.harness.run_worker", return_value=worker_output):
                report = orchestrate_prompt(root, "요약해줘", complexity="fast", execute_local=True)

            run_dir = root / ".runs" / report["run_id"]
            dag = load_dag(root, report["run_id"])

            self.assertIsNotNone(dag)
            self.assertTrue((run_dir / "agents" / "local" / "summarize.json").exists())
            self.assertEqual(dag.by_id("local_summarize").status, "completed")
            self.assertEqual(report["workflow"]["status"], "ready_for_verification")
            self.assertEqual(report["next"]["command"], "hive step run verify")
            events = [record.get("event") for record in read_execution_ledger(root, report["run_id"])]
            self.assertIn("step_started", events)
            self.assertIn("step_completed", events)

    def test_git_diff_report_includes_ledger_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "diff ledger summary", project="Hive Mind")
            artifact = paths.run_dir / "artifact.json"
            artifact.write_text('{"ok": true}\n', encoding="utf-8")
            append_execution_ledger(
                root,
                paths.run_id,
                "step_completed",
                actor="harness",
                step_id="verify",
                status="completed",
                files_touched=["README.md"],
                artifact=artifact.relative_to(root).as_posix(),
            )

            report = git_diff_report(root, paths.run_id)
            text = format_git_diff_report(report)

            self.assertEqual(report["ledger"]["record_count"], 1)
            self.assertTrue(report["ledger"]["hash_chain_ok"])
            self.assertIn("README.md", report["ledger"]["touched_files"])
            self.assertIn("Ledger:", text)
            self.assertIn("README.md", text)

    def test_flow_advance_injects_completed_local_context_into_provider_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker_output = {
                "runtime": "ollama",
                "model": "qwen3:1.7b",
                "raw": '{"summary": "LOCAL-CONTEXT-SENTINEL"}',
                "parsed": {
                    "summary": "LOCAL-CONTEXT-SENTINEL",
                    "key_decisions": [],
                    "open_questions": [],
                    "constraints": [],
                    "risks": [],
                    "handoff_notes": [],
                    "confidence": 0.9,
                    "should_escalate": False,
                    "escalation_reason": "",
                },
            }

            with patch("hivemind.harness.run_worker", return_value=worker_output):
                report = flow_advance(root, task="build feature", complexity="fast", execute_local=True)

            prompt_path = root / ".runs" / report["run_id"] / "agents" / "claude" / "planner_prompt.md"
            self.assertIn("LOCAL-CONTEXT-SENTINEL", prompt_path.read_text(encoding="utf-8"))


def prepare_run_until_verification(root: Path) -> RunPaths:
    paths = create_run(root, "auto loop verification", project="Hive Mind")
    (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")
    set_agent_status(paths, "local-context-compressor", "completed")
    set_agent_status(paths, "claude-planner", "prepared")
    set_agent_status(paths, "codex-executor", "prepared")
    return paths


if __name__ == "__main__":
    unittest.main()
