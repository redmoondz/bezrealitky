from unittest import TestCase

from src.scraper import parse_listing, parse_page


SEARCH_HTML = """
<main>
  <article><a href="/properties-flats-houses/123-first">First</a></article>
  <article><a href="/properties-flats-houses/123-first">Duplicate image</a></article>
  <article><a href="https://www.bezrealitky.com/properties-flats-houses/456-second">Second</a></article>
  <a href="/search?offerType=PRONAJEM&page=2">Next</a>
</main>
"""

LISTING_HTML = """
<main>
  <h1><span>Flat to rent</span> Studio • 30 m² without real estate <span>Za Humny, Modřice</span></h1>
  <div role="tabpanel"><p>First paragraph.</p><p>Second paragraph.</p></div>
  <table>
    <tr><th>Layout</th><td>Studio</td></tr>
    <tr><th>Floor</th><td>2. floor out of 2</td></tr>
    <tr><th>Listing ID</th><td>875675</td></tr>
    <tr><th>Price per unit</th><td>CZK 433.33 / m²</td></tr>
    <tr><th>Available from</th><td>01/09/2026</td></tr>
    <tr><th>Fully furnished</th><td>Partly</td></tr>
    <tr><th>Heating</th><td>Electric boiler</td></tr>
    <tr><th>Usable area</th><td>30 m²</td></tr>
  </table>
  <section><span>Monthly rent</span><strong>CZK 13,000</strong></section>
  <section><span>+ Service charges</span><strong>CZK 1,225</strong></section>
  <section><span>+ Utility charges</span><strong>CZK 2,500</strong></section>
  <section><span>+ Refundable deposit</span><strong>CZK 20,000</strong></section>
</main>
"""


class ScraperTests(TestCase):
    def test_parses_search_page_and_next_page(self):
        listings, next_url = parse_page(SEARCH_HTML, "https://www.bezrealitky.com/search?page=1")
        self.assertEqual(
            listings,
            [
                "https://www.bezrealitky.com/properties-flats-houses/123-first",
                "https://www.bezrealitky.com/properties-flats-houses/456-second",
            ],
        )
        self.assertEqual(
            next_url,
            "https://www.bezrealitky.com/search?offerType=PRONAJEM&page=2",
        )

    def test_parses_listing_fields_and_total(self):
        listing = parse_listing(
            LISTING_HTML,
            "https://www.bezrealitky.com/properties-flats-houses/875675-example",
        )
        self.assertEqual(listing.listing_id, "875675")
        self.assertEqual(listing.format, "Studio")
        self.assertEqual(listing.area, "30")
        self.assertEqual(listing.monthly_rent, "13000")
        self.assertEqual(listing.service_charges, "1225")
        self.assertEqual(listing.utility_charges, "2500")
        self.assertEqual(listing.refundable_deposit, "20000")
        self.assertEqual(listing.total_price, "16725")
        self.assertEqual(listing.currency, "CZK")
        self.assertEqual(listing.price_per_unit, "433.33")
        self.assertEqual(listing.location, "Za Humny, Modřice")
        self.assertEqual(listing.description, "First paragraph.\nSecond paragraph.")
