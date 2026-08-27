"""Split the free-text ``floor`` table cell into floor number and building height."""

from __future__ import annotations

import re

_WORD_TO_FLOOR = {
    "ground": "0",
}

# "2. floor out of 2" / "Ground floor out of 5"
_WITH_TOTAL_RE = re.compile(
    r"^(?:(?P<number>\d+)\.|(?P<word>ground))\s*floor\s+out of\s+(?P<total>\d+)$"
)
# "3. floor" / "Ground floor" (no building height given)
_WITHOUT_TOTAL_RE = re.compile(
    r"^(?:(?P<number>\d+)\.|(?P<word>ground))\s*floor$"
)


def _normalize(raw: str) -> str:
    return " ".join((raw or "").split()).casefold()


def _floor_number(match: re.Match) -> str:
    word = match.group("word")
    if word is not None:
        return _WORD_TO_FLOOR[word]
    return match.group("number")


def parse_floor(raw: str) -> tuple[str, str]:
    """Parse a ``floor`` table cell into ``(floor_number, floor_total)``.

    Returns ``("", "")`` when the text doesn't match a recognized shape; the raw
    text is preserved separately in the ``floor`` column regardless.
    """
    text = _normalize(raw)
    if not text:
        return "", ""

    match = _WITH_TOTAL_RE.match(text)
    if match:
        return _floor_number(match), match.group("total")

    match = _WITHOUT_TOTAL_RE.match(text)
    if match:
        return _floor_number(match), ""

    return "", ""
