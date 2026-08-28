"""Amenity taxonomies for the shared classifier in ``taxonomy.py``.

Unlike ``pets_friendly`` (a policy statement — a bare mention of an animal says
nothing about whether they're allowed), a bare mention of one of these amenities
in a listing description ("klimatizace", "myčka", ...) already *is* the positive
signal, so no stem-proximity fallback is needed here: exact/fuzzy phrase matching
plus the shared negation window (catching "byt je bez klimatizace") is enough.
"""

from __future__ import annotations

try:
    from .taxonomy import Taxonomy, classify
except ImportError:  # Support: python3 src/amenities.py
    from taxonomy import Taxonomy, classify  # type: ignore[no-redef]

AIR_CONDITIONING = Taxonomy(
    positive_phrases=[
        "klimatizace",
        "klimatizací",
        "klimatizaci",
        "s klimatizací",
        "air conditioning",
        "air conditioned",
        "air-conditioned",
    ],
    negative_phrases=[
        "bez klimatizace",
        "žádná klimatizace",
        "no air conditioning",
        "without air conditioning",
    ],
)

WASHING_MACHINE = Taxonomy(
    positive_phrases=[
        "pračka",
        "pračkou",
        "s pračkou",
        "washing machine",
        "washer",
    ],
    negative_phrases=[
        "bez pračky",
        "žádná pračka",
        "no washing machine",
        "without a washing machine",
    ],
)

DRYER = Taxonomy(
    positive_phrases=[
        "sušička",
        "sušičkou",
        "s sušičkou",
        "tumble dryer",
        "clothes dryer",
        "dryer",
    ],
    negative_phrases=[
        "bez sušičky",
        "no dryer",
        "without a dryer",
    ],
)

INTERNET = Taxonomy(
    positive_phrases=[
        "internet",
        "wifi",
        "wi-fi",
        "připojení k internetu",
        "internet connection",
    ],
    negative_phrases=[
        "bez internetu",
        "no internet",
        "without internet",
    ],
)

DISHWASHER = Taxonomy(
    positive_phrases=[
        "myčka",
        "myčkou",
        "myčka nádobí",
        "dishwasher",
    ],
    negative_phrases=[
        "bez myčky",
        "no dishwasher",
        "without a dishwasher",
    ],
)

# No negative phrases: a listing doesn't usually assert "this is NOT an attic
# apartment", so there's nothing to enumerate — the shared negation window
# still catches the rare "bez podkroví"-style phrasing on its own.
MANSARD = Taxonomy(
    positive_phrases=[
        "podkroví",
        "podkrovní byt",
        "podkrovním bytě",
        "mansardový byt",
        "mansardová střecha",
        "mansarda",
        "attic apartment",
        "attic flat",
        "mansard apartment",
    ],
    negative_phrases=[],
)

# Keyed by the exact Listing/listings-column field name each taxonomy fills in.
AMENITY_TAXONOMIES: dict[str, Taxonomy] = {
    "air_conditioning": AIR_CONDITIONING,
    "has_washing_machine": WASHING_MACHINE,
    "has_dryer": DRYER,
    "has_internet": INTERNET,
    "has_dishwasher": DISHWASHER,
    "mansard": MANSARD,
}


def classify_amenities(description: str) -> dict[str, str]:
    """Classify ``description`` against every known amenity taxonomy.

    Returns a dict keyed like :data:`AMENITY_TAXONOMIES`, each value ``"True"``,
    ``"False"``, or ``""`` (unknown), matching :func:`src.pets.classify_pets_friendly`.
    """
    return {field: classify(description, taxonomy) for field, taxonomy in AMENITY_TAXONOMIES.items()}
