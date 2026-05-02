import json
from pathlib import Path
import tempfile
import unittest

from hivemind.importers import import_path_with_warnings


class ImportWarningsTest(unittest.TestCase):
    def test_non_object_conversation_warns_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "conversations.json"
            path.write_text(
                json.dumps(
                    [
                        "bad-record",
                        {
                            "id": "ok",
                            "title": "Valid conversation",
                            "mapping": {},
                        },
                    ]
                ),
                encoding="utf-8",
            )
            result = import_path_with_warnings(path)
            self.assertTrue(result.nodes)
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("Skipped non-object conversation", result.warnings[0]["message"])

    def test_malformed_json_warns_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            result = import_path_with_warnings(path)
            self.assertEqual(result.nodes, [])
            self.assertEqual(result.edges, [])
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("JSON parse failed", result.warnings[0]["message"])


if __name__ == "__main__":
    unittest.main()
