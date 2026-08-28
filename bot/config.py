"""Environment-driven configuration for the Telegram bot."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Matches the variable name already used in this project's .env file.
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_API", "").strip()

NOTIFY_POLL_SECONDS = int(os.environ.get("NOTIFY_POLL_SECONDS", "600"))

# More new matches than this in one sync (a first-time search, or a filter
# change that suddenly widens the results) collapse into a single summary
# notification instead of one message per listing.
NOTIFY_BATCH_THRESHOLD = int(os.environ.get("NOTIFY_BATCH_THRESHOLD", "5"))

# Descriptions are shown translated into whichever of these the user picks via
# /start or /language; the source text itself (mostly Czech) is left untouched.
SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("cs", "Čeština"),
    ("ru", "Русский"),
    ("uk", "Українська"),
]
SUPPORTED_LANGUAGE_CODES = {code for code, _ in SUPPORTED_LANGUAGES}


def _parse_id_list(value: str) -> set[int]:
    ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError:
            continue
    return ids


ALLOWED_USER_IDS = _parse_id_list(os.environ.get("TELEGRAM_ALLOWED_USER_IDS", ""))
