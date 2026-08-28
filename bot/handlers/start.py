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
from aiogram.types import BotCommand, CallbackQuery, Message

from src import db
from src.configuration import ConfigurationError, load_config, validate_search_url
from src.scheduler import run_once_for_user
from src.scraper import parse_number

from .. import config, notify_loop
from ..access import IsAllowed, denial_text
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


ONBOARDING_PROMPT = (
    "🔗 <b>One more thing — let's personalize your search.</b>\n\n"
    "Send me the link to your search results on bezrealitky.com:\n"
    "1️⃣ Open bezrealitky.com and set your filters (city, price, rooms…)\n"
    "2️⃣ Run the search so the results page loads\n"
    "3️⃣ Copy the URL from your browser's address bar\n"
    "4️⃣ Paste it here as a message\n\n"
    "Or tap the button below to start with the project's default search instead — "
    "you can always change it later with /parse_custom."
)

PETS_PROMPT = "🐾 Do you have — or want — a place that's pet-friendly?"

_DEFAULT_CURRENCY = "CZK"


def _search_currency(search_url: str) -> str:
    """The ``currency`` filter from the user's own saved search URL — the same
    currency their listing prices are already shown in, so the budget question
    isn't ambiguous about units.
    """
    values = parse_qs(urlparse(search_url).query).get("currency")
    return values[0].upper() if values else _DEFAULT_CURRENCY


def _budget_prompt(currency: str) -> str:
    return (
        f"💰 What's your monthly budget, <b>all costs included</b> (rent + service + "
        f"utility charges), in <b>{escape(currency)}</b>? Send a plain number (e.g. 25000), "
        "or tap Skip.\n\n"
        "This only affects how listings are ranked for you — it won't hide anything."
    )


AREA_PROMPT = (
    "📐 Any minimum size you need, in m²? Send a plain number (e.g. 40), or tap Skip."
)

_NUMBER_RETRY = "That doesn't look like a plain number. Please try again, or tap Skip."

ONBOARDING_RUNNING = "Saving your search and running the scraper now…"

ONBOARDING_NO_RESULTS = (
    "Saved! No listings match it yet — I'll keep checking and let you know when something turns up."
)

# Registered with Telegram via bot.set_my_commands() in main.py, so they show up
# in the "/" command menu next to the message input. Keep in sync with HELP_TEXT.
BOT_COMMANDS = [
    BotCommand(command="start", description="Welcome message and language setup"),
    BotCommand(command="help", description="Show available commands"),
    BotCommand(command="language", description="Choose the translation language"),
    BotCommand(command="list", description="Browse listings matching your saved search"),
    BotCommand(command="view", description="Full details for one listing (needs an ID)"),
    BotCommand(command="parse", description="Run the scraper now with your saved search"),
    BotCommand(command="parse_custom", description="Update your saved search and run it"),
    BotCommand(command="parse_help", description="Show the flags /parse_custom accepts"),
    BotCommand(command="search", description="Show your current saved search"),
    BotCommand(command="charts", description="Distribution charts for your saved search"),
]

HELP_TEXT = (
    "<b>Bezrealitky listings bot</b>\n\n"
    "🌐 /start, /language — choose the language listing descriptions are translated into\n"
    "📋 /list — browse listings matching your saved search\n"
    "🔎 /view &lt;listing_id&gt; — full details and photos for one listing\n"
    "🔄 /parse — run the scraper now with your saved search\n"
    "⚙️ /parse_custom — update your saved search with flags and run it (see /parse_help)\n"
    "🔍 /search — show your current saved search\n"
    "📊 /charts — distribution charts for your saved search\n\n"
    "Everyone has their own independent saved search — /parse_custom only ever "
    "changes yours. First time, it starts from the project's default (broad) search.\n\n"
    "Everything except language selection requires your Telegram user ID to be "
    "in the server's TELEGRAM_ALLOWED_USER_IDS."
)


def _set_language(telegram_user_id: int, language_code: str) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.set_user_language(conn, telegram_user_id, language_code)


def _has_saved_search(telegram_user_id: int) -> bool:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_search(conn, telegram_user_id) is not None


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


async def _ask_pets(message: Message, state: FSMContext, search_url: str) -> None:
    await state.update_data(search_url=search_url)
    await state.set_state(Onboarding.waiting_for_pets)
    await message.answer(PETS_PROMPT, reply_markup=pets_preference_keyboard())


async def _ask_budget(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    currency = _search_currency(data.get("search_url", ""))
    await state.set_state(Onboarding.waiting_for_budget)
    await message.answer(
        _budget_prompt(currency), parse_mode="HTML", reply_markup=skip_keyboard("budget_pref:skip")
    )


async def _ask_area(message: Message, state: FSMContext) -> None:
    await state.set_state(Onboarding.waiting_for_area)
    await message.answer(AREA_PROMPT, reply_markup=skip_keyboard("area_pref:skip"))


async def _finish_onboarding_from_state(message: Message, telegram_user_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    search_url = data.get("search_url", "")
    await state.clear()
    await _finish_onboarding(message, telegram_user_id, search_url)


async def _finish_onboarding(message: Message, telegram_user_id: int, search_url: str) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
    await message.answer(ONBOARDING_RUNNING)
    try:
        _listings, failures = await asyncio.to_thread(_save_and_run, telegram_user_id, search_url)
    except (ConfigurationError, OSError) as exc:
        await message.answer(f"Scrape failed: {exc}\n\nYou can retry anytime with /parse.")
        return
    if failures:
        await message.answer(f"Note: {len(failures)} publication(s) failed to parse.")
    rows, language = await asyncio.to_thread(notify_loop.load_unnotified, telegram_user_id)
    if not rows:
        await message.answer(ONBOARDING_NO_RESULTS)
        return
    await notify_loop.notify_matches(message.bot, telegram_user_id, rows, language)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.set_state(Onboarding.waiting_for_language)
    await message.answer(
        "Welcome! Pick the language you'd like listing descriptions translated into:",
        reply_markup=language_keyboard(),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Onboarding.waiting_for_url, F.text, ~F.text.startswith("/"), IsAllowed())
async def onboarding_receive_url(message: Message, state: FSMContext) -> None:
    try:
        search_url = validate_search_url(message.text)
    except ConfigurationError as exc:
        await message.answer(
            f"That doesn't look like a valid bezrealitky.com search link: {exc}\n\n"
            "Please try again, or tap the button to use the default search instead.",
            reply_markup=onboarding_keyboard(),
        )
        return
    await _ask_pets(message, state, search_url)


@router.message(Onboarding.waiting_for_url, F.text, ~F.text.startswith("/"))
async def onboarding_receive_url_denied(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(denial_text())


@router.callback_query(F.data == "onboarding:skip", IsAllowed())
async def onboarding_skip(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    if query.message:
        search_url = await asyncio.to_thread(_default_search_url)
        await _ask_pets(query.message, state, search_url)


@router.callback_query(F.data == "onboarding:skip")
async def onboarding_skip_denied(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer(denial_text(), show_alert=True)


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
        await message.answer(_NUMBER_RETRY, reply_markup=skip_keyboard("budget_pref:skip"))
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
        await message.answer(_NUMBER_RETRY, reply_markup=skip_keyboard("area_pref:skip"))
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
    await message.answer("Pick a language:", reply_markup=language_keyboard())


async def _apply_language_choice(query: CallbackQuery) -> str | None:
    """Save the chosen language and confirm it in-place. Returns the language's
    display label, or ``None`` if the code was invalid (already answered).
    """
    code = query.data.split(":", 1)[1]
    if code not in config.SUPPORTED_LANGUAGE_CODES:
        await query.answer("Unknown language.", show_alert=True)
        return None
    await asyncio.to_thread(_set_language, query.from_user.id, code)
    label = dict(config.SUPPORTED_LANGUAGES)[code]
    await query.answer(f"Language set to {label}.")
    if query.message:
        await query.message.edit_text(f"Descriptions will now be translated into {label}.")
    return label


@router.callback_query(Onboarding.waiting_for_language, F.data.startswith("lang:"))
async def on_start_language_chosen(query: CallbackQuery, state: FSMContext) -> None:
    """The very first language pick, right after /start — continues straight
    into onboarding instead of just confirming the choice, so /start's messages
    arrive one step at a time instead of all at once.
    """
    if await _apply_language_choice(query) is None:
        return
    has_search = await asyncio.to_thread(_has_saved_search, query.from_user.id)
    if has_search:
        await state.clear()
        if query.message:
            await query.message.answer(HELP_TEXT, parse_mode="HTML")
        return
    await state.set_state(Onboarding.waiting_for_url)
    if query.message:
        await query.message.answer(
            ONBOARDING_PROMPT, parse_mode="HTML", reply_markup=onboarding_keyboard()
        )


@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(query: CallbackQuery) -> None:
    await _apply_language_choice(query)
