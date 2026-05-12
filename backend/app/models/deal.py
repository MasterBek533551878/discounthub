from datetime import datetime
from typing import Literal
from pydantic import Field

from app.models.common import ApiModel
from app.models.feed_provider import FeedProviderAdapter


DealSort = Literal[
    "score_desc",
    "discount_desc",
    "price_asc",
    "price_desc",
    "rating_desc",
    "newest",
]


class Deal(ApiModel):
    id: str
    title: str
    description: str
    image_url: str
    platform: str
    category: str
    old_price: float
    current_price: float
    currency: str = "USD"
    product_url: str
    affiliate_url: str | None = None
    rating: float = Field(ge=0, le=5)
    review_count: int = 0
    free_shipping: bool = False
    verified: bool = False
    ships_to: list[str] = Field(default_factory=list)
    hot_deal: bool = False
    lowest_price: bool = False
    deal_score: int = Field(default=0, ge=0, le=100)
    updated_at: datetime
    expires_at: datetime | None = None

    @property
    def discount_percent(self) -> int:
        if self.old_price <= 0:
            return 0
        return round(((self.old_price - self.current_price) / self.old_price) * 100)


class DealResponse(ApiModel):
    id: str
    title: str
    description: str
    image_url: str
    platform: str
    category: str
    old_price: float
    current_price: float
    currency: str
    product_url: str
    affiliate_url: str | None = None
    rating: float
    review_count: int
    free_shipping: bool
    verified: bool
    ships_to: list[str]
    hot_deal: bool
    lowest_price: bool
    deal_score: int
    discount_percent: int
    updated_at: datetime
    expires_at: datetime | None = None


class DealsPage(ApiModel):
    items: list[DealResponse]
    total: int
    page: int
    page_size: int
    has_next_page: bool


class DealUpsertRequest(ApiModel):
    id: str
    title: str
    description: str
    image_url: str
    platform: str
    category: str
    old_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    currency: str = "USD"
    product_url: str
    affiliate_url: str | None = None
    rating: float = Field(default=0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    free_shipping: bool = False
    verified: bool = False
    ships_to: list[str] = Field(default_factory=list)
    hot_deal: bool = False
    lowest_price: bool = False
    deal_score: int | None = Field(default=None, ge=0, le=100)
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class BulkDealUpsertRequest(ApiModel):
    items: list[DealUpsertRequest]


class DealsImportRequest(ApiModel):
    items: list[DealUpsertRequest]
    replace: bool = False


class DealsImportUrlRequest(ApiModel):
    url: str
    adapter: FeedProviderAdapter = "auto"
    replace: bool = False
    timeout_seconds: int = Field(default=20, ge=3, le=60)


class DealsExportResponse(ApiModel):
    status: str
    exported_at: datetime
    total: int
    items: list[DealUpsertRequest]


class AdminActionResponse(ApiModel):
    status: str
    message: str
    deal_count: int | None = None


class RatesResponse(ApiModel):
    base_currency: str
    rates: dict[str, float]
    note: str
