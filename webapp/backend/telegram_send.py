"""Minimal Telegram Bot API client for the admin broadcast feature.

Deliberately a plain HTTP call rather than aiogram — the webapp process
doesn't install aiogram, to keep its dependency footprint light (see
``telegram_auth.py``'s module docstring); this is the one place it needs to
actually send a message rather than just validate auth, so it talks to the
Bot API directly instead of pulling in the full client library.
"""

from __future__ import annotations

import requests

from bot import config as bot_config

_API_BASE = "https://api.telegram.org"
_TIMEOUT_SECONDS = 15


def send_message(chat_id: int, text: str) -> bool:
    """Best-effort send — returns whether it succeeded rather than raising, so
    one blocked/deactivated chat in a broadcast never stops the rest.
    """
    try:
        response = requests.post(
            f"{_API_BASE}/bot{bot_config.BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=_TIMEOUT_SECONDS,
        )
        return response.ok and bool(response.json().get("ok"))
    except requests.RequestException:
        return False
