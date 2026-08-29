"""``/start``, ``/language``, and ``/help`` — onboarding and language preference.

Open to anyone (not gated by the allowlist): picking a language is harmless and
useful to set up before an operator has approved a user's Telegram ID.
"""

from __future__ import annotations

import asyncio
from html import escape
from urllib.parse import parse_qs, urlparse

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from src import db
from src.configuration import ConfigurationError, load_config, validate_search_url
from src.scheduler import run_once_for_user
from src.scraper import parse_number

from .. import config, i18n, notify_loop
from ..access import IsAllowed, denial_text_for
from ..keyboards import (
    language_keyboard,
    onboarding_keyboard,
    pets_preference_keyboard,
    skip_keyboard,
)

router = Router(name="start")


class Onboarding(StatesGroup):
    waiting_for_language = State()
    waiting_for_url = State()
    waiting_for_pets = State()
    waiting_for_budget = State()
    waiting_for_area = State()


_DEFAULT_CURRENCY = "CZK"

def bot_commands(language: str) -> list[BotCommand]:
    return [
        BotCommand(command=command, description=description)
        for command, description in i18n.bot_command_descriptions(language)
    ]


# Registered with Telegram via bot.set_my_commands() in main.py (English default,
# shown before a language is chosen), and re-registered per-chat in the user's own
# language right after they pick one (see _apply_language_choice below) — and again
# for every known user at startup (see main.py), since Telegram caches a per-chat
# override once set and won't otherwise pick up a newly added command on its own.
BOT_COMMANDS = bot_commands("en")


def _search_currency(search_url: str) -> str:
    """The ``currency`` filter from the user's own saved search URL — the same
    currency their listing prices are already shown in, so the budget question
    isn't ambiguous about units.
    """
    values = parse_qs(urlparse(search_url).query).get("currency")
    return values[0].upper() if values else _DEFAULT_CURRENCY


def _set_language(telegram_user_id: int, language_code: str) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.set_user_language(conn, telegram_user_id, language_code)


def _user_language(telegram_user_id: int) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_language(conn, telegram_user_id)


def _has_saved_search(telegram_user_id: int) -> bool:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_search(conn, telegram_user_id) is not None


def _reset_onboarding(telegram_user_id: int) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.reset_user_onboarding(conn, telegram_user_id)


def _queue_count(telegram_user_id: int) -> int:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.count_relevant_listings(conn, telegram_user_id)


def _default_search_url() -> str:
    return load_config()["search"]["url"]


def _save_and_run(telegram_user_id: int, search_url: str):
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.set_user_search(conn, telegram_user_id, search_url)
    base_config = load_config()
    return run_once_for_user(telegram_user_id, search_url, base_config)


def _save_preference(telegram_user_id: int, column: str, value) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.set_user_preference(conn, telegram_user_id, column, value)


def _parse_preference_number(text: str):
    """A positive number for the budget/area onboarding questions, or ``None``
    if ``text`` isn't one — reuses the scraper's own tolerant number parser
    (handles "25 000", "25,000", decimals, ...) rather than a bespoke regex.
    """
    value = parse_number(text)
    if value is None or value <= 0:
        return None
    return value


async def _ask_pets(message: Message, state: FSMContext, search_url: str, language: str) -> None:
    await state.update_data(search_url=search_url)
    await state.set_state(Onboarding.waiting_for_pets)
    await message.answer(i18n.t("pets_prompt", language), reply_markup=pets_preference_keyboard(language))


async def _ask_budget(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    currency = _search_currency(data.get("search_url", ""))
    language = data.get("language", "en")
    await state.set_state(Onboarding.waiting_for_budget)
    await message.answer(
        i18n.t("budget_prompt", language, currency=escape(currency)),
        parse_mode="HTML",
        reply_markup=skip_keyboard("budget_pref:skip", language),
    )


async def _ask_area(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language = data.get("language", "en")
    await state.set_state(Onboarding.waiting_for_area)
    await message.answer(i18n.t("area_prompt", language), reply_markup=skip_keyboard("area_pref:skip", language))


async def _finish_onboarding_from_state(message: Message, telegram_user_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    search_url = data.get("search_url", "")
    language = data.get("language", "en")
    await state.clear()
    await _finish_onboarding(message, telegram_user_id, search_url, language)


async def _finish_onboarding(message: Message, telegram_user_id: int, search_url: str, language: str) -> None:
    await message.answer(i18n.t("help_text", language), parse_mode="HTML")
    await message.answer(i18n.t("onboarding_running", language))
    try:
        _listings, failures = await asyncio.to_thread(_save_and_run, telegram_user_id, search_url)
    except (ConfigurationError, OSError) as exc:
        await message.answer(i18n.t("onboarding_scrape_failed", language, error=str(exc)))
        return
    if failures:
        await message.answer(i18n.t("onboarding_failures_note", language, count=len(failures)))
    rows, notify_language = await asyncio.to_thread(notify_loop.load_unnotified, telegram_user_id)
    if rows:
        await notify_loop.notify_matches(message.bot, telegram_user_id, rows, notify_language)
        return
    # No *new* matches to push — but "new since the last notification" isn't
    # the same as "nothing found": re-running onboarding with an overlapping
    # search commonly turns up listings that were already notified about in a
    # previous run and are simply still sitting unreacted-to in the queue.
    # Telling the user "no results" there would be flatly wrong.
    queue_count = await asyncio.to_thread(_queue_count, telegram_user_id)
    if queue_count:
        await message.answer(i18n.t("onboarding_queue_waiting", language, count=queue_count))
    else:
        await message.answer(i18n.t("onboarding_no_results", language))


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.set_state(Onboarding.waiting_for_language)
    await message.answer(i18n.LANGUAGE_PROMPT_INITIAL, reply_markup=language_keyboard())


@router.message(Command("onboarding"), IsAllowed())
async def onboarding_restart(message: Message, state: FSMContext) -> None:
    """Redo the onboarding wizard from scratch — clears the saved search and
    preferences first so the post-language-choice handler (which otherwise
    treats a user with a saved search as already onboarded) continues into
    the full wizard again instead of stopping short.
    """
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    await asyncio.to_thread(_reset_onboarding, message.from_user.id)
    await message.answer(i18n.t("onboarding_reset_confirm", language))
    await state.set_state(Onboarding.waiting_for_language)
    await message.answer(i18n.LANGUAGE_PROMPT_INITIAL, reply_markup=language_keyboard())


@router.message(Command("onboarding"))
async def onboarding_restart_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    await message.answer(i18n.t("help_text", language), parse_mode="HTML")


@router.message(Onboarding.waiting_for_url, F.text, ~F.text.startswith("/"), IsAllowed())
async def onboarding_receive_url(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language = data.get("language", "en")
    try:
        search_url = validate_search_url(message.text)
    except ConfigurationError as exc:
        await message.answer(
            i18n.t("onboarding_invalid_url", language, error=str(exc)),
            reply_markup=onboarding_keyboard(language),
        )
        return
    await _ask_pets(message, state, search_url, language)


@router.message(Onboarding.waiting_for_url, F.text, ~F.text.startswith("/"))
async def onboarding_receive_url_denied(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(await denial_text_for(message.from_user.id))


@router.callback_query(F.data == "onboarding:skip", IsAllowed())
async def onboarding_skip(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message:
        data = await state.get_data()
        language = data.get("language", "en")
        search_url = await asyncio.to_thread(_default_search_url)
        await _ask_pets(query.message, state, search_url, language)


@router.callback_query(F.data == "onboarding:skip")
async def onboarding_skip_denied(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer(await denial_text_for(query.from_user.id), show_alert=True)


@router.callback_query(Onboarding.waiting_for_pets, F.data.startswith("pets_pref:"))
async def onboarding_pets_answered(query: CallbackQuery, state: FSMContext) -> None:
    answer = query.data.split(":", 1)[1]
    wants_pets = {"yes": True, "no": False, "skip": None}.get(answer)
    await query.answer()
    if answer != "skip":
        await asyncio.to_thread(_save_preference, query.from_user.id, "wants_pets", wants_pets)
    if query.message:
        await _ask_budget(query.message, state)


@router.message(Onboarding.waiting_for_budget, F.text, ~F.text.startswith("/"))
async def onboarding_budget_answered(message: Message, state: FSMContext) -> None:
    value = _parse_preference_number(message.text)
    if value is None:
        data = await state.get_data()
        language = data.get("language", "en")
        await message.answer(i18n.t("number_retry", language), reply_markup=skip_keyboard("budget_pref:skip", language))
        return
    await asyncio.to_thread(_save_preference, message.from_user.id, "budget_total_price", value)
    await _ask_area(message, state)


@router.callback_query(Onboarding.waiting_for_budget, F.data == "budget_pref:skip")
async def onboarding_budget_skipped(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message:
        await _ask_area(query.message, state)


@router.message(Onboarding.waiting_for_area, F.text, ~F.text.startswith("/"))
async def onboarding_area_answered(message: Message, state: FSMContext) -> None:
    value = _parse_preference_number(message.text)
    if value is None:
        data = await state.get_data()
        language = data.get("language", "en")
        await message.answer(i18n.t("number_retry", language), reply_markup=skip_keyboard("area_pref:skip", language))
        return
    await asyncio.to_thread(_save_preference, message.from_user.id, "min_area_m2", value)
    await _finish_onboarding_from_state(message, message.from_user.id, state)


@router.callback_query(Onboarding.waiting_for_area, F.data == "area_pref:skip")
async def onboarding_area_skipped(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message:
        await _finish_onboarding_from_state(query.message, query.from_user.id, state)


@router.message(Command("language"))
async def language(message: Message) -> None:
    current = await asyncio.to_thread(_user_language, message.from_user.id)
    await message.answer(i18n.t("language_prompt", current), reply_markup=language_keyboard())


async def _apply_language_choice(query: CallbackQuery) -> tuple[str, str] | None:
    """Save the chosen language, confirm it in-place, and re-point this chat's
    command menu (and Mini App button, if configured) at the same language.
    Returns the language's ``(code, display label)``, or ``None`` if the code
    was invalid (already answered).
    """
    code = query.data.split(":", 1)[1]
    if code not in config.SUPPORTED_LANGUAGE_CODES:
        await query.answer(i18n.t("unknown_language", "en"), show_alert=True)
        return None
    await asyncio.to_thread(_set_language, query.from_user.id, code)
    label = dict(config.SUPPORTED_LANGUAGES)[code]
    await query.answer(i18n.t("language_set_answer", code, label=label))
    if query.message:
        await query.message.edit_text(i18n.t("language_set_confirm", code, label=label))
    if query.bot:
        await query.bot.set_my_commands(
            bot_commands(code), scope=BotCommandScopeChat(chat_id=query.from_user.id)
        )
        if config.WEBAPP_URL:
            await query.bot.set_chat_menu_button(
                chat_id=query.from_user.id,
                menu_button=MenuButtonWebApp(
                    text=i18n.t("open_app_button", code), web_app=WebAppInfo(url=config.WEBAPP_URL)
                ),
            )
    return code, label


@router.callback_query(Onboarding.waiting_for_language, F.data.startswith("lang:"))
async def on_start_language_chosen(query: CallbackQuery, state: FSMContext) -> None:
    """The very first language pick, right after /start — continues straight
    into onboarding instead of just confirming the choice, so /start's messages
    arrive one step at a time instead of all at once.
    """
    result = await _apply_language_choice(query)
    if result is None:
        return
    code, _label = result
    await state.update_data(language=code)
    has_search = await asyncio.to_thread(_has_saved_search, query.from_user.id)
    if has_search:
        await state.clear()
        if query.message:
            await query.message.answer(i18n.t("help_text", code), parse_mode="HTML")
        return
    await state.set_state(Onboarding.waiting_for_url)
    if query.message:
        await query.message.answer(
            i18n.t("onboarding_prompt", code), parse_mode="HTML", reply_markup=onboarding_keyboard(code)
        )


@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(query: CallbackQuery) -> None:
    await _apply_language_choice(query)
