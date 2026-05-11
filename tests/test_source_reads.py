from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.arrival_pack import build_arrival_pack
from hivemind.harness import create_run
from hivemind.source_reads import load_registry, record_source_read, summarize_source_reads


class SourceReadsTest(unittest.TestCase):
    def test_records_source_read_without_raw_source_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "source read smoke")

            record = record_source_read(
                root,
                run_id=paths.run_id,
                agent="codex",
                role="executor",
                source="docs/example.md",
                interpretation="implementation view",
            )
            registry = load_registry(root, paths.run_id)
            encoded = json.dumps(registry, ensure_ascii=False)

            self.assertEqual(registry["schema_version"], "hive.source_reads.v1")
            self.assertEqual(len(registry["records"]), 1)
            self.assertEqual(record["source_ref"], "docs/example.md")
            self.assertEqual(record["agent"], "codex")
            self.assertTrue(record["privacy"]["path_or_ref_only"])
            self.assertFalse(record["privacy"]["raw_source_body_included"])
            self.assertNotIn("raw_body", encoded)

    def test_summary_flags_shared_source_divergent_interpretations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "source divergent smoke")
            record_source_read(
                root,
                run_id=paths.run_id,
                agent="codex",
                source="docs/shared.md",
                interpretation="ship implementation first",
            )
            record_source_read(
                root,
                run_id=paths.run_id,
                agent="claude",
                source="docs/shared.md",
                interpretation="hold for policy review",
            )

            summary = summarize_source_reads(root, paths.run_id)

            self.assertEqual(summary["record_count"], 2)
            self.assertEqual(summary["source_count"], 1)
            self.assertEqual(summary["shared_source_count"], 1)
            self.assertEqual(summary["divergent_source_count"], 1)
            self.assertEqual(summary["divergent_sources"][0]["recommended_action"], "reconcile_interpretations")

    def test_arrival_pack_surfaces_source_read_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "arrival source read smoke")
            record_source_read(root, run_id=paths.run_id, agent="codex", source="docs/shared.md", interpretation="code")
            record_source_read(root, run_id=paths.run_id, agent="claude", source="docs/shared.md", interpretation="policy")

            pack = build_arrival_pack(root, paths.run_id)

            self.assertEqual(pack["source_reads"]["divergent_source_count"], 1)
            self.assertTrue(any(item["kind"] == "source_read_reconciliation" for item in pack["blocked_items"]))
            self.assertTrue(any(item["kind"] == "source_reads" for item in pack["latest_artifacts"]))
            self.assertTrue(any("source-read summary" in item["command"] for item in pack["suggested_commands"]))

    def test_cli_record_and_summary_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "source cli smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            recorded = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "source-read",
                    "record",
                    "--run",
                    run_id,
                    "--agent",
                    "codex",
                    "--source",
                    "docs/example.md",
                    "--interpretation",
                    "implementation",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            record = json.loads(recorded.stdout)
            self.assertEqual(record["agent"], "codex")

            summarized = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "source-read",
                    "summary",
                    "--run",
                    run_id,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            summary = json.loads(summarized.stdout)
            self.assertEqual(summary["kind"], "hive_source_read_summary")
            self.assertEqual(summary["record_count"], 1)


if __name__ == "__main__":
    unittest.main()
