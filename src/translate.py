"""Free, self-hosted translation for listing descriptions via LibreTranslate.

Descriptions on Bezrealitky are usually Czech but not always — some are written
directly in English — so the source language is auto-detected per description
rather than assumed, letting each Telegram user read them in whichever language
they picked with /start or /language, without depending on a paid translation API.

Lives in ``src`` (not ``bot``) because the scheduler now pre-translates and
caches descriptions at scrape time too (see ``db.get_or_translate_description``),
not just the bot process — this module has no Telegram-specific dependencies.
"""

from __future__ import annotations

import logging
import os
import time

import requests

LOGGER = logging.getLogger(__name__)

TRANSLATE_URL = os.environ.get("TRANSLATE_URL", "http://translate:5000/translate")

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

# Bezrealitky is a Czech site; almost every description that isn't in English
# is Czech — but occasionally Slovak (close enough to Czech to read, distinct
# enough to trip up language ID). LibreTranslate's auto-detect sometimes scores
# such text as English with ~0 confidence, then "translates" it by echoing it
# straight back untranslated. Falling back to this assumed source lets the
# (very similar) Czech model produce a real translation instead.
_FALLBACK_SOURCE = "cs"


def _request(text: str, target_language: str, source: str) -> tuple[str | None, str | None]:
    """One LibreTranslate call. Returns ``(translated_text, detected_language)``,
    either of which may be ``None`` if the response didn't include it. Network
    and HTTP errors propagate to the caller's retry loop.
    """
    response = requests.post(
        TRANSLATE_URL,
        json={"q": text, "source": source, "target": target_language, "format": "text"},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    translated = body.get("translatedText")
    detected = (body.get("detectedLanguage") or {}).get("language")
    return (translated if isinstance(translated, str) else None), detected


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
            translated, detected = _request(text, target_language, source="auto")
            if not translated:
                return text, True
            if translated.strip() == text.strip() and detected != target_language:
                # Auto-detect likely misread the source and the model just
                # echoed the input back rather than translating it — a real
                # "already in the target language" case would have detected
                # as target_language above, so this is worth one retry.
                retried, _ = _request(text, target_language, source=_FALLBACK_SOURCE)
                if retried and retried.strip() != text.strip():
                    return retried, True
                return text, False
            return translated, True
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
