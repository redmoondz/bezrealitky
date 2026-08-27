"""Primitive keyword taxonomy for classifying ``pets_friendly`` from free text.

Listing descriptions on Bezrealitky are written in Czech (with occasional English),
so the taxonomy leads with Czech phrases and stems, English second. Matching is
diacritics- and case-insensitive so both ``zvíře`` and a mistyped ``zvire`` line up.
Text and phrases are both tokenized into plain word lists (punctuation and emoji
stripped) and compared word-for-word, so a phrase match doesn't depend on exact
punctuation, and a negation word ("není", "nejsou", "bez", ...) immediately before
an otherwise-positive phrase flips the result — e.g. "není vhodný pro domácí
mazlíčky" ("not suitable for pets") must classify as ``False``, not ``True``.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

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

# A negation immediately before an otherwise-positive phrase flips it to negative
# ("není vhodný pro domácí mazlíčky" = "not suitable for pets"). The enumerated
# negative phrases above already spell out their own negation, so this window is
# only applied to positive-phrase matches.
NEGATION_CUES = {"ne", "nejsou", "neni", "zadny", "zadna", "zadne", "no", "not", "without"}
NEGATION_WINDOW = 3

_FUZZY_CUTOFF = 0.8
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Last-resort fallback: Czech word order is flexible enough that a real subject and
# polarity word can end up several words apart ("mazlíčci jsou po dohodě vítáni" —
# "pets are, by agreement, welcome"), too far apart for the phrase tiers above to
# catch as one contiguous (possibly-typo'd) sequence. This tier instead just asks
# whether a pets/animals *subject* stem and a permission/suitability *polarity* stem
# occur near each other, independent of what sits between them, then applies the
# same negation-window check to the polarity word.
_SUBJECT_STEMS = ("zvir", "mazlic", "kock", "pes", "ps", "pet", "animal")
_POSITIVE_POLARITY_STEMS = ("vitan", "povolen", "vhodn", "friendly", "allowed", "welcome")
_NEGATIVE_POLARITY_STEMS = ("zakaz",)
_STEM_PROXIMITY_WINDOW = 6


def _stem_matches(words: list[str], stems: tuple[str, ...]) -> list[int]:
    return [index for index, word in enumerate(words) if word.startswith(stems)]


def _normalize(text: str) -> str:
    """Casefold, strip diacritics/punctuation, and collapse to single-space tokens."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(_TOKEN_RE.findall(without_marks.casefold()))


def _phrase_words(phrases: list[str]) -> list[list[str]]:
    return [_normalize(phrase).split() for phrase in phrases]


NEGATIVE_PHRASE_WORDS = _phrase_words(NEGATIVE_PHRASES)
POSITIVE_PHRASE_WORDS = _phrase_words(POSITIVE_PHRASES)


def _find_exact_matches(words: list[str], phrase: list[str]) -> list[int]:
    length = len(phrase)
    if length == 0 or length > len(words):
        return []
    return [start for start in range(len(words) - length + 1) if words[start : start + length] == phrase]


def _find_fuzzy_matches(words: list[str], phrase: list[str]) -> list[int]:
    """Word-position-aligned fuzzy match: every word in the window must be close
    to the corresponding phrase word. This tolerates a typo in one word without
    letting two windows match just because they share some words in common
    (comparing the whole joined phrase as one string lets unrelated windows score
    high on character overlap alone).
    """
    length = len(phrase)
    if length == 0 or length > len(words):
        return []
    matches = []
    for start in range(len(words) - length + 1):
        window = words[start : start + length]
        if all(
            difflib.SequenceMatcher(None, expected, actual).ratio() >= _FUZZY_CUTOFF
            for expected, actual in zip(phrase, window)
        ):
            matches.append(start)
    return matches


def _is_negated(words: list[str], match_index: int) -> bool:
    start = max(0, match_index - NEGATION_WINDOW)
    return any(word in NEGATION_CUES for word in words[start:match_index])


def classify_pets_friendly(description: str) -> str:
    """Classify a listing description as pets-friendly.

    Returns ``"True"``, ``"False"``, or ``""`` when the description gives no signal
    either way (an unknown outcome, never guessed).
    """
    words = _normalize(description).split()
    if not words:
        return ""

    for phrase in NEGATIVE_PHRASE_WORDS:
        if _find_exact_matches(words, phrase):
            return "False"

    positive_matches = [
        index for phrase in POSITIVE_PHRASE_WORDS for index in _find_exact_matches(words, phrase)
    ]
    if positive_matches:
        return "False" if all(_is_negated(words, index) for index in positive_matches) else "True"

    for phrase in NEGATIVE_PHRASE_WORDS:
        if _find_fuzzy_matches(words, phrase):
            return "False"

    fuzzy_positive_matches = [
        index for phrase in POSITIVE_PHRASE_WORDS for index in _find_fuzzy_matches(words, phrase)
    ]
    if fuzzy_positive_matches:
        return (
            "False"
            if all(_is_negated(words, index) for index in fuzzy_positive_matches)
            else "True"
        )

    subject_indices = _stem_matches(words, _SUBJECT_STEMS)
    if not subject_indices:
        return ""

    verdicts = []
    for subject_index in subject_indices:
        for polarity_index in _stem_matches(words, _POSITIVE_POLARITY_STEMS):
            if abs(subject_index - polarity_index) <= _STEM_PROXIMITY_WINDOW:
                verdicts.append(not _is_negated(words, polarity_index))
        for polarity_index in _stem_matches(words, _NEGATIVE_POLARITY_STEMS):
            if abs(subject_index - polarity_index) <= _STEM_PROXIMITY_WINDOW:
                verdicts.append(_is_negated(words, polarity_index))

    if not verdicts:
        return ""
    return "True" if any(verdicts) else "False"
