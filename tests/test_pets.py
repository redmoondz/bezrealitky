from unittest import TestCase

from src.pets import classify_pets_friendly


class PetsFriendlyClassificationTests(TestCase):
    def test_detects_czech_positive_phrase(self):
        self.assertEqual(
            classify_pets_friendly("Byt je vhodný i pro chov zvířat. Domácí mazlíčci vítáni."),
            "True",
        )

    def test_detects_czech_negative_phrase(self):
        self.assertEqual(
            classify_pets_friendly("V bytě je zakázán chov zvířat, bez zvířat prosím."),
            "False",
        )

    def test_negative_wins_when_text_also_looks_positive(self):
        self.assertEqual(classify_pets_friendly("Pets not allowed in this apartment."), "False")

    def test_detects_english_positive_phrase(self):
        self.assertEqual(classify_pets_friendly("This flat is pet friendly."), "True")

    def test_returns_empty_when_no_signal(self):
        self.assertEqual(
            classify_pets_friendly("Moderní byt 1+kk s balkónem v cihlové budově."),
            "",
        )

    def test_returns_empty_for_blank_description(self):
        self.assertEqual(classify_pets_friendly(""), "")

    def test_fuzzy_match_tolerates_missing_diacritics_and_typos(self):
        self.assertEqual(classify_pets_friendly("Domaci mazlicci vitani v bytě."), "True")

    def test_fuzzy_match_tolerates_typo_in_negative_phrase(self):
        self.assertEqual(classify_pets_friendly("Bohuzel, bez zvirat v tomto byte."), "False")

    def test_negation_before_positive_phrase_flips_to_false(self):
        self.assertEqual(
            classify_pets_friendly("Byt není vhodný pro domácí mazlíčky."),
            "False",
        )

    def test_positive_phrase_separated_by_other_words_is_still_true(self):
        self.assertEqual(
            classify_pets_friendly(
                "Byt je vhodný pro pár, domácí mazlíčci jsou po dohodě vítáni."
            ),
            "True",
        )

    def test_unrelated_window_does_not_fuzzy_match_a_longer_negative_phrase(self):
        # "mazlíčci jsou po" must not be mistaken for "mazlíčci nejsou povoleni"
        # just because they share two of four words.
        self.assertEqual(
            classify_pets_friendly("V okolí bytu žijí i domácí mazlíčci jsou po celý rok."),
            "",
        )
