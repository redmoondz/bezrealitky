"""Free, self-hosted translation for listing descriptions via LibreTranslate.

Descriptions on Bezrealitky are usually Czech but not always — some are written
directly in English — so the source language is auto-detected per description
rather than assumed, letting each Telegram user read them in whichever language
they picked with /start or /language, without depending on a paid translation API.
"""

from __future__ import annotations

import logging

import requests

from . import config

LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


def translate_description(text: str, target_language: str) -> str:
    """Translate text, falling back to the original on any failure.

    A translation-service hiccup (container still warming up, timeout, unexpected
    response) must never break browsing or notifications — the original text is
    always an acceptable result. Source language is "auto": translating text
    that's already in the target language is a safe, near-identity no-op for
    LibreTranslate, so there's no need to detect first and compare.
    """
    if not text:
        return text
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
        return translated if isinstance(translated, str) and translated else text
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Translation failed, showing the original text: %s", exc)
        return text
