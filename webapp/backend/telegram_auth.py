"""Validates Telegram Mini App ``initData`` using Telegram's documented
HMAC-SHA256 scheme, then enforces the same ``TELEGRAM_ALLOWED_USER_IDS``
allowlist ``bot/access.py`` uses for the chat bot — fails closed the same way.

Deliberately imports only ``bot.config`` (plain env parsing, no ``aiogram``)
rather than ``bot.access`` itself, so the webapp process never pulls the
Telegram Bot API client library into its dependency tree just to read two
environment-derived sets.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException

from bot import config as bot_config

from .schemas import TelegramUser

MAX_AUTH_AGE_SECONDS = 24 * 3600


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Return the parsed, hash-verified ``initData`` fields, or raise
    ``ValueError`` with a short reason.
    """
    if not init_data:
        raise ValueError("missing initData")
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("missing hash")
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    computed_hash = hmac.new(
        _secret_key(bot_token), data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("hash mismatch")
    auth_date = int(pairs.get("auth_date", "0") or "0")
    if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
        raise ValueError("stale auth_date")
    return pairs


def _denial_text() -> str:
    """Mirrors ``bot/access.py::denial_text`` — duplicated (not imported) to
    keep this module free of any ``aiogram`` dependency; see module docstring.
    """
    if not bot_config.ALLOWED_USER_IDS:
        return (
            "This app isn't configured yet: set TELEGRAM_ALLOWED_USER_IDS in the "
            "server's .env file to your Telegram user ID and restart the bot."
        )
    return "You're not authorized to use this app."


async def get_current_telegram_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> TelegramUser:
    if not bot_config.BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Bot is not configured")
    try:
        pairs = validate_init_data(x_telegram_init_data, bot_config.BOT_TOKEN)
        user_data = json.loads(pairs["user"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Telegram auth: {exc}") from exc
    user = TelegramUser(
        id=user_data["id"],
        first_name=user_data.get("first_name", ""),
        last_name=user_data.get("last_name", ""),
        username=user_data.get("username", ""),
        language_code=user_data.get("language_code", ""),
        is_premium=bool(user_data.get("is_premium", False)),
    )
    if user.id not in bot_config.ALLOWED_USER_IDS:
        raise HTTPException(status_code=403, detail=_denial_text())
    return user


async def get_current_admin_user(
    user: TelegramUser = Depends(get_current_telegram_user),
) -> TelegramUser:
    """Narrower than :func:`get_current_telegram_user` — requires the caller's
    ID to also be in ``TELEGRAM_ADMIN_USER_IDS``, for the Mini App's Admin tab.
    """
    if user.id not in bot_config.ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user
