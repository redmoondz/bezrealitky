"""Deterministic, hand-weighted scoring of one listing against one user's
onboarding preferences.

This is explicitly *not* a trained model — at this project's scale (a single
operator, no training data) a small set of explainable point rules is the
honest design. Every rule contributes 0 whenever its preference (or the
listing's own data) is missing, so a user who skipped every onboarding
question always scores every listing 0 — identical to browsing before scoring
existed. Weights below are a first cut, expected to be retuned after seeing
real results.
"""

from __future__ import annotations

from decimal import Decimal

_PETS_MATCH_BONUS = 30
_PETS_MISMATCH_PENALTY = -50

_BUDGET_WITHIN_BONUS = 15
# Above this ratio of total_price to budget, a listing is no longer "gold for a
# bit more" — it's simply over budget.
_BUDGET_OVERAGE_CEILING = Decimal("1.15")
_BUDGET_OVER_CEILING_PENALTY = -1000

_AREA_MATCH_BONUS = 10
_AREA_MISMATCH_PENALTY = -10

# A listing at or above this total score gets the "Top match" badge in Telegram.
TOP_MATCH_THRESHOLD = 25


def _pets_score(listing: dict, preferences: dict) -> int:
    if preferences.get("wants_pets") is not True:
        return 0
    pets_friendly = listing.get("pets_friendly")
    if pets_friendly is True:
        return _PETS_MATCH_BONUS
    if pets_friendly is False:
        return _PETS_MISMATCH_PENALTY
    return 0


def _budget_score(listing: dict, preferences: dict) -> int:
    budget = preferences.get("budget_total_price")
    total_price = listing.get("total_price")
    if not budget or total_price is None:
        return 0
    ratio = total_price / budget
    if ratio <= 1:
        return _BUDGET_WITHIN_BONUS
    if ratio <= _BUDGET_OVERAGE_CEILING:
        taper = (_BUDGET_OVERAGE_CEILING - ratio) / (_BUDGET_OVERAGE_CEILING - 1)
        return round(_BUDGET_WITHIN_BONUS * taper)
    return _BUDGET_OVER_CEILING_PENALTY


def _area_score(listing: dict, preferences: dict) -> int:
    min_area = preferences.get("min_area_m2")
    area = listing.get("area")
    if min_area is None or area is None:
        return 0
    return _AREA_MATCH_BONUS if area >= min_area else _AREA_MISMATCH_PENALTY


def compute_score(listing: dict, preferences: dict) -> int:
    """Sum of every rule's contribution — see module docstring for the rules.

    ``listing`` is a ``listings`` row dict (as produced by
    :func:`src.db.row_from_listing`: ``total_price``/``area`` are ``Decimal``
    or ``None``, ``pets_friendly`` is ``bool`` or ``None``). ``preferences`` is
    a :func:`src.db.get_user_preferences` result.
    """
    return (
        _pets_score(listing, preferences)
        + _budget_score(listing, preferences)
        + _area_score(listing, preferences)
    )
