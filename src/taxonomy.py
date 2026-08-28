"""Generic phrase-based tri-state text classifier, extracted from the original
``pets.py`` pet-friendliness detector so the same matching machinery (exact and
fuzzy phrase matching, a negation window, and a stem-proximity fallback for
phrases whose parts can be far apart) can drive more than one taxonomy — pets,
air conditioning, a washing machine, and so on.

Matching is diacritics- and case-insensitive, so both accented and unaccented
(or mistyped) forms line up. Text and phrases are both tokenized into plain word
lists (punctuation and emoji stripped) and compared word-for-word, so a phrase
match doesn't depend on exact punctuation, and a negation word ("není",
"nejsou", "bez", ...) immediately before an otherwise-positive phrase flips the
result.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Iterable

NEGATION_CUES = {"ne", "nejsou", "neni", "zadny", "zadna", "zadne", "no", "not", "without"}
NEGATION_WINDOW = 3

_FUZZY_CUTOFF = 0.8
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Last-resort fallback for taxonomies whose subject and polarity words can end
# up several words apart (flexible word order): matches whenever a subject stem
# and a polarity stem occur within this many words of each other, independent of
# what sits between them, still subject to the same negation-window check.
_STEM_PROXIMITY_WINDOW = 6


def _normalize(text: str) -> str:
    """Casefold, strip diacritics/punctuation, and collapse to single-space tokens."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(_TOKEN_RE.findall(without_marks.casefold()))


def _phrase_words(phrases: Iterable[str]) -> list[list[str]]:
    return [_normalize(phrase).split() for phrase in phrases]


def _stem_matches(words: list[str], stems: tuple[str, ...]) -> list[int]:
    if not stems:
        return []
    return [index for index, word in enumerate(words) if word.startswith(stems)]


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


class Taxonomy:
    """A phrase-based classifier definition: positive/negative phrase lists, plus
    an optional subject/polarity stem-proximity fallback (leave the stem tuples
    empty to skip that tier entirely — appropriate whenever a bare mention of the
    thing, e.g. "klimatizace", already is the positive signal, unlike pets where
    a bare "zvíře" says nothing about whether they're allowed).
    """

    def __init__(
        self,
        *,
        positive_phrases: Iterable[str],
        negative_phrases: Iterable[str],
        subject_stems: tuple[str, ...] = (),
        positive_polarity_stems: tuple[str, ...] = (),
        negative_polarity_stems: tuple[str, ...] = (),
    ) -> None:
        self.positive_phrase_words = _phrase_words(positive_phrases)
        self.negative_phrase_words = _phrase_words(negative_phrases)
        self.subject_stems = subject_stems
        self.positive_polarity_stems = positive_polarity_stems
        self.negative_polarity_stems = negative_polarity_stems


def classify(description: str, taxonomy: Taxonomy) -> str:
    """Classify ``description`` against ``taxonomy``.

    Returns ``"True"``, ``"False"``, or ``""`` when the description gives no signal
    either way (an unknown outcome, never guessed).
    """
    words = _normalize(description).split()
    if not words:
        return ""

    for phrase in taxonomy.negative_phrase_words:
        if _find_exact_matches(words, phrase):
            return "False"

    positive_matches = [
        index for phrase in taxonomy.positive_phrase_words for index in _find_exact_matches(words, phrase)
    ]
    if positive_matches:
        return "False" if all(_is_negated(words, index) for index in positive_matches) else "True"

    for phrase in taxonomy.negative_phrase_words:
        if _find_fuzzy_matches(words, phrase):
            return "False"

    fuzzy_positive_matches = [
        index for phrase in taxonomy.positive_phrase_words for index in _find_fuzzy_matches(words, phrase)
    ]
    if fuzzy_positive_matches:
        return (
            "False"
            if all(_is_negated(words, index) for index in fuzzy_positive_matches)
            else "True"
        )

    subject_indices = _stem_matches(words, taxonomy.subject_stems)
    if not subject_indices:
        return ""

    verdicts = []
    for subject_index in subject_indices:
        for polarity_index in _stem_matches(words, taxonomy.positive_polarity_stems):
            if abs(subject_index - polarity_index) <= _STEM_PROXIMITY_WINDOW:
                verdicts.append(not _is_negated(words, polarity_index))
        for polarity_index in _stem_matches(words, taxonomy.negative_polarity_stems):
            if abs(subject_index - polarity_index) <= _STEM_PROXIMITY_WINDOW:
                verdicts.append(_is_negated(words, polarity_index))

    if not verdicts:
        return ""
    return "True" if any(verdicts) else "False"
