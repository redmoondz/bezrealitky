"""Allowlist gate for commands that read or control scraper data.

Fails closed: if ``TELEGRAM_ALLOWED_USER_IDS`` is empty, every gated command is
refused (with a setup hint) rather than left open to anyone who finds the bot.
Set ``TELEGRAM_PUBLIC_ACCESS=true`` to flip this off and open every gated
command to any Telegram user, regardless of the allowlist; leaving it unset
keeps the default closed behavior.
"""

from __future__ import annotations

import asyncio

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src import db

from . import config, i18n


class IsAllowed(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if config.PUBLIC_ACCESS:
            return bool(event.from_user)
        user = event.from_user
        return bool(user) and user.id in config.ALLOWED_USER_IDS


def denial_text(language: str = "en") -> str:
    if not config.ALLOWED_USER_IDS:
        return i18n.t("denial_setup", language)
    return i18n.t("denial_not_authorized", language)


def _user_language(telegram_user_id: int) -> str:
    with db.connect() as conn:
        db.ensure_schema(conn)
        return db.get_user_language(conn, telegram_user_id)


async def denial_text_for(telegram_user_id: int) -> str:
    """The denial message in this user's own chosen language — looked up even
    for gated commands, since language selection is open to everyone (see
    module docstring), so an unauthorized user may well have already picked one.
    """
    language = await asyncio.to_thread(_user_language, telegram_user_id)
    return denial_text(language)
