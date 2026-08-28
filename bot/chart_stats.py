"""Pure data-shaping helpers shared by ``bot/charts.py`` (matplotlib PNGs, for
the chat bot) and ``webapp/backend/chart_data.py`` (JSON, for the Mini App's
interactive charts) — kept dependency-free (no matplotlib) so importing it
never pulls a rendering library into the webapp process.
"""

from __future__ import annotations

PETS_LABELS = {True: "Yes", False: "No", None: "Unknown"}


def numeric_values(rows: list[dict], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def price_per_unit_values(rows: list[dict]) -> list[float]:
    return [
        float(row["total_price"]) / float(row["area"])
        for row in rows
        if row.get("total_price") is not None and row.get("area")
    ]


def price_area_pairs(rows: list[dict]) -> list[tuple[float, float]]:
    return [
        (float(row["area"]), float(row["total_price"]))
        for row in rows
        if row.get("area") is not None and row.get("total_price") is not None
    ]


def price_area_points(rows: list[dict]) -> list[dict]:
    """Same pairing as :func:`price_area_pairs`, plus each listing's own URL —
    only the Mini App's interactive scatter chart needs this (a point there is
    clickable), the bot's static PNG plots stay on the plain tuple form.
    """
    return [
        {"area": float(row["area"]), "price": float(row["total_price"]), "url": row.get("url") or ""}
        for row in rows
        if row.get("area") is not None and row.get("total_price") is not None
    ]


def format_counts(rows: list[dict]) -> list[tuple[str, int]]:
    """Top-3 layouts by frequency, everything else folded into "Other" — keeps
    a pie chart's legend readable no matter how many distinct layouts exist.
    """
    counts: dict[str, int] = {}
    for row in rows:
        key = (row.get("format") or "Unknown").strip() or "Unknown"
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    top, rest = ordered[:3], ordered[3:]
    if rest:
        top.append(("Other", sum(count for _, count in rest)))
    return top


def pets_counts(rows: list[dict]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        label = PETS_LABELS[row.get("pets_friendly")]
        counts[label] = counts.get(label, 0) + 1
    return [(label, counts[label]) for label in ("Yes", "No", "Unknown") if label in counts]
