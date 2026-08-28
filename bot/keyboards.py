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


def pets_preference_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🐾 Yes", callback_data="pets_pref:yes"),
                InlineKeyboardButton(text="🚫 No", callback_data="pets_pref:no"),
            ],
            [InlineKeyboardButton(text="⏭ Skip", callback_data="pets_pref:skip")],
        ]
    )


def skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭ Skip", callback_data=callback_data)]]
    )


def reaction_keyboard(listing_id: str, offset: int, prefix: str = "react") -> InlineKeyboardMarkup:
    """A standalone Like/Dislike row — used both as /list's swipe-card row (via
    :func:`listing_keyboard`, ``prefix="react"``) and on its own on the /view
    detail card (``prefix="reactd"``, since that's a distinct callback so its
    handler knows to hand back into the /list queue afterwards instead of
    editing a swipe card).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👎 Pass", callback_data=f"{prefix}:dislike:{offset}:{listing_id}"
                ),
                InlineKeyboardButton(
                    text="❤️ Like", callback_data=f"{prefix}:like:{offset}:{listing_id}"
                ),
            ]
        ]
    )


def listing_keyboard(
    listing_id: str,
    url: str,
    offset: int,
    total: int,
    nav_prefix: str = "page",
    show_reactions: bool = True,
) -> InlineKeyboardMarkup:
    """``nav_prefix`` namespaces Prev/Next callback data so /list's pager
    (``page:``) and /liked's pager (``likedpage:``) never collide.
    ``show_reactions`` adds the Like/Dislike row for the /list swipe queue;
    /liked omits it since un-liking isn't supported yet.
    """
    nav_row = []
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="◂ Prev", callback_data=f"{nav_prefix}:{max(0, offset - PAGE_SIZE)}"
            )
        )
    if offset + PAGE_SIZE < total:
        nav_row.append(
            InlineKeyboardButton(text="Next ▸", callback_data=f"{nav_prefix}:{offset + PAGE_SIZE}")
        )
    rows = []
    if nav_row:
        rows.append(nav_row)
    if show_reactions:
        rows.append(reaction_keyboard(listing_id, offset).inline_keyboard[0])
    rows.append(
        [
            InlineKeyboardButton(
                text="Full details & photos", callback_data=f"view:{offset}:{listing_id}"
            ),
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
