"""``/parse``, ``/parse_custom``, ``/search``, and ``/parse_help``.

Each Telegram user has their own independent saved search, stored as
``bot_users.search_url``. A first-time user is seeded from the project's default
search (``config/defaults.yaml`` — the broad Brno search) the first time they run
/parse or /parse_custom; from then on /parse_custom edits *their own* search only.

Flag parsing reuses the exact argparse parser from ``src/cli.py`` so the bot never
re-implements validation, and so ``/parse_help`` can never drift from what the real
CLI accepts: it's generated straight from ``build_parser().format_help()``. Parsing
happens through argparse itself (never a shell), so there's no command-injection
surface — a malformed flag just fails validation like any CLI misuse. The flag names
and argparse-generated help text below stay in English regardless of the user's
chosen language — they're literal syntax, not prose — only the surrounding
explanation is translated.
"""

from __future__ import annotations

import asyncio
import shlex
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src import db
from src.cli import build_parser, has_updates
from src.configuration import ConfigurationError, apply_updates, load_config
from src.scheduler import run_once_for_user, user_config

from .. import i18n
from ..access import IsAllowed, denial_text_for
from ..keyboards import batch_summary_keyboard

router = Router(name="parser")


def _user_language(telegram_user_id: int) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_language(conn, telegram_user_id)


def _help_text(language: str) -> str:
    parser = build_parser()
    parser.prog = "/parse_custom"
    return escape(i18n.t("parse_help_prefix", language) + parser.format_help())


def _parse_args(argv: list[str], language: str):
    parser = build_parser()
    parser.prog = "/parse_custom"
    try:
        return parser.parse_args(argv), None
    except SystemExit:
        return None, i18n.t("parse_flags_error", language)


def _current_search_url(telegram_user_id: int) -> tuple[str, str]:
    base_config = load_config()
    with db.connect() as conn:
        db.ensure_schema(conn)
        url = db.get_or_seed_user_search(conn, telegram_user_id, base_config["search"]["url"])
        language = db.get_user_language(conn, telegram_user_id)
    return url, language


def _new_match_count_and_language(telegram_user_id: int) -> tuple[int, str]:
    with db.connect() as conn:
        db.ensure_schema(conn)
        new_count = db.count_unnotified_relevant_listings(conn, telegram_user_id)
        language = db.get_user_language(conn, telegram_user_id)
        return new_count, language


def _sync_summary(listings: list, failures: list, new_count: int, language: str) -> str:
    new_note = (
        i18n.t("sync_new_some", language, count=new_count) if new_count else i18n.t("sync_new_none", language)
    )
    text = i18n.t("sync_summary", language, count=len(listings), new_note=new_note)
    if failures:
        text += i18n.t("sync_failures_suffix", language, count=len(failures))
    return text


def _run_saved_search(telegram_user_id: int):
    base_config = load_config()
    with db.connect() as conn:
        db.ensure_schema(conn)
        search_url = db.get_or_seed_user_search(conn, telegram_user_id, base_config["search"]["url"])
    listings, failures = run_once_for_user(telegram_user_id, search_url, base_config)
    new_count, language = _new_match_count_and_language(telegram_user_id)
    return listings, failures, new_count, language


def _apply_flags_and_run(telegram_user_id: int, args):
    base_config = load_config()
    with db.connect() as conn:
        db.ensure_schema(conn)
        current_url = db.get_or_seed_user_search(conn, telegram_user_id, base_config["search"]["url"])
    updated = apply_updates(
        user_config(base_config, current_url),
        url=args.url,
        price_from=args.price_from,
        price_to=args.price_to,
        delay=args.delay,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    new_url = updated["search"]["url"]
    with db.connect() as conn:
        db.set_user_search(conn, telegram_user_id, new_url)
    listings, failures = run_once_for_user(telegram_user_id, new_url, base_config)
    new_count, language = _new_match_count_and_language(telegram_user_id)
    return new_url, listings, failures, new_count, language


@router.message(Command("parse_help"))
async def parse_help(message: Message) -> None:
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    await message.answer(f"<pre>{_help_text(language)}</pre>", parse_mode="HTML")


@router.message(Command("search"), IsAllowed())
async def search(message: Message) -> None:
    url, language = await asyncio.to_thread(_current_search_url, message.from_user.id)
    await message.answer(i18n.t("search_current", language, url=url))


@router.message(Command("search"))
async def search_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.message(Command("parse"), IsAllowed())
async def parse(message: Message) -> None:
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    await message.answer(i18n.t("parse_running", language))
    try:
        listings, failures, new_count, language = await asyncio.to_thread(
            _run_saved_search, message.from_user.id
        )
    except (ConfigurationError, OSError) as exc:
        await message.answer(i18n.t("scrape_failed", language, error=str(exc)))
        return
    keyboard = batch_summary_keyboard(language) if new_count else None
    await message.answer(_sync_summary(listings, failures, new_count, language), reply_markup=keyboard)


@router.message(Command("parse"))
async def parse_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))


@router.message(Command("parse_custom"), IsAllowed())
async def parse_custom(message: Message) -> None:
    language = await asyncio.to_thread(_user_language, message.from_user.id)
    _, _, argv_text = (message.text or "").partition(" ")
    args, error = _parse_args(shlex.split(argv_text), language)
    if error:
        await message.answer(error)
        return
    if not has_updates(args):
        await message.answer(i18n.t("parse_custom_no_flags", language))
        return
    await message.answer(i18n.t("parse_custom_running", language))
    try:
        new_url, listings, failures, new_count, language = await asyncio.to_thread(
            _apply_flags_and_run, message.from_user.id, args
        )
    except (ConfigurationError, OSError) as exc:
        await message.answer(i18n.t("scrape_failed", language, error=str(exc)))
        return
    text = i18n.t(
        "parse_custom_updated",
        language,
        url=new_url,
        summary=_sync_summary(listings, failures, new_count, language),
    )
    keyboard = batch_summary_keyboard(language) if new_count else None
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("parse_custom"))
async def parse_custom_denied(message: Message) -> None:
    await message.answer(await denial_text_for(message.from_user.id))
