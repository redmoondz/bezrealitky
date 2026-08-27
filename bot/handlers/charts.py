"""``/charts`` — distribution charts for the current saved search."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from src import db

from ..access import IsAllowed, denial_text
from ..charts import CHART_BUILDERS
from ..keyboards import CHART_OPTIONS, charts_keyboard

router = Router(name="charts")


def _build_chart(telegram_user_id: int, key: str) -> bytes | None:
    builder = CHART_BUILDERS.get(key)
    if builder is None:
        return None
    with db.connect() as conn:
        db.ensure_schema(conn)
        rows = db.fetch_relevant_listings(conn, telegram_user_id)
    return builder(rows)


@router.message(Command("charts"), IsAllowed())
async def charts_menu(message: Message) -> None:
    await message.answer("Pick a chart:", reply_markup=charts_keyboard())


@router.message(Command("charts"))
async def charts_menu_denied(message: Message) -> None:
    await message.answer(denial_text())


@router.callback_query(F.data == "menu:charts", IsAllowed())
async def on_menu_charts(query: CallbackQuery) -> None:
    if query.message:
        await query.message.answer("Pick a chart:", reply_markup=charts_keyboard())
    await query.answer()


@router.callback_query(F.data == "menu:charts")
async def on_menu_charts_denied(query: CallbackQuery) -> None:
    await query.answer(denial_text(), show_alert=True)


@router.callback_query(F.data.startswith("chart:"), IsAllowed())
async def on_chart(query: CallbackQuery) -> None:
    key = query.data.split(":", 1)[1]
    png = await asyncio.to_thread(_build_chart, query.from_user.id, key)
    if png is None or not query.message:
        await query.answer("Unknown chart.", show_alert=True)
        return
    label = dict(CHART_OPTIONS).get(key, key)
    await query.message.answer_photo(BufferedInputFile(png, filename=f"{key}.png"), caption=label)
    await query.answer()


@router.callback_query(F.data.startswith("chart:"))
async def on_chart_denied(query: CallbackQuery) -> None:
    await query.answer(denial_text(), show_alert=True)
