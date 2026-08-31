from unittest import TestCase

from src.furnished import parse_furnished


class FurnishedParsingTests(TestCase):
    def test_parses_yes(self):
        self.assertEqual(parse_furnished("Yes"), "True")

    def test_parses_no(self):
        self.assertEqual(parse_furnished("No"), "False")

    def test_ignores_surrounding_whitespace_and_case(self):
        self.assertEqual(parse_furnished("  YES  "), "True")

    def test_partly_is_ambiguous_not_guessed(self):
        self.assertEqual(parse_furnished("Partly"), "")

    def test_returns_empty_for_blank_input(self):
        self.assertEqual(parse_furnished(""), "")

    def test_returns_empty_for_unrecognized_text(self):
        self.assertEqual(parse_furnished("Loft"), "")
