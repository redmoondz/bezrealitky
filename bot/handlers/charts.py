"""``/charts`` — distribution charts for the current saved search."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from src import db

from .. import i18n
from ..access import IsAllowed, denial_text_for
from ..charts import CHART_BUILDERS
from ..keyboards import charts_keyboard

router = Router(name="charts")


def _user_language(telegram_user_id: int) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_language(conn, telegram_user_id)


def _build_chart(telegram_user_id: int, key: str) -> tuple[bytes | None, str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        language = db.get_user_language(conn, telegram_user_id)
        builder = CHART_BUILDERS.get(key)
        if builder is None:
            return None, language
        rows = db.fetch_relevant_listings(conn, telegram_user_id)
    return builder(rows), language


@router.message(Command("charts"), IsAllowed())
async def charts_menu(message: Message) -> None:
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    await message.answer(i18n.t("charts_pick", language), reply_markup=charts_keyboard(language))


@router.message(Command("charts"))
async def charts_menu_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.callback_query(F.data == "menu:charts", IsAllowed())
async def on_menu_charts(query: CallbackQuery) -> None:
    language = await asyncio.to_thread(_user_language, query.from_user.id)
    if query.message:
        await query.message.answer(i18n.t("charts_pick", language), reply_markup=charts_keyboard(language))
    await query.answer()


@router.callback_query(F.data == "menu:charts")
async def on_menu_charts_denied(query: CallbackQuery) -> None:
    await query.answer(await denial_text_for(query.from_user.id), show_alert=True)


@router.callback_query(F.data.startswith("chart:"), IsAllowed())
async def on_chart(query: CallbackQuery) -> None:
    key = query.data.split(":", 1)[1]
    png, language = await asyncio.to_thread(_build_chart, query.from_user.id, key)
    if png is None or not query.message:
        await query.answer(i18n.t("chart_unknown", language), show_alert=True)
        return
    label = i18n.chart_label(key, language)
    await query.message.answer_photo(BufferedInputFile(png, filename=f"{key}.png"), caption=label)
    await query.answer()


@router.callback_query(F.data.startswith("chart:"))
async def on_chart_denied(query: CallbackQuery) -> None:
    await query.answer(await denial_text_for(query.from_user.id), show_alert=True)
