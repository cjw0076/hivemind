from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import append_hive_activity, create_run, debate_topic
from hivemind.live import build_live_report, build_memoryos_observability_report, format_live_report, sanitize_summary
from hivemind.plan_dag import build_dag, save_dag
from hivemind.protocol import build_execution_intent, check_intent, decide_intent, save_intent
from hivemind.workloop import append_execution_ledger


class LiveSurfaceTest(unittest.TestCase):
    def test_live_report_hides_paths_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "live hides paths")
            append_execution_ledger(
                root,
                paths.run_id,
                "step_completed",
                actor="harness",
                step_id="verify",
                status="completed",
                files_touched=[".runs/run_x/verification.yaml"],
            )

            report = build_live_report(root, paths.run_id)
            output = format_live_report(report)

            self.assertIn("Hive Live", output)
            self.assertIn("Paths hidden", output)
            self.assertNotIn(".runs/run_x/verification.yaml", output)

    def test_live_report_shows_protocol_waiting_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "live authority")
            dag = build_dag(paths.run_id, "live authority", "implementation")
            save_dag(root, dag)
            intent = build_execution_intent(root, dag, "planner", execute=True)
            save_intent(root, intent)
            check_intent(root, paths.run_id, intent.intent_id)
            decide_intent(root, paths.run_id, intent.intent_id)

            output = format_live_report(build_live_report(root, paths.run_id))
            self.assertIn("Authority:", output)
            self.assertIn("planner", output)
            self.assertIn("waiting", output)
            self.assertIn("verifier", output)

    def test_cli_live_prompt_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "live",
                    "한글",
                    "prompt",
                    "--json",
                    "--tail",
                    "4",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(completed.stdout)
            self.assertEqual(data["task"], "한글 prompt")
            self.assertTrue(data["paths_hidden"])
            self.assertIn("log", data)

    def test_sanitize_summary_hides_artifact_paths(self) -> None:
        text = "prepared result=.runs/run_x/agents/claude/planner_result.yaml path=/home/user/workspaces/a"
        sanitized = sanitize_summary(text, show_paths=False)
        self.assertIn("result=<hidden>", sanitized)
        self.assertIn("path=<hidden>", sanitized)
        self.assertNotIn(".runs/run_x", sanitized)
        self.assertNotIn("/home/user", sanitized)

    def test_memoryos_observability_report_is_graph_shaped_and_hides_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "neural map export")
            append_execution_ledger(
                root,
                paths.run_id,
                "step_completed",
                actor="harness",
                step_id="context",
                status="completed",
                files_touched=[".runs/run_x/context_pack.md"],
            )
            (paths.run_dir / "memory_drafts.json").write_text(
                json.dumps(
                    {
                        "memory_drafts": [
                            {
                                "type": "decision",
                                "content": "Use MemoryOS neural map for observability.",
                                "origin": "user",
                                "confidence": 0.9,
                                "status": "draft",
                                "project": "Hive Mind",
                                "raw_refs": [".runs/run_x/transcript.md"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = build_memoryos_observability_report(root, paths.run_id)
            encoded = json.dumps(report, ensure_ascii=False)

            self.assertEqual(report["kind"], "memoryos_neural_map_read_model")
            self.assertTrue(report["paths_hidden"])
            self.assertIn("graph", report)
            self.assertTrue(any(node["type"] == "hive_run" for node in report["graph"]["nodes"]))
            self.assertTrue(any(node["type"] == "agent_turn" for node in report["graph"]["nodes"]))
            self.assertTrue(any(node["type"] == "memory_draft" for node in report["graph"]["nodes"]))
            self.assertTrue(any(edge["type"] == "participates_in" for edge in report["graph"]["edges"]))
            self.assertEqual(report["memoryos_contract"], "HiveLiveEventV1")
            self.assertTrue(report["events"])
            event = report["events"][0]
            self.assertIn("event_id", event)
            self.assertIn("event_type", event)
            self.assertEqual(event["run_id"], paths.run_id)
            self.assertIn("timestamp", event)
            self.assertIn("agent_id", event)
            self.assertIn("payload", event)
            self.assertNotIn(".runs/run_x", encoded)
            self.assertNotIn("/home/user", encoded)

    def test_memoryos_events_use_stable_ledger_ids_across_tail_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "stable memoryos events")
            first = append_execution_ledger(
                root,
                paths.run_id,
                "step_started",
                actor="harness",
                step_id="context",
                status="running",
            )
            second = append_execution_ledger(
                root,
                paths.run_id,
                "step_completed",
                actor="harness",
                step_id="context",
                status="completed",
            )

            short_report = build_memoryos_observability_report(root, paths.run_id, tail=1)
            long_report = build_memoryos_observability_report(root, paths.run_id, tail=4)
            short_by_seq = {
                event["payload"].get("ledger_seq"): event
                for event in short_report["events"]
                if event["payload"].get("source") == "execution_ledger"
            }
            long_by_seq = {
                event["payload"].get("ledger_seq"): event
                for event in long_report["events"]
                if event["payload"].get("source") == "execution_ledger"
            }

            self.assertEqual(long_by_seq[first["seq"]]["payload"]["ledger_hash"], first["hash"])
            self.assertEqual(short_by_seq[second["seq"]]["event_id"], long_by_seq[second["seq"]]["event_id"])
            self.assertEqual(short_by_seq[second["seq"]]["payload"]["ledger_hash"], second["hash"])
            self.assertEqual(short_by_seq[second["seq"]]["id"], short_by_seq[second["seq"]]["event_id"])

    def test_memoryos_activity_event_identity_is_independent_from_path_hiding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "activity id stable")
            append_hive_activity(
                paths,
                "hive-mind",
                "log",
                "prepared result=.runs/run_x/result.json path=/home/user/workspaces/a",
                {"artifact": ".runs/run_x/result.json"},
            )

            hidden = build_memoryos_observability_report(root, paths.run_id, tail=10, show_paths=False)
            shown = build_memoryos_observability_report(root, paths.run_id, tail=10, show_paths=True)
            hidden_event = next(event for event in hidden["events"] if event["event_type"] == "log")
            shown_event = next(event for event in shown["events"] if event["event_type"] == "log")

            self.assertEqual(hidden_event["event_id"], shown_event["event_id"])
            self.assertIn("<hidden>", hidden_event["summary"])
            self.assertIn(".runs/run_x", shown_event["summary"])

    def test_memoryos_observability_report_includes_authority_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "authority graph")
            dag = build_dag(paths.run_id, "authority graph", "implementation")
            save_dag(root, dag)
            intent = build_execution_intent(root, dag, "planner", execute=True)
            save_intent(root, intent)
            check_intent(root, paths.run_id, intent.intent_id)
            decide_intent(root, paths.run_id, intent.intent_id)

            report = build_memoryos_observability_report(root, paths.run_id)
            nodes = report["graph"]["nodes"]
            edges = report["graph"]["edges"]

            self.assertTrue(any(node["type"] == "authority_gate" for node in nodes))
            self.assertTrue(any(edge["type"] == "gates" for edge in edges))
            self.assertGreaterEqual(report["summary"]["authority_gate_count"], 1)

    def test_live_report_summarizes_debate_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            debate = debate_topic(root, "review release readiness", participants=["claude", "gemini"], execute=False)

            report = build_live_report(root, debate["run_id"])
            output = format_live_report(report)

            self.assertEqual(report["debate"]["status"], "review_ready")
            self.assertEqual(report["debate"]["participant_count"], 2)
            self.assertEqual(report["debate"]["prepared_output_count"], 4)
            self.assertEqual(len(report["debate"]["readiness"]), 2)
            self.assertIn("Debate:", output)
            self.assertIn("barrier_ready=True", output)

    def test_cli_live_memoryos_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "live",
                    "한글",
                    "memoryos",
                    "--memoryos",
                    "--tail",
                    "4",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(completed.stdout)
            self.assertEqual(data["kind"], "memoryos_neural_map_read_model")
            self.assertEqual(data["run"]["task"], "한글 memoryos")
            self.assertTrue(data["paths_hidden"])
            self.assertIn("nodes", data["graph"])


if __name__ == "__main__":
    unittest.main()
