"""``/api/admin/*`` — stats, user list, and manual notifications.

Every endpoint here requires the caller's Telegram ID to be in
``TELEGRAM_ADMIN_USER_IDS``, a narrower allowlist than the
``TELEGRAM_ALLOWED_USER_IDS`` every other endpoint enforces — see
``get_current_admin_user``.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from src import db

from ..deps import run_db
from ..schemas import AdminNotifyRequest, AdminNotifyResponse, AdminStats, AdminUser, TelegramUser
from ..telegram_auth import get_current_admin_user
from ..telegram_send import send_message

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats(_: TelegramUser = Depends(get_current_admin_user)) -> AdminStats:
    return AdminStats(**await run_db(db.admin_stats))


@router.get("/users", response_model=list[AdminUser])
async def users(_: TelegramUser = Depends(get_current_admin_user)) -> list[AdminUser]:
    rows = await run_db(db.admin_list_users)
    return [AdminUser(**row) for row in rows]


@router.post("/notify", response_model=AdminNotifyResponse)
async def notify(
    payload: AdminNotifyRequest, _: TelegramUser = Depends(get_current_admin_user)
) -> AdminNotifyResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text is required")
    if payload.scope == "user":
        if payload.user_id is None:
            raise HTTPException(status_code=400, detail="user_id is required for scope=user")
        targets = [payload.user_id]
    else:
        targets = await run_db(db.list_registered_users)
    if not targets:
        return AdminNotifyResponse(sent=0, failed=0)
    results = await asyncio.gather(*(asyncio.to_thread(send_message, target, text) for target in targets))
    sent = sum(1 for ok in results if ok)
    return AdminNotifyResponse(sent=sent, failed=len(results) - sent)
