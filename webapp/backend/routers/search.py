"""Saved-search view/edit + run-now endpoints — mirrors
``bot/handlers/parser.py``'s ``/search``, ``/parse``, and ``/parse_custom``.
The Mini App is a form, not a flag string, so this calls
``src.configuration.apply_updates`` directly with the same fields
``bot/handlers/parser.py::_apply_flags_and_run`` passes, rather than going
through ``src.cli``'s argv parser.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from src import db
from src.configuration import ConfigurationError, apply_updates, load_config
from src.scheduler import run_once_for_user, user_config

from ..deps import run_db
from ..schemas import (
    SearchResponse,
    SearchUpdateRequest,
    SearchUpdateResponse,
    SyncSummary,
    TelegramUser,
)
from ..telegram_auth import get_current_telegram_user

router = APIRouter(prefix="/search", tags=["search"])


async def _new_match_count(telegram_user_id: int) -> int:
    return await run_db(db.count_unnotified_relevant_listings, telegram_user_id)


async def _queue_total(telegram_user_id: int) -> int:
    return await run_db(db.count_relevant_listings, telegram_user_id)


@router.get("", response_model=SearchResponse)
async def get_search(user: TelegramUser = Depends(get_current_telegram_user)) -> SearchResponse:
    base_config = await asyncio.to_thread(load_config)
    url = await run_db(db.get_or_seed_user_search, user.id, base_config["search"]["url"])
    return SearchResponse(url=url)


@router.post("/run", response_model=SyncSummary)
async def run_search(user: TelegramUser = Depends(get_current_telegram_user)) -> SyncSummary:
    base_config = await asyncio.to_thread(load_config)
    search_url = await run_db(db.get_or_seed_user_search, user.id, base_config["search"]["url"])
    try:
        listings, failures = await asyncio.to_thread(
            run_once_for_user, user.id, search_url, base_config
        )
    except (ConfigurationError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    new_count = await _new_match_count(user.id)
    queue_total = await _queue_total(user.id)
    return SyncSummary(
        synced=len(listings), failures=len(failures), new_count=new_count, queue_total=queue_total
    )


@router.post("", response_model=SearchUpdateResponse)
async def update_search(
    payload: SearchUpdateRequest, user: TelegramUser = Depends(get_current_telegram_user)
) -> SearchUpdateResponse:
    base_config = await asyncio.to_thread(load_config)
    current_url = await run_db(db.get_or_seed_user_search, user.id, base_config["search"]["url"])
    try:
        updated = apply_updates(
            user_config(base_config, current_url),
            url=payload.url,
            price_from=payload.price_from,
            price_to=payload.price_to,
            delay=payload.delay,
            timeout=payload.timeout,
            max_retries=payload.max_retries,
        )
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    new_url = updated["search"]["url"]
    await run_db(db.set_user_search, user.id, new_url)
    try:
        listings, failures = await asyncio.to_thread(run_once_for_user, user.id, new_url, base_config)
    except (ConfigurationError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    new_count = await _new_match_count(user.id)
    queue_total = await _queue_total(user.id)
    return SearchUpdateResponse(
        new_url=new_url,
        synced=len(listings),
        failures=len(failures),
        new_count=new_count,
        queue_total=queue_total,
    )
