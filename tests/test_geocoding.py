from unittest import TestCase
from unittest.mock import MagicMock, patch

import requests

from src.geocoding import GeocodingError, resolve_location

BRNO_RESULT = {
    "osm_type": "relation",
    "osm_id": 438171,
    "category": "boundary",
    "type": "administrative",
    "display_name": "Brno, okres Brno-město, South Moravian Region, Czechia",
}


class ResolveLocationTests(TestCase):
    def test_rejects_empty_query(self):
        with self.assertRaises(GeocodingError):
            resolve_location("   ")

    @patch("src.geocoding.requests.get")
    def test_resolves_first_boundary_relation(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: [
                {"osm_type": "node", "category": "place"},
                BRNO_RESULT,
            ]
        )
        osm_value, region_osm_id = resolve_location("Brno")
        self.assertEqual(osm_value, "Brno, okres Brno-město, South Moravian Region, Czechia")
        self.assertEqual(region_osm_id, "R438171")

    @patch("src.geocoding.requests.get")
    def test_raises_when_no_boundary_relation_found(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: [{"osm_type": "node", "category": "place"}])
        with self.assertRaises(GeocodingError):
            resolve_location("nonexistent place xyz")

    @patch("src.geocoding.requests.get", side_effect=requests.RequestException("network down"))
    def test_wraps_request_errors(self, mock_get):
        with self.assertRaises(GeocodingError):
            resolve_location("Brno")
