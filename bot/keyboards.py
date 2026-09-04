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


def offer_type_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t("offer_type_rent_button", language), callback_data="offer_type:PRONAJEM"),
                InlineKeyboardButton(text=i18n.t("offer_type_buy_button", language), callback_data="offer_type:PRODEJ"),
            ]
        ]
    )


def estate_type_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t("estate_type_apartment_button", language), callback_data="estate_type:BYT"),
                InlineKeyboardButton(text=i18n.t("estate_type_house_button", language), callback_data="estate_type:DUM"),
            ],
            [
                InlineKeyboardButton(text=i18n.t("estate_type_land_button", language), callback_data="estate_type:POZEMEK"),
                InlineKeyboardButton(text=i18n.t("estate_type_garage_button", language), callback_data="estate_type:GARAZ"),
            ],
        ]
    )


def currency_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="CZK", callback_data="currency:CZK"),
                InlineKeyboardButton(text="EUR", callback_data="currency:EUR"),
            ]
        ]
    )


def location_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t("whole_country_button", language), callback_data="location_pref:skip")]
        ]
    )


def pets_preference_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t("pets_yes_button", language), callback_data="pets_pref:yes"),
                InlineKeyboardButton(text=i18n.t("pets_no_button", language), callback_data="pets_pref:no"),
            ],
            [InlineKeyboardButton(text=i18n.t("skip_button", language), callback_data="pets_pref:skip")],
        ]
    )


def furniture_preference_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.t("furniture_yes_button", language), callback_data="furniture_pref:yes"
                ),
                InlineKeyboardButton(
                    text=i18n.t("furniture_no_button", language), callback_data="furniture_pref:no"
                ),
            ],
            [InlineKeyboardButton(text=i18n.t("skip_button", language), callback_data="furniture_pref:skip")],
        ]
    )


def skip_keyboard(callback_data: str, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.t("skip_button", language), callback_data=callback_data)]]
    )


def reaction_keyboard(listing_id: str, offset: int, language: str, prefix: str = "react") -> InlineKeyboardMarkup:
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
                    text=i18n.t("pass_button", language), callback_data=f"{prefix}:dislike:{offset}:{listing_id}"
                ),
                InlineKeyboardButton(
                    text=i18n.t("like_button", language), callback_data=f"{prefix}:like:{offset}:{listing_id}"
                ),
            ]
        ]
    )


def listing_keyboard(
    listing_id: str,
    url: str,
    offset: int,
    total: int,
    language: str,
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
                text=i18n.t("prev_button", language), callback_data=f"{nav_prefix}:{max(0, offset - PAGE_SIZE)}"
            )
        )
    if offset + PAGE_SIZE < total:
        nav_row.append(
            InlineKeyboardButton(
                text=i18n.t("next_button", language), callback_data=f"{nav_prefix}:{offset + PAGE_SIZE}"
            )
        )
    rows = []
    if nav_row:
        rows.append(nav_row)
    if show_reactions:
        rows.append(reaction_keyboard(listing_id, offset, language).inline_keyboard[0])
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.t("full_details_button", language), callback_data=f"view:{offset}:{listing_id}"
            ),
            InlineKeyboardButton(text=i18n.t("open_listing_button", language), url=url),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def charts_keyboard(language: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"chart:{key}")]
        for key, label in i18n.chart_options(language)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
