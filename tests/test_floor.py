from unittest import TestCase

from src.floor import parse_floor


class FloorParsingTests(TestCase):
    def test_parses_numbered_floor_with_total(self):
        self.assertEqual(parse_floor("2. floor out of 2"), ("2", "2"))

    def test_parses_ground_floor_with_total(self):
        self.assertEqual(parse_floor("Ground floor out of 5"), ("0", "5"))

    def test_parses_numbered_floor_without_total(self):
        self.assertEqual(parse_floor("3. floor"), ("3", ""))

    def test_parses_ground_floor_without_total(self):
        self.assertEqual(parse_floor("Ground floor"), ("0", ""))

    def test_ignores_surrounding_whitespace_and_case(self):
        self.assertEqual(parse_floor("  10.  FLOOR  out  of  12  "), ("10", "12"))

    def test_returns_empty_pair_for_blank_input(self):
        self.assertEqual(parse_floor(""), ("", ""))

    def test_returns_empty_pair_for_unrecognized_text(self):
        self.assertEqual(parse_floor("Loft"), ("", ""))
