"""Build Telegram-ready captions/messages from a ``listings`` row."""

from __future__ import annotations

from html import escape

_PETS_LABELS = {True: "Yes", False: "No", None: "Unknown"}


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


def summary_caption(row: dict, offset: int, total: int) -> str:
    """Short caption for a single card in the /list pager (Telegram photo captions
    are capped at 1024 characters, so the full description lives in /view only).
    """
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    return (
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 {_price_text(row)}   📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"\n{offset + 1}/{total}"
    )


def detail_text(row: dict, description: str) -> str:
    """Full detail text for /view (Telegram message text is capped at 4096 chars)."""
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    body = (
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 {_price_text(row)}   📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"🔗 <a href=\"{escape(row.get('url') or '')}\">Open on Bezrealitky</a>\n"
    )
    if description:
        body += f"\n{escape(description)}"
    return body[:4096]
