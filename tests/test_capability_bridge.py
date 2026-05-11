import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.capability_bridge import bridge_status, recommend_for
from hivemind.harness import ask_router, create_run, ensure_capabilityos_recommendation, load_run


class CapabilityBridgeTest(unittest.TestCase):
    def test_route_phase_records_capabilityos_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            capabilityos_root = self._fake_capabilityos(base / "CapabilityOS")

            with patch.dict(
                os.environ,
                {"HIVE_CAPABILITYOS_SOURCE_ROOT": capabilityos_root.as_posix(), "HIVE_DISABLE_CAPABILITYOS": ""},
            ):
                plan_path = ask_router(root, "summarize capability routing fallback", complexity="fast")

            paths, state = load_run(root, plan_path.parent.name)
            recommendation = state.get("capability_recommendation")
            bridge = state.get("capability_bridge")

            self.assertTrue(plan_path.exists())
            self.assertIsInstance(recommendation, dict)
            self.assertEqual(recommendation["recommended_capability"], "cap_test_recommender")
            self.assertEqual(recommendation["score"], 42)
            self.assertEqual(recommendation["evidence_refs"], ["docs/contracts/ASC-0002-capabilityos-executable-surface.md"])
            self.assertEqual(bridge["bridge_status"], "ok")
            self.assertTrue((root / bridge["artifact"]).exists())
            events = paths.events.read_text(encoding="utf-8")
            self.assertIn("capability_recommendation_retrieved", events)

    def test_route_phase_is_nonblocking_when_capabilityos_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            missing = base / "missing-CapabilityOS"

            with patch.dict(
                os.environ,
                {"HIVE_CAPABILITYOS_SOURCE_ROOT": missing.as_posix(), "HIVE_DISABLE_CAPABILITYOS": ""},
            ):
                plan_path = ask_router(root, "summarize without CapabilityOS", complexity="fast")

            _paths, state = load_run(root, plan_path.parent.name)
            bridge = state.get("capability_bridge")

            self.assertTrue(plan_path.exists())
            self.assertIsNone(state.get("capability_recommendation"))
            self.assertEqual(bridge["bridge_status"], "unavailable")
            self.assertIn("CapabilityOS CLI source not found", bridge["reason"])
            self.assertTrue((root / bridge["artifact"]).exists())

    def test_public_bridge_surface_returns_top_recommendation_or_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            capabilityos_root = self._fake_capabilityos(base / "CapabilityOS")
            with patch.dict(
                os.environ,
                {"HIVE_CAPABILITYOS_SOURCE_ROOT": capabilityos_root.as_posix(), "HIVE_DISABLE_CAPABILITYOS": ""},
            ):
                self.assertEqual(bridge_status(), "ok")
                recommendation = recommend_for("route capability fallback")

            self.assertIsNotNone(recommendation)
            self.assertEqual(recommendation["recommended_capability"], "cap_test_recommender")

    def test_ensure_capabilityos_recommendation_can_degrade_without_router(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hivemind"
            root.mkdir()
            paths = create_run(root, "direct capability bridge check", project="Hive Mind")
            with patch.dict(
                os.environ,
                {"HIVE_CAPABILITYOS_SOURCE_ROOT": (base / "missing").as_posix(), "HIVE_DISABLE_CAPABILITYOS": ""},
            ):
                report = ensure_capabilityos_recommendation(root, paths.run_id)

            self.assertEqual(report["bridge_status"], "unavailable")
            _paths, state = load_run(root, paths.run_id)
            self.assertIsNone(state["capability_recommendation"])

    def _fake_capabilityos(self, root: Path) -> Path:
        package = root / "capabilityos"
        fixture = root / "tests" / "fixtures"
        package.mkdir(parents=True)
        fixture.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (fixture / "capabilities.json").write_text('{"capabilities": []}\n', encoding="utf-8")
        (package / "cli.py").write_text(
            textwrap.dedent(
                """
                from __future__ import annotations

                import argparse
                import json


                def main() -> int:
                    parser = argparse.ArgumentParser()
                    parser.add_argument("--catalog")
                    sub = parser.add_subparsers(dest="cmd", required=True)
                    recommend = sub.add_parser("recommend")
                    recommend.add_argument("--task", required=True)
                    recommend.add_argument("--limit", type=int, default=5)
                    recommend.add_argument("--json", action="store_true")
                    args = parser.parse_args()
                    print(json.dumps({
                        "contract": "capabilityos.recommendations.v1",
                        "task": args.task,
                        "total_candidates": 1,
                        "recommendations": [{
                            "id": "cap_test_recommender",
                            "name": "Test Capability Recommendation",
                            "kind": "catalog",
                            "score": 42,
                            "reason_codes": ["term_match:capability", "recommendation_only"],
                            "fallback_ids": ["cap_test_fallback"],
                            "risk_notes": ["local_read_only"],
                            "evidence_refs": ["docs/contracts/ASC-0002-capabilityos-executable-surface.md"],
                            "requires_network": False,
                            "executes_tools": False,
                            "privacy": "local"
                        }]
                    }))
                    return 0


                if __name__ == "__main__":
                    raise SystemExit(main())
                """
            ).lstrip(),
            encoding="utf-8",
        )
        return root


if __name__ == "__main__":
    unittest.main()
