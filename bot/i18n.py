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

# Emoji is the actual color-coding here — Telegram's HTML/MarkdownV2 parse modes
# have no colored-text feature, so a distinct emoji per amenity is the only
# per-tag visual distinction the message text can actually carry.
_AMENITY_EMOJI = {
    "air_conditioning": "❄️",
    "has_washing_machine": "🧺",
    "has_dryer": "🌀",
    "has_internet": "📶",
    "has_dishwasher": "🍽",
    "mansard": "🔺",
}

_AMENITY_LABELS = {
    "air_conditioning": {
        "en": "AC",
        "cs": "Klimatizace",
        "ru": "Кондиционер",
        "uk": "Кондиціонер",
    },
    "has_washing_machine": {
        "en": "Washer",
        "cs": "Pračka",
        "ru": "Стиральная машина",
        "uk": "Пральна машина",
    },
    "has_dryer": {
        "en": "Dryer",
        "cs": "Sušička",
        "ru": "Сушильная машина",
        "uk": "Сушильна машина",
    },
    "has_internet": {
        "en": "Internet",
        "cs": "Internet",
        "ru": "Интернет",
        "uk": "Інтернет",
    },
    "has_dishwasher": {
        "en": "Dishwasher",
        "cs": "Myčka",
        "ru": "Посудомоечная машина",
        "uk": "Посудомийна машина",
    },
    "mansard": {
        "en": "Attic/mansard",
        "cs": "Podkroví",
        "ru": "Мансарда",
        "uk": "Мансарда",
    },
}


def amenity_tags(language: str, row: dict) -> list[str]:
    """Emoji+label tags for every amenity confirmed present (``True``) on ``row``.

    Amenities that are absent or unknown are left out entirely, the same way a
    listing's own feature list only ever mentions what's there.
    """
    tags = []
    for field, emoji in _AMENITY_EMOJI.items():
        if row.get(field) is True:
            labels = _AMENITY_LABELS[field]
            tags.append(f"{emoji} {labels.get(language, labels[_DEFAULT_LANGUAGE])}")
    return tags


def batch_summary_text(language: str, count: int) -> str:
    template = _BATCH_SUMMARY.get(language, _BATCH_SUMMARY[_DEFAULT_LANGUAGE])
    return template.format(count=count)


def browse_button_label(language: str) -> str:
    return _BROWSE_BUTTON.get(language, _BROWSE_BUTTON[_DEFAULT_LANGUAGE])


def charts_button_label(language: str) -> str:
    return _CHARTS_BUTTON.get(language, _CHARTS_BUTTON[_DEFAULT_LANGUAGE])
