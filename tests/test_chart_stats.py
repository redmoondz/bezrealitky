from unittest import TestCase

from bot.chart_stats import (
    format_counts,
    numeric_values,
    pets_counts,
    price_area_pairs,
    price_per_unit_values,
)


class NumericValuesTests(TestCase):
    def test_skips_missing_values(self):
        rows = [{"area": 40}, {"area": None}, {"area": 60}]
        self.assertEqual(numeric_values(rows, "area"), [40, 60])


class PricePerUnitValuesTests(TestCase):
    def test_divides_price_by_area(self):
        rows = [{"total_price": 20000, "area": 100}, {"total_price": None, "area": 50}]
        self.assertEqual(price_per_unit_values(rows), [200.0])

    def test_skips_zero_area_to_avoid_division_by_zero(self):
        rows = [{"total_price": 20000, "area": 0}]
        self.assertEqual(price_per_unit_values(rows), [])


class PriceAreaPairsTests(TestCase):
    def test_pairs_only_rows_with_both_fields(self):
        rows = [{"area": 40, "total_price": 15000}, {"area": None, "total_price": 12000}]
        self.assertEqual(price_area_pairs(rows), [(40.0, 15000.0)])


class FormatCountsTests(TestCase):
    def test_folds_everything_past_top_three_into_other(self):
        rows = (
            [{"format": "1+kk"}] * 5
            + [{"format": "2+kk"}] * 4
            + [{"format": "3+kk"}] * 3
            + [{"format": "4+kk"}] * 2
            + [{"format": "5+kk"}] * 1
        )
        result = dict(format_counts(rows))
        self.assertEqual(result, {"1+kk": 5, "2+kk": 4, "3+kk": 3, "Other": 3})

    def test_blank_format_counts_as_unknown(self):
        rows = [{"format": ""}, {"format": None}]
        self.assertEqual(format_counts(rows), [("Unknown", 2)])


class PetsCountsTests(TestCase):
    def test_orders_yes_no_unknown_and_omits_absent_labels(self):
        rows = [{"pets_friendly": True}, {"pets_friendly": None}, {"pets_friendly": None}]
        self.assertEqual(pets_counts(rows), [("Yes", 1), ("Unknown", 2)])
