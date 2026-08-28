from unittest import TestCase

from src.amenities import classify_amenities


class AmenityClassificationTests(TestCase):
    def test_detects_air_conditioning(self):
        result = classify_amenities("Byt je vybaven klimatizací a je světlý.")
        self.assertEqual(result["air_conditioning"], "True")

    def test_detects_negated_air_conditioning(self):
        result = classify_amenities("Byt je bez klimatizace.")
        self.assertEqual(result["air_conditioning"], "False")

    def test_detects_washing_machine_in_english(self):
        result = classify_amenities("The kitchen has a washing machine and a dishwasher.")
        self.assertEqual(result["has_washing_machine"], "True")
        self.assertEqual(result["has_dishwasher"], "True")

    def test_detects_negated_dryer(self):
        result = classify_amenities("Apartment comes without a dryer.")
        self.assertEqual(result["has_dryer"], "False")

    def test_detects_internet(self):
        result = classify_amenities("V ceně nájmu je zahrnut i internet.")
        self.assertEqual(result["has_internet"], "True")

    def test_detects_mansard_in_czech(self):
        result = classify_amenities("Krásný podkrovní byt se šikmými stropy.")
        self.assertEqual(result["mansard"], "True")

    def test_detects_mansard_in_english(self):
        result = classify_amenities("Beautiful attic apartment with sloped ceilings.")
        self.assertEqual(result["mansard"], "True")

    def test_detects_balcony(self):
        result = classify_amenities("Moderní byt 1+kk s balkónem v cihlové budově.")
        self.assertEqual(result["balcony"], "True")

    def test_detects_negated_balcony(self):
        result = classify_amenities("Byt bez balkónu.")
        self.assertEqual(result["balcony"], "False")

    def test_detects_oven_and_microwave_and_fridge(self):
        result = classify_amenities("Kuchyně je vybavena troubou, mikrovlnkou a lednicí.")
        self.assertEqual(result["oven"], "True")
        self.assertEqual(result["microwave"], "True")
        self.assertEqual(result["refrigerator"], "True")

    def test_detects_quiet_surroundings(self):
        result = classify_amenities("Byt se nachází v klidné lokalitě na okraji města.")
        self.assertEqual(result["quiet_surroundings"], "True")

    def test_detects_garage(self):
        result = classify_amenities("K bytu náleží i garáž.")
        self.assertEqual(result["garage"], "True")

    def test_detects_negated_garage(self):
        result = classify_amenities("Apartment comes without a garage.")
        self.assertEqual(result["garage"], "False")

    def test_detects_english_speaking(self):
        result = classify_amenities("Pronajímatel: we speak english, no problem.")
        self.assertEqual(result["english_speaking"], "True")

    def test_returns_empty_for_unrelated_text(self):
        result = classify_amenities("Moderní byt 1+kk v cihlové budově s výtahem.")
        for field in result:
            self.assertEqual(result[field], "", field)

    def test_returns_empty_for_blank_description(self):
        result = classify_amenities("")
        for field in result:
            self.assertEqual(result[field], "", field)

    def test_fields_cover_every_amenity(self):
        result = classify_amenities("")
        self.assertEqual(
            set(result),
            {
                "air_conditioning",
                "has_washing_machine",
                "has_dryer",
                "has_internet",
                "has_dishwasher",
                "mansard",
                "balcony",
                "oven",
                "microwave",
                "refrigerator",
                "quiet_surroundings",
                "garage",
                "english_speaking",
            },
        )
