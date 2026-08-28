"""``/list`` (paginated browsing, Tinder-style Like/Dislike), ``/view <listing_id>``
(full detail), and ``/liked`` (a user's own liked listings).

Every query is scoped to the calling Telegram user's own saved search — there is
no shared "the current saved search," each user has their own. Liking or
disliking a listing removes it from /list for good (see ``reaction`` on
``user_listing_relevance``); liked listings additionally stay browsable via
/liked regardless of whether the listing is still ``is_relevant``.

Each card's photos go out first as their own message(s) since Telegram's
``sendMediaGroup`` can't carry an inline keyboard, then a details message with
the Like/Dislike/Prev/Next keyboard follows. A media group can't be edited in
place, so Prev/Next/Like/Dislike send a fresh card rather than editing the old
one — but the previous card's messages (photos + details) are deleted first,
tracked per-chat via FSM storage's freeform data (``card_message_ids``,
independent of any actual FSM *state*), so the chat always shows one current
card rather than accumulating every card ever shown.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from src import db

from .. import formatting, i18n
from ..access import IsAllowed, denial_text_for
from ..keyboards import PAGE_SIZE, listing_keyboard, reaction_keyboard

router = Router(name="browse")


def _load_page(telegram_user_id: int, offset: int) -> tuple[int, dict | None, str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        total = db.count_relevant_listings(conn, telegram_user_id)
        rows = db.fetch_relevant_listings_page(conn, telegram_user_id, offset, PAGE_SIZE)
        language = db.get_user_language(conn, telegram_user_id)
        return total, (rows[0] if rows else None), language


def _load_liked_page(telegram_user_id: int, offset: int) -> tuple[int, dict | None, str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        total = db.count_liked_listings(conn, telegram_user_id)
        rows = db.fetch_liked_listings_page(conn, telegram_user_id, offset, PAGE_SIZE)
        language = db.get_user_language(conn, telegram_user_id)
        return total, (rows[0] if rows else None), language


def _record_reaction(telegram_user_id: int, listing_id: str, reaction: str) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.record_reaction(conn, telegram_user_id, listing_id, reaction)
        return db.get_user_language(conn, telegram_user_id)


def _load_detail(listing_id: str, telegram_user_id: int) -> tuple[dict | None, str, str, bool]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        language = db.get_user_language(conn, telegram_user_id)
        row = db.fetch_listing(conn, listing_id)
        if row is None:
            return None, "", language, True
        row["score"] = db.get_relevance_score(conn, telegram_user_id, listing_id)
        description = row.get("description") or ""
        translated, translation_ok = db.get_or_translate_description(
            conn, listing_id, description, language
        )
    return row, translated, language, translation_ok


def _user_language(telegram_user_id: int) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_language(conn, telegram_user_id)


_CARD_PHOTO_COUNT = 4


async def _clear_previous_card(message: Message, state: FSMContext) -> None:
    """Delete every message from the last card shown in this chat, if any —
    called right before showing a new one so the chat holds a single current
    card instead of piling up every past card.
    """
    data = await state.get_data()
    for message_id in data.get("card_message_ids") or []:
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception:  # noqa: BLE001 - already gone/too old/no permission; nothing to recover
            pass
    await state.update_data(card_message_ids=[])


async def _send_card_photos(message: Message, images: list[str]) -> list[int]:
    """A card's photos as their own message(s) — a Telegram photo caption can
    carry an inline keyboard, but ``sendMediaGroup`` cannot, so the keyboard
    always lives on the separate details message sent right after this.
    Returns the sent messages' IDs so the card can be deleted as a whole later.
    """
    if len(images) >= 2:
        sent = await message.answer_media_group(
            [InputMediaPhoto(media=url) for url in images[:_CARD_PHOTO_COUNT]]
        )
        return [item.message_id for item in sent]
    if images:
        sent = await message.answer_photo(images[0])
        return [sent.message_id]
    return []


async def _render_card(
    message: Message,
    row: dict,
    offset: int,
    total: int,
    language: str,
    state: FSMContext,
    nav_prefix: str = "page",
    show_reactions: bool = True,
) -> None:
    message_ids = await _send_card_photos(message, row.get("images") or [])
    caption = formatting.summary_caption(row, offset, total, language)
    keyboard = listing_keyboard(
        row["listing_id"],
        row["url"],
        offset,
        total,
        language,
        nav_prefix=nav_prefix,
        show_reactions=show_reactions,
    )
    details = await message.answer(caption, parse_mode="HTML", reply_markup=keyboard)
    message_ids.append(details.message_id)
    await state.update_data(card_message_ids=message_ids)


async def _send_page(message: Message, telegram_user_id: int, offset: int, state: FSMContext) -> None:
    total, row, language = await asyncio.to_thread(_load_page, telegram_user_id, offset)
    await _clear_previous_card(message, state)
    if row is None:
        await message.answer(i18n.t("no_listings_match", language))
        return
    await _render_card(message, row, offset, total, language, state)


async def _send_liked_page(
    message: Message, telegram_user_id: int, offset: int, state: FSMContext
) -> None:
    total, row, language = await asyncio.to_thread(_load_liked_page, telegram_user_id, offset)
    await _clear_previous_card(message, state)
    if row is None:
        await message.answer(i18n.t("no_liked_listings", language))
        return
    await _render_card(
        message, row, offset, total, language, state, nav_prefix="likedpage", show_reactions=False
    )


async def _send_detail(target: Message, listing_id: str, telegram_user_id: int, offset: int = 0) -> None:
    row, translated, language, translation_ok = await asyncio.to_thread(
        _load_detail, listing_id, telegram_user_id
    )
    if row is None:
        await target.answer(i18n.t("listing_not_found", language, id=listing_id))
        return
    images = row.get("images") or []
    if len(images) > 1:
        await target.answer_media_group([InputMediaPhoto(media=url) for url in images[:10]])
    elif images:
        await target.answer_photo(images[0])
    await target.answer(
        formatting.detail_text(row, translated, language, translation_ok),
        parse_mode="HTML",
        reply_markup=reaction_keyboard(listing_id, offset, language, prefix="reactd"),
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
async def list_listings(message: Message, state: FSMContext) -> None:
    await _send_page(message, message.from_user.id, 0, state)


@router.message(Command("list"))
async def list_listings_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.message(Command("view"), IsAllowed())
async def view_listing(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        language = await asyncio.to_thread(_user_language, message.from_user.id)
        await message.answer(i18n.t("view_usage", language))
        return
    await _send_detail(message, parts[1].strip(), message.from_user.id, 0)


@router.message(Command("view"))
async def view_listing_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.message(Command("liked"), IsAllowed())
async def liked_listings(message: Message, state: FSMContext) -> None:
    await _send_liked_page(message, message.from_user.id, 0, state)


@router.message(Command("liked"))
async def liked_listings_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.callback_query(F.data.startswith("page:"), IsAllowed())
async def on_page(query: CallbackQuery, state: FSMContext) -> None:
    offset = int(query.data.split(":", 1)[1])
    await query.answer()
    if query.message:
        await _send_page(query.message, query.from_user.id, offset, state)


@router.callback_query(F.data.startswith("likedpage:"), IsAllowed())
async def on_liked_page(query: CallbackQuery, state: FSMContext) -> None:
    offset = int(query.data.split(":", 1)[1])
    await query.answer()
    if query.message:
        await _send_liked_page(query.message, query.from_user.id, offset, state)


@router.callback_query(F.data.startswith("react:") | F.data.startswith("reactd:"), IsAllowed())
async def on_react(query: CallbackQuery, state: FSMContext) -> None:
    """Liking/disliking from a /list swipe card (``react:``) or from the /view
    detail card (``reactd:``) — either way, records the reaction and hands
    back into the /list queue at that card's offset to keep the swipe flow
    going.
    """
    _, reaction, offset_str, listing_id = query.data.split(":", 3)
    language = await asyncio.to_thread(_record_reaction, query.from_user.id, listing_id, reaction)
    await query.answer(i18n.t("reacted_liked" if reaction == "like" else "reacted_passed", language))
    if query.message:
        await _send_page(query.message, query.from_user.id, int(offset_str), state)


@router.callback_query(F.data.startswith("view:"), IsAllowed())
async def on_view(query: CallbackQuery) -> None:
    _, offset_str, listing_id = query.data.split(":", 2)
    if query.message:
        await _send_detail(query.message, listing_id, query.from_user.id, int(offset_str))
    await query.answer()


@router.callback_query(F.data == "menu:browse", IsAllowed())
async def on_menu_browse(query: CallbackQuery, state: FSMContext) -> None:
    if query.message:
        await _send_page(query.message, query.from_user.id, 0, state)
    await query.answer()


@router.callback_query(
    F.data.startswith("page:")
    | F.data.startswith("likedpage:")
    | F.data.startswith("react:")
    | F.data.startswith("reactd:")
    | F.data.startswith("view:")
    | (F.data == "menu:browse")
)
async def on_gated_callback_denied(query: CallbackQuery) -> None:
    await query.answer(await denial_text_for(query.from_user.id), show_alert=True)
