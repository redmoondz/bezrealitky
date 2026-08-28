"""``/api/charts`` — mirrors ``bot/handlers/charts.py``'s ``/charts`` menu,
serving JSON (for interactive client-side charts) instead of matplotlib PNGs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src import db

from ..chart_data import CHART_DATA_BUILDERS, CHART_KINDS, CHART_LABELS
from ..deps import run_db
from ..schemas import ChartDataResponse, ChartOption, TelegramUser
from ..telegram_auth import get_current_telegram_user

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("", response_model=list[ChartOption])
async def list_charts(
    _: TelegramUser = Depends(get_current_telegram_user),
) -> list[ChartOption]:
    return [ChartOption(key=key, label=label) for key, label in CHART_LABELS.items()]


@router.get("/{key}/data", response_model=ChartDataResponse)
async def chart_data(
    key: str, user: TelegramUser = Depends(get_current_telegram_user)
) -> ChartDataResponse:
    builder = CHART_DATA_BUILDERS.get(key)
    if builder is None:
        raise HTTPException(status_code=404, detail="Unknown chart")
    rows = await run_db(db.fetch_relevant_listings, user.id)
    return ChartDataResponse(key=key, label=CHART_LABELS[key], kind=CHART_KINDS[key], data=builder(rows))
