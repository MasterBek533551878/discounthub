from datetime import datetime
from typing import Literal
from pydantic import Field

from app.models.common import ApiModel
from app.models.deal import DealMonetizationMode


PromotionType = Literal[
    "coupon",
    "sale",
    "flash_sale",
]

PromotionSort = Literal[
    "featured",
    "ending_soon",
    "newest",
]


class Promotion(ApiModel):
    id: str
    type: PromotionType = "sale"
    title: str
    description: str = ""
    store: str
    discount_text: str = ""
    code: str | None = None
    landing_url: str
    affiliate_url: str | None = None
    image_url: str | None = None
    provider_id: str | None = None
    monetization_mode: DealMonetizationMode = "affiliate"
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    updated_at: datetime


class PromotionResponse(ApiModel):
    id: str
    type: PromotionType
    title: str
    description: str
    store: str
    discount_text: str
    code: str | None = None
    landing_url: str
    affiliate_url: str | None = None
    image_url: str | None = None
    provider_id: str | None = None
    monetization_mode: DealMonetizationMode = "affiliate"
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    updated_at: datetime


class PromotionsPage(ApiModel):
    items: list[PromotionResponse]
    total: int
    page: int
    page_size: int
    has_next_page: bool


class PromotionUpsertRequest(ApiModel):
    id: str
    type: PromotionType = "sale"
    title: str = Field(min_length=1)
    description: str = ""
    store: str = Field(min_length=1)
    discount_text: str = ""
    code: str | None = None
    landing_url: str = Field(min_length=1)
    affiliate_url: str | None = None
    image_url: str | None = None
    provider_id: str | None = None
    monetization_mode: DealMonetizationMode | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    updated_at: datetime | None = None


class PromotionCleanupResponse(ApiModel):
    status: str
    message: str
    checked_count: int = 0
    deleted_count: int = 0
    remaining_count: int = 0
    deleted_reasons: dict[str, int] = Field(default_factory=dict)

class AwinPromotionSyncRequest(ApiModel):
    membership: Literal["joined", "notJoined", "all"] = "joined"
    status: Literal["active", "expiringSoon", "upcoming"] = "active"
    type: Literal["promotion", "voucher", "all"] = "all"
    page_size: int = Field(default=100, ge=10, le=200)
    max_pages: int = Field(default=5, ge=1, le=50)
    advertiser_ids: list[int] | None = None
    region_codes: list[str] | None = None
    exclusive_only: bool | None = None
    updated_since: str | None = None


class AwinPromotionSyncResponse(ApiModel):
    status: str
    message: str
    fetched_count: int
    imported_count: int
    total_before: int
    total_after: int
    skipped_count: int = 0
    pages_checked: int = 0
    cleanup_deleted_count: int = 0
    cleanup_deleted_reasons: dict[str, int] = Field(default_factory=dict)
