"""Inline keyboards shared by the bot's handlers."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from . import config, i18n

PAGE_SIZE = 1


def batch_summary_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.browse_button_label(language), callback_data="menu:browse"),
                InlineKeyboardButton(text=i18n.charts_button_label(language), callback_data="menu:charts"),
            ]
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
        for code, name in config.SUPPORTED_LANGUAGES
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def onboarding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Use the default search", callback_data="onboarding:skip")]
        ]
    )


def listing_keyboard(listing_id: str, url: str, offset: int, total: int) -> InlineKeyboardMarkup:
    nav_row = []
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(text="◂ Prev", callback_data=f"page:{max(0, offset - PAGE_SIZE)}")
        )
    if offset + PAGE_SIZE < total:
        nav_row.append(
            InlineKeyboardButton(text="Next ▸", callback_data=f"page:{offset + PAGE_SIZE}")
        )
    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(
        [
            InlineKeyboardButton(text="Full details & photos", callback_data=f"view:{listing_id}"),
            InlineKeyboardButton(text="Open listing", url=url),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


CHART_OPTIONS = [
    ("area_hist", "Area distribution"),
    ("price_hist", "Price distribution"),
    ("price_per_unit_hist", "Price per m² distribution"),
    ("price_vs_area", "Price vs. area"),
    ("format_pie", "By layout"),
    ("pets_pie", "By pets_friendly"),
]


def charts_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"chart:{key}")]
        for key, label in CHART_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
