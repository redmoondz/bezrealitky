"""Normalize the raw ``Fully furnished`` table cell into a boolean signal.

Unlike ``pets_friendly`` (classified from free-text descriptions), this is
already a direct site property — a short, closed-vocabulary value like "Yes",
"No", or "Partly" (see ``tests/test_scraper.py``) — so an exact lookup is
enough, no fuzzy/negation handling needed.
"""

from __future__ import annotations

_YES = {"yes", "fully", "fully furnished", "furnished"}
_NO = {"no", "unfurnished", "not furnished"}


def _normalize(raw: str) -> str:
    return " ".join((raw or "").split()).casefold()


def parse_furnished(raw: str) -> str:
    """Parse a ``fully furnished`` table cell into ``"True"``/``"False"``/``""``.

    Returns ``""`` for "Partly" and anything else unrecognized — genuinely
    ambiguous with respect to a plain furnished/unfurnished preference, never
    guessed either way, same three-state contract as
    :func:`src.pets.classify_pets_friendly`.
    """
    text = _normalize(raw)
    if text in _YES:
        return "True"
    if text in _NO:
        return "False"
    return ""
