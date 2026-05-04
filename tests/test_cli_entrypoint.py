import sys
import unittest
from unittest.mock import patch

from hivemind.hive import normalize_argv


class CliEntrypointTest(unittest.TestCase):
    def test_bare_hive_opens_tui_on_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv([]), ["tui"])

    def test_bare_hive_prints_help_when_not_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=False), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv([]), ["--help"])

    def test_bare_hive_with_root_opens_tui_on_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv(["--root", "/tmp/hive"]), ["--root", "/tmp/hive", "tui"])
            self.assertEqual(normalize_argv(["--root=/tmp/hive"]), ["--root=/tmp/hive", "tui"])

    def test_prompt_shorthand_still_orchestrates(self) -> None:
        self.assertEqual(normalize_argv(["build", "this"]), ["orchestrate", "build this"])
        self.assertEqual(normalize_argv(["--root", "/tmp/hive", "build", "this"]), ["--root", "/tmp/hive", "orchestrate", "build this"])


if __name__ == "__main__":
    unittest.main()
