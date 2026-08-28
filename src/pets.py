"""``pets_friendly`` taxonomy: pet-policy phrases for the shared classifier in
``taxonomy.py``.

Listing descriptions on Bezrealitky are written in Czech (with occasional English),
so the taxonomy leads with Czech phrases and stems, English second. A bare mention
of an animal says nothing about whether they're allowed, so — unlike the simpler
amenity taxonomies in ``amenities.py`` — pets also needs the stem-proximity
fallback: a subject stem ("zvir", "mazlic", ...) and a permission/suitability
polarity stem ("vitan", "povolen", ...) occurring near each other, independent of
what sits between them (Czech word order is flexible enough to separate them,
e.g. "mazlíčci jsou po dohodě vítáni" — "pets are, by agreement, welcome").
"""

from __future__ import annotations

try:
    from .taxonomy import Taxonomy, classify
except ImportError:  # Support: python3 src/pets.py
    from taxonomy import Taxonomy, classify  # type: ignore[no-redef]

# Checked first: an explicit denial ("no pets") must win even though the text
# also contains a word ("pets") that would otherwise look positive.
NEGATIVE_PHRASES = [
    "bez zvířat",
    "bez domácích mazlíčků",
    "zvířata nejsou povolena",
    "zvířata zakázána",
    "chov zvířat není povolen",
    "chov zvířat je zakázán",
    "chov zvířat zakázán",
    "mazlíčci nejsou povoleni",
    "mazlíčci nejsou vítáni",
    "psi nejsou povoleni",
    "kočky nejsou povoleny",
    "domácí mazlíčci nejsou povoleni",
    "no pets",
    "pets not allowed",
    "pets are not allowed",
    "pet free",
    "no animals",
    "no animals allowed",
    "animals not allowed",
    "animals are not allowed",
]

POSITIVE_PHRASES = [
    "se zvířetem",
    "se zvířaty",
    "domácí mazlíčci vítáni",
    "mazlíčci jsou vítáni",
    "mazlíčci vítáni",
    "zvíře povoleno",
    "zvířata povolena",
    "chov zvířat povolen",
    "chov zvířat je povolen",
    "psi povoleni",
    "kočky povoleny",
    "vhodné pro chov zvířat",
    "vhodný pro domácí mazlíčky",
    "vhodný pro mazlíčky",
    "pet friendly",
    "pets allowed",
    "pets welcome",
    "small pets allowed",
    "animals allowed",
    "animals welcome",
]

_SUBJECT_STEMS = ("zvir", "mazlic", "kock", "pes", "ps", "pet", "animal")
_POSITIVE_POLARITY_STEMS = ("vitan", "povolen", "vhodn", "friendly", "allowed", "welcome")
_NEGATIVE_POLARITY_STEMS = ("zakaz",)

PETS_TAXONOMY = Taxonomy(
    positive_phrases=POSITIVE_PHRASES,
    negative_phrases=NEGATIVE_PHRASES,
    subject_stems=_SUBJECT_STEMS,
    positive_polarity_stems=_POSITIVE_POLARITY_STEMS,
    negative_polarity_stems=_NEGATIVE_POLARITY_STEMS,
)


def classify_pets_friendly(description: str) -> str:
    """Classify a listing description as pets-friendly.

    Returns ``"True"``, ``"False"``, or ``""`` when the description gives no signal
    either way (an unknown outcome, never guessed).
    """
    return classify(description, PETS_TAXONOMY)
