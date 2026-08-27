"""Allowlist gate for commands that read or control scraper data.

Fails closed: if ``TELEGRAM_ALLOWED_USER_IDS`` is empty, every gated command is
refused (with a setup hint) rather than left open to anyone who finds the bot.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from . import config


class IsAllowed(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user) and user.id in config.ALLOWED_USER_IDS


def denial_text() -> str:
    if not config.ALLOWED_USER_IDS:
        return (
            "This bot isn't configured yet: set TELEGRAM_ALLOWED_USER_IDS in the "
            "server's .env file to your Telegram user ID and restart the bot."
        )
    return "You're not authorized to use this bot."
