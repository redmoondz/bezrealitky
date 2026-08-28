"""JSON data-shaping for the Mini App's interactive charts — one function per
``bot/charts.py::CHART_BUILDERS`` key, built on the same shared bin/group
helpers in ``bot/chart_stats.py`` so the chat bot's PNGs and the app's
interactive charts never drift on what counts as "Unknown" or "Other".

Unlike the bot (Telegram delivers a chart as one static photo), the Mini App
is a live, resizable, theme-aware page — so this returns raw series for the
frontend to render with an interactive charting library, not pre-rendered
images.
"""

from __future__ import annotations

from bot.chart_stats import (
    format_counts,
    numeric_values,
    pets_counts,
    price_area_points,
    price_per_unit_values,
)

CHART_LABELS = {
    "area_hist": "Area distribution",
    "price_hist": "Price distribution",
    "price_per_unit_hist": "Price per m² distribution",
    "price_vs_area": "Price vs. area",
    "format_pie": "By layout",
    "pets_pie": "By pets_friendly",
}

CHART_KINDS = {
    "area_hist": "histogram",
    "price_hist": "histogram",
    "price_per_unit_hist": "histogram",
    "price_vs_area": "scatter",
    "format_pie": "pie",
    "pets_pie": "pie",
}


def area_histogram(rows: list[dict]) -> dict:
    return {"values": numeric_values(rows, "area")}


def price_histogram(rows: list[dict]) -> dict:
    return {"values": numeric_values(rows, "total_price")}


def price_per_unit_histogram(rows: list[dict]) -> dict:
    return {"values": price_per_unit_values(rows)}


def price_vs_area(rows: list[dict]) -> dict:
    return {"points": price_area_points(rows)}


def format_breakdown(rows: list[dict]) -> dict:
    return {"counts": [{"label": label, "value": value} for label, value in format_counts(rows)]}


def pets_breakdown(rows: list[dict]) -> dict:
    return {"counts": [{"label": label, "value": value} for label, value in pets_counts(rows)]}


CHART_DATA_BUILDERS = {
    "area_hist": area_histogram,
    "price_hist": price_histogram,
    "price_per_unit_hist": price_per_unit_histogram,
    "price_vs_area": price_vs_area,
    "format_pie": format_breakdown,
    "pets_pie": pets_breakdown,
}
