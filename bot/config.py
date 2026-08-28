"""Environment-driven configuration for the Telegram bot."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Matches the variable name already used in this project's .env file.
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_API", "").strip()

NOTIFY_POLL_SECONDS = int(os.environ.get("NOTIFY_POLL_SECONDS", "600"))

# Public HTTPS URL of the Mini App (webapp/), if deployed — set as the bot's
# persistent menu button in main.py. Empty means no menu button is set.
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip()

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


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


ALLOWED_USER_IDS = _parse_id_list(os.environ.get("TELEGRAM_ALLOWED_USER_IDS", ""))

# Subset of ALLOWED_USER_IDS that additionally sees the Mini App's Admin tab
# (stats, user list, manual notifications) — see webapp/backend/routers/admin.py.
ADMIN_USER_IDS = _parse_id_list(os.environ.get("TELEGRAM_ADMIN_USER_IDS", ""))

# Toggle to open every gated bot command to any Telegram user, bypassing
# ALLOWED_USER_IDS entirely. Unset (or any value other than 1/true/yes/on)
# keeps the default: access stays closed to the allowlist.
PUBLIC_ACCESS = _parse_bool(os.environ.get("TELEGRAM_PUBLIC_ACCESS", ""))
