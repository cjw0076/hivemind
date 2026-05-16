import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hivemind.hive import normalize_argv


class CliEntrypointTest(unittest.TestCase):
    def test_bare_hive_opens_live_surface_on_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv([]), ["live"])

    def test_bare_hive_prints_help_when_not_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=False), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv([]), ["--help"])

    def test_bare_hive_with_root_opens_live_surface_on_tty(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=True), patch.object(sys.stdout, "isatty", return_value=True):
            self.assertEqual(normalize_argv(["--root", "/tmp/hive"]), ["--root", "/tmp/hive", "live"])
            self.assertEqual(normalize_argv(["--root=/tmp/hive"]), ["--root=/tmp/hive", "live"])

    def test_removed_tui_command_is_reserved(self) -> None:
        self.assertEqual(normalize_argv(["tui"]), ["tui"])

    def test_removed_tui_command_is_not_public_parser_choice(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "hivemind.hive", "tui"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_public_help_does_not_advertise_terminal_tui(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "hivemind.hive", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("legacy terminal view", result.stdout)
        self.assertNotIn("tui", result.stdout)

    def test_live_surface_has_idle_state_without_current_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", tmp, "live", "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "no_run")
        self.assertEqual(report["next"]["command"], 'hive live "your task"')

    def test_prompt_shorthand_still_orchestrates(self) -> None:
        self.assertEqual(normalize_argv(["build", "this"]), ["orchestrate", "build this"])
        self.assertEqual(normalize_argv(["--root", "/tmp/hive", "build", "this"]), ["--root", "/tmp/hive", "orchestrate", "build this"])


if __name__ == "__main__":
    unittest.main()
