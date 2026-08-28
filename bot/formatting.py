"""Build Telegram-ready captions/messages from a ``listings`` row."""

from __future__ import annotations

from html import escape

from src.scoring import TOP_MATCH_THRESHOLD

from . import i18n

_PETS_LABELS = {True: "Yes", False: "No", None: "Unknown"}


def _tags_line(language: str, row: dict) -> str:
    tags = i18n.amenity_tags(language, row)
    return f"🏷 {'   '.join(tags)}\n" if tags else ""


def _top_match_badge(row: dict) -> str:
    """A visible badge, not the raw point total — the score itself is an
    internal ranking detail, not something to show a user as "42 points".
    """
    score = row.get("score") or 0
    return "⭐ <b>Top match</b>\n" if score >= TOP_MATCH_THRESHOLD else ""


def _floor_text(row: dict) -> str:
    if row.get("floor_number") is not None:
        total = row.get("floor_total")
        return f"{row['floor_number']}/{total}" if total is not None else str(row["floor_number"])
    return row.get("floor") or "—"


def _price_text(row: dict) -> str:
    if row.get("total_price") is None:
        return "—"
    currency = row.get("currency") or ""
    return f"{row['total_price']} {currency}".strip()


def summary_caption(row: dict, offset: int, total: int, language: str = "en") -> str:
    """Short caption for a single card in the /list pager (Telegram photo captions
    are capped at 1024 characters, so the full description lives in /view only).
    """
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    return (
        f"{_top_match_badge(row)}"
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 {_price_text(row)}   📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"{_tags_line(language, row)}"
        f"\n{offset + 1}/{total}"
    )


def detail_text(row: dict, description: str, language: str = "en") -> str:
    """Full detail text for /view (Telegram message text is capped at 4096 chars)."""
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    body = (
        f"{_top_match_badge(row)}"
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 {_price_text(row)}   📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"{_tags_line(language, row)}"
        f"🔗 <a href=\"{escape(row.get('url') or '')}\">Open on Bezrealitky</a>\n"
    )
    if description:
        body += f"\n{escape(description)}"
    return body[:4096]
