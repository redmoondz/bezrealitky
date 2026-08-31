from decimal import Decimal
from unittest import TestCase

from src.scoring import TOP_MATCH_THRESHOLD, compute_score

NO_PREFERENCES = {
    "wants_pets": None,
    "budget_total_price": None,
    "min_area_m2": None,
    "min_floor_number": None,
    "min_floor_total": None,
    "wants_furnished": None,
}


class ScoringTests(TestCase):
    def test_no_preferences_scores_zero_regardless_of_listing(self):
        listing = {"pets_friendly": True, "total_price": Decimal("10000"), "area": Decimal("50")}
        self.assertEqual(compute_score(listing, NO_PREFERENCES), 0)

    def test_pets_match_scores_bonus(self):
        preferences = {**NO_PREFERENCES, "wants_pets": True}
        listing = {"pets_friendly": True}
        self.assertEqual(compute_score(listing, preferences), 30)

    def test_pets_mismatch_scores_penalty(self):
        preferences = {**NO_PREFERENCES, "wants_pets": True}
        listing = {"pets_friendly": False}
        self.assertEqual(compute_score(listing, preferences), -50)

    def test_pets_unknown_is_neutral(self):
        preferences = {**NO_PREFERENCES, "wants_pets": True}
        listing = {"pets_friendly": None}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_no_pet_preference_ignores_pets_friendly_entirely(self):
        preferences = {**NO_PREFERENCES, "wants_pets": False}
        listing = {"pets_friendly": False}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_within_budget_scores_flat_bonus(self):
        preferences = {**NO_PREFERENCES, "budget_total_price": Decimal("20000")}
        listing = {"total_price": Decimal("18000")}
        self.assertEqual(compute_score(listing, preferences), 15)

    def test_ten_percent_over_budget_tapers_the_bonus(self):
        preferences = {**NO_PREFERENCES, "budget_total_price": Decimal("100")}
        listing = {"total_price": Decimal("110")}
        self.assertEqual(compute_score(listing, preferences), 5)

    def test_exactly_at_the_115_percent_ceiling_scores_zero(self):
        preferences = {**NO_PREFERENCES, "budget_total_price": Decimal("100")}
        listing = {"total_price": Decimal("115")}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_beyond_115_percent_scores_the_suppression_penalty(self):
        preferences = {**NO_PREFERENCES, "budget_total_price": Decimal("100")}
        listing = {"total_price": Decimal("116")}
        self.assertEqual(compute_score(listing, preferences), -1000)

    def test_missing_total_price_is_neutral(self):
        preferences = {**NO_PREFERENCES, "budget_total_price": Decimal("20000")}
        listing = {"total_price": None}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_area_at_or_above_minimum_scores_bonus(self):
        preferences = {**NO_PREFERENCES, "min_area_m2": Decimal("40")}
        listing = {"area": Decimal("40")}
        self.assertEqual(compute_score(listing, preferences), 10)

    def test_area_below_minimum_scores_penalty(self):
        preferences = {**NO_PREFERENCES, "min_area_m2": Decimal("40")}
        listing = {"area": Decimal("35")}
        self.assertEqual(compute_score(listing, preferences), -10)

    def test_floor_number_at_or_above_minimum_scores_bonus(self):
        preferences = {**NO_PREFERENCES, "min_floor_number": 2}
        listing = {"floor_number": 2}
        self.assertEqual(compute_score(listing, preferences), 10)

    def test_floor_number_below_minimum_scores_penalty(self):
        preferences = {**NO_PREFERENCES, "min_floor_number": 2}
        listing = {"floor_number": 0}
        self.assertEqual(compute_score(listing, preferences), -10)

    def test_floor_total_at_or_above_minimum_scores_bonus(self):
        preferences = {**NO_PREFERENCES, "min_floor_total": 4}
        listing = {"floor_total": 5}
        self.assertEqual(compute_score(listing, preferences), 10)

    def test_floor_total_below_minimum_scores_penalty(self):
        preferences = {**NO_PREFERENCES, "min_floor_total": 4}
        listing = {"floor_total": 2}
        self.assertEqual(compute_score(listing, preferences), -10)

    def test_both_floor_preferences_score_independently(self):
        preferences = {**NO_PREFERENCES, "min_floor_number": 2, "min_floor_total": 4}
        listing = {"floor_number": 3, "floor_total": 5}
        self.assertEqual(compute_score(listing, preferences), 20)

    def test_missing_floor_data_is_neutral(self):
        preferences = {**NO_PREFERENCES, "min_floor_number": 2, "min_floor_total": 4}
        listing = {"floor_number": None, "floor_total": None}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_furniture_match_scores_bonus(self):
        preferences = {**NO_PREFERENCES, "wants_furnished": True}
        listing = {"furnished": True}
        self.assertEqual(compute_score(listing, preferences), 15)

    def test_furniture_mismatch_scores_penalty(self):
        preferences = {**NO_PREFERENCES, "wants_furnished": True}
        listing = {"furnished": False}
        self.assertEqual(compute_score(listing, preferences), -20)

    def test_furniture_unknown_is_neutral(self):
        preferences = {**NO_PREFERENCES, "wants_furnished": True}
        listing = {"furnished": None}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_no_furniture_preference_ignores_furnished_entirely(self):
        preferences = {**NO_PREFERENCES, "wants_furnished": False}
        listing = {"furnished": False}
        self.assertEqual(compute_score(listing, preferences), 0)

    def test_rules_combine_additively(self):
        preferences = {
            "wants_pets": True,
            "budget_total_price": Decimal("20000"),
            "min_area_m2": Decimal("40"),
        }
        listing = {"pets_friendly": True, "total_price": Decimal("18000"), "area": Decimal("45")}
        self.assertEqual(compute_score(listing, preferences), 30 + 15 + 10)

    def test_top_match_threshold_matches_a_single_strong_signal(self):
        preferences = {**NO_PREFERENCES, "wants_pets": True}
        listing = {"pets_friendly": True}
        self.assertGreaterEqual(compute_score(listing, preferences), TOP_MATCH_THRESHOLD)
