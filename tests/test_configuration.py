from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from src.configuration import (
    ConfigurationError,
    apply_updates,
    build_search_url,
    load_config,
    normalize_url_input,
    reset_config,
    save_config,
    validate_price_range,
    validate_search_url,
)


class ConfigurationTests(TestCase):
    def test_imports_markdown_url_and_unescapes_ampersands(self):
        value = "[search](https://www.bezrealitky.com/search?disposition=A\\&disposition=B\\&priceFrom=500)"
        self.assertEqual(
            normalize_url_input(value),
            "https://www.bezrealitky.com/search?disposition=A&disposition=B&priceFrom=500",
        )

    def test_rejects_wrong_domain(self):
        with self.assertRaises(ConfigurationError):
            validate_search_url("https://sample_url.com/search?priceFrom=1")

    def test_updates_prices_and_preserves_repeated_parameters(self):
        config = {
            "version": 1,
            "search": {
                "url": "https://www.bezrealitky.com/search?disposition=A&disposition=B&priceFrom=500&priceTo=1000"
            },
            "scraper": {
                "output_csv": "output/test.csv",
                "request_timeout_seconds": 30,
                "delay_seconds": 0,
                "max_retries": 3,
                "user_agent": "test",
            },
        }
        updated = apply_updates(config, price_from=750, price_to=1200)
        query = parse_qs(urlparse(updated["search"]["url"]).query)
        self.assertEqual(query["disposition"], ["A", "B"])
        self.assertEqual(query["priceFrom"], ["750"])
        self.assertEqual(query["priceTo"], ["1200"])

    def test_rejects_inverted_price_range(self):
        url = "https://www.bezrealitky.com/search?priceFrom=1200&priceTo=750"
        with self.assertRaises(ConfigurationError):
            validate_price_range(url)

    def test_save_load_and_reset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            defaults = reset_config(path)
            defaults["scraper"]["output_csv"] = "changed.csv"
            save_config(defaults, path)
            self.assertEqual(load_config(path)["scraper"]["output_csv"], "changed.csv")
            restored = reset_config(path)
            self.assertEqual(restored["scraper"]["output_csv"], "output/bezrealitky_listings.csv")


class BuildSearchUrlTests(TestCase):
    def test_builds_minimal_nationwide_url(self):
        url = build_search_url(offer_type="PRONAJEM", estate_type="BYT", currency="CZK")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(urlparse(url).netloc, "www.bezrealitky.com")
        self.assertEqual(query["offerType"], ["PRONAJEM"])
        self.assertEqual(query["estateType"], ["BYT"])
        self.assertEqual(query["currency"], ["CZK"])
        self.assertNotIn("regionOsmIds", query)

    def test_builds_url_with_location_and_price(self):
        url = build_search_url(
            offer_type="PRONAJEM",
            estate_type="BYT",
            currency="EUR",
            location=("Brno, okres Brno-město, South Moravian Region, Czechia", "R438171"),
            price_to=1500,
        )
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["regionOsmIds"], ["R438171"])
        self.assertEqual(query["osm_value"], ["Brno, okres Brno-město, South Moravian Region, Czechia"])
        self.assertEqual(query["location"], ["exact"])
        self.assertEqual(query["priceTo"], ["1500"])

    def test_rejects_unknown_offer_type(self):
        with self.assertRaises(ConfigurationError):
            build_search_url(offer_type="RENT", estate_type="BYT", currency="CZK")

    def test_rejects_unknown_estate_type(self):
        with self.assertRaises(ConfigurationError):
            build_search_url(offer_type="PRONAJEM", estate_type="APARTMENT", currency="CZK")

    def test_rejects_unknown_currency(self):
        with self.assertRaises(ConfigurationError):
            build_search_url(offer_type="PRONAJEM", estate_type="BYT", currency="USD")
