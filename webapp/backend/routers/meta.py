"""``/api/me``, ``/api/languages``, ``/api/language``, ``/api/help`` — account
probe, language list/selection, and static help content. Mirrors
``bot/handlers/start.py``'s ``/language`` and ``/help``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from bot import config as bot_config
from src import db

from ..deps import run_db
from ..schemas import HelpResponse, LanguageOption, MeResponse, SetLanguageRequest, TelegramUser
from ..telegram_auth import get_current_telegram_user

router = APIRouter(tags=["meta"])

HELP_TEXT = (
    "Bezrealitky listings — Mini App\n\n"
    "Browse — swipe through listings matching your saved search (like/pass).\n"
    "Liked — the listings you've liked.\n"
    "Search — view or edit your saved search, and run it now.\n"
    "Charts — distributions for your saved search.\n\n"
    "Everyone has their own independent saved search. New matches found here "
    "are the same ones the bot would notify you about in chat.\n\n"
    "Questions or feedback? Write to redmoo.rsv@gmail.com anytime."
)


@router.get("/me", response_model=MeResponse)
async def me(user: TelegramUser = Depends(get_current_telegram_user)) -> MeResponse:
    language = await run_db(db.get_user_language, user.id)
    search_url = await run_db(db.get_user_search, user.id)
    return MeResponse(
        id=user.id,
        language=language,
        has_search=search_url is not None,
        is_admin=user.id in bot_config.ADMIN_USER_IDS,
    )


@router.get("/languages", response_model=list[LanguageOption])
async def languages(
    _: TelegramUser = Depends(get_current_telegram_user),
) -> list[LanguageOption]:
    return [LanguageOption(code=code, label=label) for code, label in bot_config.SUPPORTED_LANGUAGES]


@router.post("/language")
async def set_language(
    payload: SetLanguageRequest, user: TelegramUser = Depends(get_current_telegram_user)
) -> dict:
    if payload.code not in bot_config.SUPPORTED_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Unknown language")
    await run_db(db.set_user_language, user.id, payload.code)
    return {"ok": True}


@router.get("/help", response_model=HelpResponse)
async def help_text(_: TelegramUser = Depends(get_current_telegram_user)) -> HelpResponse:
    return HelpResponse(text=HELP_TEXT)
