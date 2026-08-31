"""``/list``/``/view``/``/liked``/reactions — mirrors ``bot/handlers/browse.py``'s
swipe queue, full-detail view, and liked-listings browse. Unlike the bot
(one "page" is a Telegram card + inline keyboard), a queue page here is just
the current item plus the total count — the frontend renders its own card
and Prev/Next controls from that.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from bot import i18n
from src import db

from ..deps import run_db
from ..schemas import ListingCard, ListingDetail, ListingQueuePage, ReactionRequest, TelegramUser
from ..telegram_auth import get_current_telegram_user

router = APIRouter(tags=["listings"])


def _card(row: dict, language: str) -> ListingCard:
    return ListingCard(
        listing_id=row["listing_id"],
        name=row.get("name") or "",
        total_price=row.get("total_price"),
        currency=row.get("currency") or "",
        refundable_deposit=row.get("refundable_deposit"),
        area=row.get("area"),
        format=row.get("format") or "",
        fully_furnished=row.get("fully_furnished") or "",
        furnished=row.get("furnished"),
        floor_number=row.get("floor_number"),
        floor_total=row.get("floor_total"),
        floor=row.get("floor") or "",
        pets_friendly=row.get("pets_friendly"),
        location=row.get("location") or "",
        url=row.get("url") or "",
        images=row.get("images") or [],
        score=row.get("score") or 0,
        tags=i18n.amenity_tags(language, row),
    )


@router.get("/listings/queue", response_model=ListingQueuePage)
async def queue(
    offset: int = 0, user: TelegramUser = Depends(get_current_telegram_user)
) -> ListingQueuePage:
    total = await run_db(db.count_relevant_listings, user.id)
    rows = await run_db(db.fetch_relevant_listings_page, user.id, offset, 1)
    language = await run_db(db.get_user_language, user.id)
    item = _card(rows[0], language) if rows else None
    return ListingQueuePage(total=total, offset=offset, item=item)


@router.get("/liked", response_model=ListingQueuePage)
async def liked(
    offset: int = 0, user: TelegramUser = Depends(get_current_telegram_user)
) -> ListingQueuePage:
    total = await run_db(db.count_liked_listings, user.id)
    rows = await run_db(db.fetch_liked_listings_page, user.id, offset, 1)
    language = await run_db(db.get_user_language, user.id)
    item = _card(rows[0], language) if rows else None
    return ListingQueuePage(total=total, offset=offset, item=item)


@router.get("/listings/{listing_id}", response_model=ListingDetail)
async def detail(
    listing_id: str, user: TelegramUser = Depends(get_current_telegram_user)
) -> ListingDetail:
    row = await run_db(db.fetch_listing, listing_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    language = await run_db(db.get_user_language, user.id)
    row["score"] = await run_db(db.get_relevance_score, user.id, listing_id)
    description = row.get("description") or ""
    translated, translation_ok = await run_db(
        db.get_or_translate_description, listing_id, description, language
    )
    card = _card(row, language)
    return ListingDetail(
        **card.model_dump(),
        description=translated,
        translation_ok=translation_ok,
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
    )


@router.post("/listings/{listing_id}/reaction")
async def react(
    listing_id: str,
    payload: ReactionRequest,
    user: TelegramUser = Depends(get_current_telegram_user),
) -> dict:
    if payload.reaction not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="reaction must be 'like' or 'dislike'")
    await run_db(db.record_reaction, user.id, listing_id, payload.reaction)
    return {"ok": True}
