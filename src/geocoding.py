"""Resolves a free-text place name (e.g. "Brno") to the OSM administrative
region that bezrealitky.com's own location filter runs on.

bezrealitky's ``osm_value``/``regionOsmIds`` search params are literally
OpenStreetMap Nominatim's ``display_name``/``osm_id`` for a relation-type
result — confirmed by geocoding "Brno" here and getting back the exact
``osm_id=438171``/``display_name="Brno, okres Brno-město, South Moravian
Region, Czechia"`` pair already hardcoded in ``config/defaults.yaml``. So the
onboarding location question can resolve through the same public API rather
than requiring the user to build the URL themselves on the site.
"""

from __future__ import annotations

import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy requires a descriptive User-Agent identifying the
# application (anonymous/browser-like UAs get blocked).
USER_AGENT = "BezrealitkyResearchParser/1.0 (onboarding location lookup)"
REQUEST_TIMEOUT_SECONDS = 10


class GeocodingError(ValueError):
    """Raised when a place name can't be resolved to a usable region."""


def resolve_location(query: str) -> tuple[str, str]:
    """Returns ``(osm_value, region_osm_id)`` for the first Czech
    administrative region matching ``query``, e.g. ``("Brno, okres
    Brno-město, South Moravian Region, Czechia", "R438171")``.
    """
    query = query.strip()
    if not query:
        raise GeocodingError("Location must not be empty")
    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={
                "q": query,
                "countrycodes": "cz",
                "format": "jsonv2",
                "accept-language": "en",
                "limit": 5,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise GeocodingError(f"Location lookup failed: {exc}") from exc

    for result in results:
        if result.get("osm_type") == "relation" and result.get("category") == "boundary":
            return result["display_name"], f"R{result['osm_id']}"
    raise GeocodingError(f"Could not find a Czech city or region matching {query!r}")
