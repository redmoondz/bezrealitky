"""Dispatcher-wide middleware that records every Telegram user's profile info.

Registered as an outer middleware (see ``main.py``) so it runs for every
incoming message/callback regardless of which handler — if any — ultimately
processes it, including unauthorized users and messages no handler matches.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from src import db


def _track(user: User) -> None:
    with db.connect() as conn:
        db.ensure_schema(conn)
        db.upsert_telegram_user(
            conn,
            user.id,
            user.first_name or "",
            user.last_name or "",
            user.username or "",
            user.language_code or "",
            bool(user.is_premium),
        )


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is not None:
            await asyncio.to_thread(_track, event.from_user)
        return await handler(event, data)
