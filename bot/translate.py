"""Free, self-hosted translation for listing descriptions via LibreTranslate.

Descriptions on Bezrealitky are usually Czech but not always — some are written
directly in English — so the source language is auto-detected per description
rather than assumed, letting each Telegram user read them in whichever language
they picked with /start or /language, without depending on a paid translation API.
"""

from __future__ import annotations

import logging
import time

import requests

from . import config

LOGGER = logging.getLogger(__name__)

# LibreTranslate runs CPU-only inference behind a small, fixed worker pool
# (see compose.yaml) — a single request can genuinely take longer than the
# old 10s cap under concurrent load (a scrape's notification batch, several
# users browsing at once), which was silently swallowed as "translation
# failed" and shown as untranslated Czech with no indication anything went
# wrong. A longer timeout plus one retry fixes most of those; the remaining
# rare failures are now reported back to the caller instead of hidden.
_TIMEOUT_SECONDS = 25
_MAX_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 1.5


def translate_description(text: str, target_language: str) -> tuple[str, bool]:
    """Translate text. Returns ``(text_to_show, translation_succeeded)``.

    On failure, ``text_to_show`` is the original (untranslated) text — browsing
    or notifications must never break over a translation-service hiccup — but
    callers now get an explicit ``False`` so they can tell the user why they're
    seeing the original language instead of silently mislabeling it.
    """
    if not text:
        return text, True

    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = requests.post(
                config.TRANSLATE_URL,
                json={
                    "q": text,
                    "source": "auto",
                    "target": target_language,
                    "format": "text",
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            translated = response.json().get("translatedText")
            return (translated, True) if isinstance(translated, str) and translated else (text, True)
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY_SECONDS)

    LOGGER.warning(
        "Translation failed after %d attempt(s), showing the original text: %s",
        _MAX_ATTEMPTS,
        last_exc,
    )
    return text, False
