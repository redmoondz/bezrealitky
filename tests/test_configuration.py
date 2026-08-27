from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from src.configuration import (
    ConfigurationError,
    apply_updates,
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
