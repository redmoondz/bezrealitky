"""Fixed UI copy translated per language, for the handful of strings where
correct grammar (word order, pluralization) matters more than raw content —
unlike listing descriptions, which go through live machine translation in
``translate.py``. Covers exactly ``config.SUPPORTED_LANGUAGE_CODES``; any other
code falls back to English.
"""

from __future__ import annotations

_DEFAULT_LANGUAGE = "en"

_BATCH_SUMMARY = {
    "en": "👋 <b>Hi!</b> Your saved search is ready.\n\nFound <b>{count}</b> listings for you.",
    "cs": "👋 <b>Ahoj!</b> Váš uložený požadavek je připraven.\n\nNalezeno inzerátů: <b>{count}</b>.",
    "ru": "👋 <b>Привет!</b> Ваш сохранённый поиск готов.\n\nНайдено объявлений: <b>{count}</b>.",
    "uk": "👋 <b>Привіт!</b> Ваш збережений пошук готовий.\n\nЗнайдено оголошень: <b>{count}</b>.",
}

_BROWSE_BUTTON = {
    "en": "📋 Browse listings",
    "cs": "📋 Procházet inzeráty",
    "ru": "📋 Смотреть объявления",
    "uk": "📋 Переглянути оголошення",
}

_CHARTS_BUTTON = {
    "en": "📊 Charts",
    "cs": "📊 Grafy",
    "ru": "📊 Графики",
    "uk": "📊 Графіки",
}


def batch_summary_text(language: str, count: int) -> str:
    template = _BATCH_SUMMARY.get(language, _BATCH_SUMMARY[_DEFAULT_LANGUAGE])
    return template.format(count=count)


def browse_button_label(language: str) -> str:
    return _BROWSE_BUTTON.get(language, _BROWSE_BUTTON[_DEFAULT_LANGUAGE])


def charts_button_label(language: str) -> str:
    return _CHARTS_BUTTON.get(language, _CHARTS_BUTTON[_DEFAULT_LANGUAGE])
