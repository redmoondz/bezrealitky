"""Pydantic request/response models for the Mini App's JSON API."""

from __future__ import annotations

from pydantic import BaseModel


class TelegramUser(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    is_premium: bool = False


class MeResponse(BaseModel):
    id: int
    language: str
    has_search: bool


class LanguageOption(BaseModel):
    code: str
    label: str


class SetLanguageRequest(BaseModel):
    code: str


class SearchUrlRequest(BaseModel):
    url: str | None = None


class PreferencesRequest(BaseModel):
    """Every field is optional and only applied if present in the request body
    — mirrors the bot onboarding's independently-skippable pets/budget/area
    questions (a field the client omits is left untouched, same as a "Skip").
    """

    wants_pets: bool | None = None
    budget_total_price: float | None = None
    min_area_m2: float | None = None


class SyncSummary(BaseModel):
    synced: int
    failures: int
    new_count: int


class SearchUpdateRequest(BaseModel):
    url: str | None = None
    price_from: int | None = None
    price_to: int | None = None
    delay: float | None = None
    timeout: float | None = None
    max_retries: int | None = None


class SearchUpdateResponse(SyncSummary):
    new_url: str


class SearchResponse(BaseModel):
    url: str


class ListingCard(BaseModel):
    listing_id: str
    name: str = ""
    total_price: float | None = None
    currency: str = ""
    refundable_deposit: float | None = None
    area: float | None = None
    format: str = ""
    fully_furnished: str = ""
    floor_number: int | None = None
    floor_total: int | None = None
    floor: str = ""
    pets_friendly: bool | None = None
    location: str = ""
    url: str = ""
    images: list[str] = []
    score: int = 0
    tags: list[str] = []


class ListingQueuePage(BaseModel):
    total: int
    offset: int
    item: ListingCard | None = None


class ListingDetail(ListingCard):
    description: str = ""
    translation_ok: bool = True
    latitude: float | None = None
    longitude: float | None = None


class ReactionRequest(BaseModel):
    reaction: str  # "like" | "dislike"


class ChartOption(BaseModel):
    key: str
    label: str


class ChartDataResponse(BaseModel):
    key: str
    label: str
    kind: str  # "histogram" | "scatter" | "pie"
    data: dict


class HelpResponse(BaseModel):
    text: str
