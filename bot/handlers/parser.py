"""``/parse``, ``/parse_custom``, ``/search``, and ``/parse_help``.

Each Telegram user has their own independent saved search, stored as
``bot_users.search_url``. A first-time user is seeded from the project's default
search (``config/defaults.yaml`` — the broad Brno search) the first time they run
/parse or /parse_custom; from then on /parse_custom edits *their own* search only.

Flag parsing reuses the exact argparse parser from ``src/cli.py`` so the bot never
re-implements validation, and so ``/parse_help`` can never drift from what the real
CLI accepts: it's generated straight from ``build_parser().format_help()``. Parsing
happens through argparse itself (never a shell), so there's no command-injection
surface — a malformed flag just fails validation like any CLI misuse.
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

from ..access import IsAllowed, denial_text

router = Router(name="parser")


_HELP_PREFIX = (
    "Only --url, --price-from, --price-to, --delay, --timeout, and --max-retries "
    "apply here — they update *your own* saved search and run it right away.\n"
    "--output, --reset, --show, --run, and --config are CLI-only and are ignored.\n"
    "Example: /parse_custom --price-from 500 --price-to 1200\n\n"
)


def _help_text() -> str:
    parser = build_parser()
    parser.prog = "/parse_custom"
    return escape(_HELP_PREFIX + parser.format_help())


def _parse_args(argv: list[str]):
    parser = build_parser()
    parser.prog = "/parse_custom"
    try:
        return parser.parse_args(argv), None
    except SystemExit:
        return None, "Couldn't parse those flags. Send /parse_help to see the accepted options."


def _current_search_url(telegram_user_id: int) -> str:
    base_config = load_config()
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_or_seed_user_search(conn, telegram_user_id, base_config["search"]["url"])


def _run_saved_search(telegram_user_id: int):
    base_config = load_config()
    with db.connect() as conn:
        db.ensure_schema(conn)
        search_url = db.get_or_seed_user_search(conn, telegram_user_id, base_config["search"]["url"])
    return run_once_for_user(telegram_user_id, search_url, base_config)


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
    return new_url, listings, failures


@router.message(Command("parse_help"))
async def parse_help(message: Message) -> None:
    await message.answer(f"<pre>{_help_text()}</pre>", parse_mode="HTML")


@router.message(Command("search"), IsAllowed())
async def search(message: Message) -> None:
    url = await asyncio.to_thread(_current_search_url, message.from_user.id)
    await message.answer(f"Your saved search:\n{url}\n\nChange it with /parse_custom.")


@router.message(Command("search"))
async def search_denied(message: Message) -> None:
    await message.answer(denial_text())


@router.message(Command("parse"), IsAllowed())
async def parse(message: Message) -> None:
    await message.answer("Running the scraper with your saved search…")
    try:
        listings, failures = await asyncio.to_thread(_run_saved_search, message.from_user.id)
    except (ConfigurationError, OSError) as exc:
        await message.answer(f"Scrape failed: {exc}")
        return
    text = f"Synced {len(listings)} listings."
    if failures:
        text += f" {len(failures)} publication(s) failed to parse."
    await message.answer(text)


@router.message(Command("parse"))
async def parse_denied(message: Message) -> None:
    await message.answer(denial_text())


@router.message(Command("parse_custom"), IsAllowed())
async def parse_custom(message: Message) -> None:
    _, _, argv_text = (message.text or "").partition(" ")
    args, error = _parse_args(shlex.split(argv_text))
    if error:
        await message.answer(error)
        return
    if not has_updates(args):
        await message.answer(
            "No flags given — see /parse_help, or just use /parse to run your saved search."
        )
        return
    await message.answer("Updating your saved search and running the scraper…")
    try:
        new_url, listings, failures = await asyncio.to_thread(
            _apply_flags_and_run, message.from_user.id, args
        )
    except (ConfigurationError, OSError) as exc:
        await message.answer(f"Scrape failed: {exc}")
        return
    text = f"Saved search updated:\n{new_url}\n\nSynced {len(listings)} listings."
    if failures:
        text += f" {len(failures)} publication(s) failed to parse."
    await message.answer(text)


@router.message(Command("parse_custom"))
async def parse_custom_denied(message: Message) -> None:
    await message.answer(denial_text())
