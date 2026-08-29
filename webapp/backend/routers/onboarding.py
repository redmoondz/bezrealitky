"""Onboarding endpoints — mirrors ``bot/handlers/start.py``'s ``Onboarding``
FSM (language is handled by ``routers/meta.py``; this covers the saved-search
URL-or-default step and the pets/budget/area preference steps). Each step is
independently skippable, same as the bot: the frontend wizard calls each
endpoint once per step and simply omits a field to mean "skip", rather than
the bot's server-side FSM state.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from src import db
from src.configuration import ConfigurationError, load_config, validate_search_url
from src.scheduler import run_once_for_user

from ..deps import run_db
from ..schemas import PreferencesRequest, SearchUrlRequest, SyncSummary, TelegramUser
from ..telegram_auth import get_current_telegram_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_PREFERENCE_FIELDS = ("wants_pets", "budget_total_price", "min_area_m2")


@router.post("/search-url")
async def set_search_url(
    payload: SearchUrlRequest, user: TelegramUser = Depends(get_current_telegram_user)
) -> dict:
    if payload.url:
        try:
            search_url = validate_search_url(payload.url)
        except ConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        base_config = await asyncio.to_thread(load_config)
        search_url = base_config["search"]["url"]
    await run_db(db.set_user_search, user.id, search_url)
    return {"search_url": search_url}


@router.post("/preferences")
async def set_preferences(
    payload: PreferencesRequest, user: TelegramUser = Depends(get_current_telegram_user)
) -> dict:
    provided = payload.model_dump(exclude_unset=True)
    for column in _PREFERENCE_FIELDS:
        if column in provided:
            await run_db(db.set_user_preference, user.id, column, provided[column])
    return {"ok": True}


@router.post("/reset")
async def reset(user: TelegramUser = Depends(get_current_telegram_user)) -> dict:
    """Clear the saved search and preferences so the wizard (``Onboarding.tsx``)
    can be run again from scratch — the Mini App's counterpart to the bot's
    ``/onboarding`` command.
    """
    await run_db(db.reset_user_onboarding, user.id)
    return {"ok": True}


@router.post("/finish", response_model=SyncSummary)
async def finish(user: TelegramUser = Depends(get_current_telegram_user)) -> SyncSummary:
    base_config = await asyncio.to_thread(load_config)
    search_url = await run_db(db.get_or_seed_user_search, user.id, base_config["search"]["url"])
    try:
        listings, failures = await asyncio.to_thread(
            run_once_for_user, user.id, search_url, base_config
        )
    except (ConfigurationError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    new_count = await run_db(db.count_unnotified_relevant_listings, user.id)
    queue_total = await run_db(db.count_relevant_listings, user.id)
    return SyncSummary(
        synced=len(listings), failures=len(failures), new_count=new_count, queue_total=queue_total
    )
