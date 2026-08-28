"""Build Telegram-ready captions/messages from a ``listings`` row."""

from __future__ import annotations

from html import escape

from src.scoring import TOP_MATCH_THRESHOLD

from . import i18n

_PETS_LABELS = {True: "Yes", False: "No", None: "Unknown"}


def _tags_line(language: str, row: dict) -> str:
    tags = i18n.amenity_tags(language, row)
    # A leading blank line so the tags don't visually run into the row above —
    # only emitted when there are tags, so the no-tags case adds no stray gap.
    return f"\n🏷 {'   '.join(tags)}\n" if tags else ""


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


def _deposit_text(row: dict) -> str:
    deposit = row.get("refundable_deposit")
    if deposit is None:
        return "—"
    currency = row.get("currency") or ""
    return f"{deposit} {currency}".strip()


def summary_caption(row: dict, offset: int, total: int, language: str = "en") -> str:
    """Short caption for a single card in the /list pager (Telegram photo captions
    are capped at 1024 characters, so the full description lives in /view only).
    """
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    return (
        f"{_top_match_badge(row)}"
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 Rent: {_price_text(row)}   💵 Deposit: {_deposit_text(row)}\n"
        f"📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"{_tags_line(language, row)}"
        f"\n{offset + 1}/{total}"
    )


_MESSAGE_LIMIT = 4096


def detail_text(row: dict, description: str, language: str = "en", translation_ok: bool = True) -> str:
    """Full detail text for /view and new-match notifications — the whole card
    (details + description) as one message, description collapsed into an
    expandable quote (Telegram message text is capped at 4096 chars).
    """
    area = f"{row['area']} m²" if row.get("area") is not None else "—"
    pets = _PETS_LABELS.get(row.get("pets_friendly"))
    header = (
        f"{_top_match_badge(row)}"
        f"<b>{escape(row.get('name') or 'Untitled listing')}</b>\n"
        f"💰 Rent: {_price_text(row)}   💵 Deposit: {_deposit_text(row)}\n"
        f"📐 {area}   🛏 {escape(row.get('format') or '—')}\n"
        f"🪜 Floor {_floor_text(row)}   🐾 Pets: {pets}\n"
        f"📍 {escape(row.get('location') or '—')}\n"
        f"{_tags_line(language, row)}"
        f"🔗 <a href=\"{escape(row.get('url') or '')}\">Open on Bezrealitky</a>\n"
    )
    if not description:
        return header[:_MESSAGE_LIMIT]

    note = f"{i18n.translation_failed_note(language)}\n" if not translation_ok else ""
    prefix = f"\n{note}<blockquote expandable>"
    suffix = "</blockquote>"
    # Truncate the description itself (never the surrounding text), so a long
    # description can never leave a truncated, unclosed <blockquote> tag behind
    # — that would make Telegram reject the whole message instead of just
    # cutting the quote short.
    budget = _MESSAGE_LIMIT - len(header) - len(prefix) - len(suffix)
    escaped_description = escape(description)
    if budget <= 0:
        return header[:_MESSAGE_LIMIT]
    return header + prefix + escaped_description[:budget] + suffix
