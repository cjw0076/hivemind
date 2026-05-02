import curses
import unittest

from hivemind.tui import update_composer


class TuiComposerTest(unittest.TestCase):
    def test_printable_keys_append_to_composer(self) -> None:
        action, text = update_composer("", ord("w"))
        self.assertEqual(action, "editing")
        self.assertEqual(text, "w")

        action, text = update_composer(text, ord("h"))
        self.assertEqual(action, "editing")
        self.assertEqual(text, "wh")

    def test_enter_submits_non_empty_composer(self) -> None:
        action, text = update_composer("who are in there", 10)
        self.assertEqual(action, "submit")
        self.assertEqual(text, "who are in there")

    def test_backspace_and_escape_edit_composer(self) -> None:
        action, text = update_composer("abc", curses.KEY_BACKSPACE)
        self.assertEqual(action, "editing")
        self.assertEqual(text, "ab")

        action, text = update_composer("abc", 27)
        self.assertEqual(action, "clear")
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
