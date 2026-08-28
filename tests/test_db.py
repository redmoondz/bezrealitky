"""Pure-logic tests for src/db.py — no live Postgres required.

End-to-end behavior (schema creation, the is_relevant sync transaction,
notification bookkeeping) is verified manually against a real Postgres
container as part of this change; see the project README.
"""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from src import db
from src.scraper import Listing


class RowFromListingTests(TestCase):
    def test_converts_numeric_text_and_json_fields(self):
        listing = Listing(
            listing_id="1",
            name="Flat",
            area="30.5",
            total_price="16725",
            currency="CZK",
            images='["https://example/a.jpg", "https://example/b.jpg"]',
            floor_number="2",
            floor_total="4",
            pets_friendly="True",
            air_conditioning="False",
        )
        row = db.row_from_listing(listing)
        self.assertEqual(row["area"], Decimal("30.5"))
        self.assertEqual(row["total_price"], Decimal("16725"))
        self.assertEqual(row["floor_number"], 2)
        self.assertEqual(row["floor_total"], 4)
        self.assertIs(row["pets_friendly"], True)
        self.assertIs(row["air_conditioning"], False)
        self.assertEqual(row["images"].obj, ["https://example/a.jpg", "https://example/b.jpg"])

    def test_converts_every_boolean_column_not_just_pets(self):
        listing = Listing(
            listing_id="1",
            pets_friendly="True",
            air_conditioning="False",
            has_washing_machine="True",
            has_dryer="",
            has_internet="True",
            has_dishwasher="False",
            mansard="True",
        )
        row = db.row_from_listing(listing)
        self.assertIs(row["pets_friendly"], True)
        self.assertIs(row["air_conditioning"], False)
        self.assertIs(row["has_washing_machine"], True)
        self.assertIsNone(row["has_dryer"])
        self.assertIs(row["has_internet"], True)
        self.assertIs(row["has_dishwasher"], False)
        self.assertIs(row["mansard"], True)

    def test_blank_optional_fields_become_none(self):
        listing = Listing(listing_id="1", images="[]")
        row = db.row_from_listing(listing)
        self.assertIsNone(row["area"])
        self.assertIsNone(row["floor_number"])
        self.assertIsNone(row["pets_friendly"])
        self.assertEqual(row["images"].obj, [])

    def test_unknown_pets_friendly_is_none_not_false(self):
        listing = Listing(listing_id="1", pets_friendly="")
        row = db.row_from_listing(listing)
        self.assertIsNone(row["pets_friendly"])

    def test_malformed_images_json_becomes_empty_list(self):
        listing = Listing(listing_id="1", images="not json")
        row = db.row_from_listing(listing)
        self.assertEqual(row["images"].obj, [])


class SetUserPreferenceTests(TestCase):
    def test_rejects_unknown_column_before_touching_the_connection(self):
        # The column-name whitelist check runs before any connection use, so a
        # deliberately unusable ``conn`` still proves the guard fires first.
        with self.assertRaises(ValueError):
            db.set_user_preference(None, 1, "not_a_real_column", "x")


class DsnTests(TestCase):
    def test_reads_connection_params_from_environment(self):
        env = {
            "POSTGRES_HOST": "example-host",
            "POSTGRES_PORT": "6543",
            "POSTGRES_DB": "exampledb",
            "POSTGRES_USER": "exampleuser",
            "POSTGRES_PASSWORD": "secret",
        }
        with patch.dict("os.environ", env, clear=False):
            dsn = db.get_dsn()
        self.assertIn("host=example-host", dsn)
        self.assertIn("port=6543", dsn)
        self.assertIn("dbname=exampledb", dsn)
        self.assertIn("user=exampleuser", dsn)
        self.assertIn("password=secret", dsn)
