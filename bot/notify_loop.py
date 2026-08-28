"""Background task: alert each registered user about their own new matches.

Runs inside the bot process (not the scheduler) so all outbound Telegram traffic
stays in one place. Polls more often than the scheduler's 2-hour scrape interval
so alerts arrive promptly without needing to know its exact timing. Every
registered user (anyone with a saved search) is notified at their own Telegram
user ID — valid because a private chat's ID is the same as the user's ID — in
their own chosen language, independent of any other user's search or matches.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from src import db

from . import config, formatting, i18n
from .keyboards import batch_summary_keyboard
from .translate import translate_description

LOGGER = logging.getLogger(__name__)


def _registered_users() -> list[int]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.list_registered_users(conn)


def load_unnotified(telegram_user_id: int) -> tuple[list[dict], str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        rows = db.fetch_unnotified_relevant_listings(conn, telegram_user_id)
        language = db.get_user_language(conn, telegram_user_id)
    return rows, language


def _mark_notified(telegram_user_id: int, listing_ids: list[str]) -> None:
    with db.connect() as conn:
        db.mark_notified(conn, telegram_user_id, listing_ids)


async def _notify_one(bot: Bot, telegram_user_id: int, row: dict, language: str) -> None:
    header = "🆕 <b>New match in your saved search</b>\n\n" + formatting.detail_text(row, "", language)
    images = row.get("images") or []
    try:
        if images:
            await bot.send_photo(telegram_user_id, images[0], caption=header[:1024], parse_mode="HTML")
        else:
            await bot.send_message(telegram_user_id, header, parse_mode="HTML")
        description = row.get("description") or ""
        if description:
            translated = await asyncio.to_thread(translate_description, description, language)
            await bot.send_message(telegram_user_id, translated[:4096])
    except Exception:  # noqa: BLE001 - one bad send must not stop the others
        LOGGER.exception(
            "Failed to notify user %s about listing %s", telegram_user_id, row["listing_id"]
        )


async def _notify_batch_summary(bot: Bot, telegram_user_id: int, count: int, language: str) -> None:
    try:
        await bot.send_message(
            telegram_user_id,
            i18n.batch_summary_text(language, count),
            parse_mode="HTML",
            reply_markup=batch_summary_keyboard(language),
        )
    except Exception:  # noqa: BLE001 - one bad send must not stop the others
        LOGGER.exception("Failed to send batch summary to user %s", telegram_user_id)


async def notify_matches(bot: Bot, telegram_user_id: int, rows: list[dict], language: str) -> None:
    """Alert one user about their (already-fetched) unnotified matches, then mark
    them notified. More than ``NOTIFY_BATCH_THRESHOLD`` at once collapses into a
    single summary — e.g. a first-time search, or a filter change that suddenly
    widens the results — so the user isn't flooded with one message per listing.
    """
    if not rows:
        return
    if len(rows) > config.NOTIFY_BATCH_THRESHOLD:
        await _notify_batch_summary(bot, telegram_user_id, len(rows), language)
    else:
        for row in rows:
            await _notify_one(bot, telegram_user_id, row, language)
    await asyncio.to_thread(_mark_notified, telegram_user_id, [row["listing_id"] for row in rows])
    LOGGER.info("Notified user %s about %d new listing(s)", telegram_user_id, len(rows))


async def _notify_user(bot: Bot, telegram_user_id: int) -> None:
    rows, language = await asyncio.to_thread(load_unnotified, telegram_user_id)
    await notify_matches(bot, telegram_user_id, rows, language)


async def run(bot: Bot) -> None:
    while True:
        try:
            users = await asyncio.to_thread(_registered_users)
            for telegram_user_id in users:
                await _notify_user(bot, telegram_user_id)
        except Exception:  # noqa: BLE001 - a bad cycle must not kill the loop
            LOGGER.exception("Notify loop cycle failed; will retry next interval")
        await asyncio.sleep(config.NOTIFY_POLL_SECONDS)
