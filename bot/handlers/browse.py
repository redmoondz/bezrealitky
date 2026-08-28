"""``/list`` (paginated browsing) and ``/view <listing_id>`` (full detail).

Every query is scoped to the calling Telegram user's own saved search — there is
no shared "the current saved search," each user has their own.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from src import db

from .. import formatting
from ..access import IsAllowed, denial_text
from ..keyboards import PAGE_SIZE, listing_keyboard
from ..translate import translate_description

router = Router(name="browse")


def _load_page(telegram_user_id: int, offset: int) -> tuple[int, dict | None, str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        total = db.count_relevant_listings(conn, telegram_user_id)
        rows = db.fetch_relevant_listings_page(conn, telegram_user_id, offset, PAGE_SIZE)
        language = db.get_user_language(conn, telegram_user_id)
        return total, (rows[0] if rows else None), language


def _load_detail(listing_id: str, telegram_user_id: int) -> tuple[dict | None, str, str, bool]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        row = db.fetch_listing(conn, listing_id)
        if row is None:
            return None, "", "", True
        language = db.get_user_language(conn, telegram_user_id)
        row["score"] = db.get_relevance_score(conn, telegram_user_id, listing_id)
    description = row.get("description") or ""
    if description:
        translated, translation_ok = translate_description(description, language)
    else:
        translated, translation_ok = "", True
    return row, translated, language, translation_ok


async def _send_page(message: Message, telegram_user_id: int, offset: int) -> None:
    total, row, language = await asyncio.to_thread(_load_page, telegram_user_id, offset)
    if row is None:
        await message.answer(
            "No listings match your saved search yet. Try /parse to scrape now, "
            "or /search to see what's saved."
        )
        return
    caption = formatting.summary_caption(row, offset, total, language)
    keyboard = listing_keyboard(row["listing_id"], row["url"], offset, total)
    images = row.get("images") or []
    if images:
        await message.answer_photo(images[0], caption=caption, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=keyboard)


async def _edit_page(query: CallbackQuery, telegram_user_id: int, offset: int) -> None:
    total, row, language = await asyncio.to_thread(_load_page, telegram_user_id, offset)
    if row is None or not query.message:
        await query.answer("No more listings.", show_alert=True)
        return
    caption = formatting.summary_caption(row, offset, total, language)
    keyboard = listing_keyboard(row["listing_id"], row["url"], offset, total)
    images = row.get("images") or []
    if images:
        await query.message.edit_media(
            InputMediaPhoto(media=images[0], caption=caption, parse_mode="HTML"),
            reply_markup=keyboard,
        )
    else:
        await query.message.edit_text(caption, parse_mode="HTML", reply_markup=keyboard)
    await query.answer()


async def _send_detail(target: Message, listing_id: str, telegram_user_id: int) -> None:
    row, translated, language, translation_ok = await asyncio.to_thread(
        _load_detail, listing_id, telegram_user_id
    )
    if row is None:
        await target.answer(f"No listing found with ID {listing_id}.")
        return
    images = row.get("images") or []
    if len(images) > 1:
        await target.answer_media_group([InputMediaPhoto(media=url) for url in images[:10]])
    elif images:
        await target.answer_photo(images[0])
    await target.answer(
        formatting.detail_text(row, translated, language, translation_ok), parse_mode="HTML"
    )
    latitude, longitude = row.get("latitude"), row.get("longitude")
    if latitude is not None and longitude is not None:
        # A native Telegram map bubble (with an "Open in Maps" button) — no
        # static-map image to generate, no maps API key, no dependence on
        # whether a plain Google Maps link happens to get a link preview.
        await target.answer_location(float(latitude), float(longitude))


# Each command is registered twice: the allowed-only handler first, a plain
# fallback second. Aiogram tries handlers for an update in registration order
# and stops at the first whose filters all pass, so an unauthorized user falls
# through to the fallback and gets a clear denial instead of silence.


@router.message(Command("list"), IsAllowed())
async def list_listings(message: Message) -> None:
    await _send_page(message, message.from_user.id, 0)


@router.message(Command("list"))
async def list_listings_denied(message: Message) -> None:
    await message.answer(denial_text())


@router.message(Command("view"), IsAllowed())
async def view_listing(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /view <listing_id> — the ID shown on a listing card.")
        return
    await _send_detail(message, parts[1].strip(), message.from_user.id)


@router.message(Command("view"))
async def view_listing_denied(message: Message) -> None:
    await message.answer(denial_text())


@router.callback_query(F.data.startswith("page:"), IsAllowed())
async def on_page(query: CallbackQuery) -> None:
    offset = int(query.data.split(":", 1)[1])
    await _edit_page(query, query.from_user.id, offset)


@router.callback_query(F.data.startswith("view:"), IsAllowed())
async def on_view(query: CallbackQuery) -> None:
    listing_id = query.data.split(":", 1)[1]
    if query.message:
        await _send_detail(query.message, listing_id, query.from_user.id)
    await query.answer()


@router.callback_query(F.data == "menu:browse", IsAllowed())
async def on_menu_browse(query: CallbackQuery) -> None:
    if query.message:
        await _send_page(query.message, query.from_user.id, 0)
    await query.answer()


@router.callback_query(F.data.startswith("page:") | F.data.startswith("view:") | (F.data == "menu:browse"))
async def on_gated_callback_denied(query: CallbackQuery) -> None:
    await query.answer(denial_text(), show_alert=True)
