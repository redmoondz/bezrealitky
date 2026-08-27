"""Matplotlib chart builders for /charts, returning PNG bytes.

Telegram delivers a chart as a single static photo (no hover/tooltip, no live
theme), so this sticks to one light look rather than the light/dark pair a
live page would ship — everything else (form choice, the validated categorical
palette, single-axis-only, sparse labels) follows the project's dataviz method.
Colors are the skill's validated default palette (see `references/palette.md`):
slots 1-3 (blue/orange/aqua) are the only three cleared for "all pairs visible
at once" (pies, scatters); a 4th+ category folds into a neutral "Other" instead
of a 4th hue.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

SERIES_1 = "#2a78d6"  # blue
SERIES_2 = "#eb6834"  # orange
SERIES_3 = "#1baf7a"  # aqua
NEUTRAL_OTHER = "#898781"

PETS_LABELS = {True: "Yes", False: "No", None: "Unknown"}


def _new_axes():
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.title.set_color(INK_PRIMARY)
    ax.xaxis.label.set_color(INK_SECONDARY)
    ax.yaxis.label.set_color(INK_SECONDARY)
    return fig, ax


def _finish(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


def _numeric_values(rows: list[dict], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def _histogram(rows: list[dict], key: str, title: str, xlabel: str) -> bytes:
    values = _numeric_values(rows, key)
    fig, ax = _new_axes()
    if values:
        ax.hist(values, bins=min(20, max(5, len(values) // 3)), color=SERIES_1, rwidth=0.9)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Listings")
    if not values:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center", color=INK_MUTED, transform=ax.transAxes)
    return _finish(fig)


def area_distribution(rows: list[dict]) -> bytes:
    return _histogram(rows, "area", "Area distribution", "Area (m²)")


def price_distribution(rows: list[dict]) -> bytes:
    return _histogram(rows, "total_price", "Price distribution", "Total price")


def price_per_unit_distribution(rows: list[dict]) -> bytes:
    values = [
        float(row["total_price"]) / float(row["area"])
        for row in rows
        if row.get("total_price") is not None and row.get("area")
    ]
    fig, ax = _new_axes()
    if values:
        ax.hist(values, bins=min(20, max(5, len(values) // 3)), color=SERIES_1, rwidth=0.9)
    ax.set_title("Price per m² distribution")
    ax.set_xlabel("Price / m²")
    ax.set_ylabel("Listings")
    if not values:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center", color=INK_MUTED, transform=ax.transAxes)
    return _finish(fig)


def price_vs_area(rows: list[dict]) -> bytes:
    pairs = [
        (float(row["area"]), float(row["total_price"]))
        for row in rows
        if row.get("area") is not None and row.get("total_price") is not None
    ]
    fig, ax = _new_axes()
    if pairs:
        areas, prices = zip(*pairs)
        ax.scatter(areas, prices, s=28, color=SERIES_1, alpha=0.85, edgecolors=SURFACE, linewidths=0.5, label="Listings")
        if len(pairs) >= 2:
            slope, intercept = np.polyfit(areas, prices, 1)
            x_line = np.linspace(min(areas), max(areas), 100)
            ax.plot(x_line, slope * x_line + intercept, color=INK_SECONDARY, linestyle="--", linewidth=2, label="Trend")
        ax.legend(frameon=False, labelcolor=INK_SECONDARY)
    else:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center", color=INK_MUTED, transform=ax.transAxes)
    ax.set_title("Price vs. area")
    ax.set_xlabel("Area (m²)")
    ax.set_ylabel("Total price")
    return _finish(fig)


def _pie(counts: list[tuple[str, int]], title: str) -> bytes:
    fig, ax = plt.subplots(figsize=(6, 6), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    if counts:
        labels = [label for label, _ in counts]
        values = [value for _, value in counts]
        colors = ([SERIES_1, SERIES_2, SERIES_3] + [NEUTRAL_OTHER] * len(counts))[: len(counts)]
        wedges, _texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct="%1.0f%%",
            pctdistance=0.75,
            textprops={"color": INK_SECONDARY, "fontsize": 9},
        )
        for autotext in autotexts:
            autotext.set_color(INK_PRIMARY)
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, labelcolor=INK_SECONDARY)
    else:
        ax.text(0.5, 0.5, "No data yet", ha="center", va="center", color=INK_MUTED, transform=ax.transAxes)
    ax.set_title(title, color=INK_PRIMARY)
    return _finish(fig)


def format_breakdown(rows: list[dict]) -> bytes:
    counts: dict[str, int] = {}
    for row in rows:
        key = (row.get("format") or "Unknown").strip() or "Unknown"
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    top, rest = ordered[:3], ordered[3:]
    if rest:
        top.append(("Other", sum(count for _, count in rest)))
    return _pie(top, "Listings by layout")


def pets_friendly_breakdown(rows: list[dict]) -> bytes:
    counts: dict[str, int] = {}
    for row in rows:
        label = PETS_LABELS[row.get("pets_friendly")]
        counts[label] = counts.get(label, 0) + 1
    ordered = [
        (label, counts[label])
        for label in ("Yes", "No", "Unknown")
        if label in counts
    ]
    return _pie(ordered, "Listings by pets_friendly")


CHART_BUILDERS = {
    "area_hist": area_distribution,
    "price_hist": price_distribution,
    "price_per_unit_hist": price_per_unit_distribution,
    "price_vs_area": price_vs_area,
    "format_pie": format_breakdown,
    "pets_pie": pets_friendly_breakdown,
}
