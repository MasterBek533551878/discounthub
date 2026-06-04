from datetime import datetime
from typing import Literal
from pydantic import Field, field_validator

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

DealMonetizationMode = Literal[
    "affiliate",
    "direct",
    "pending_affiliate",
]

DealDeliveryRegion = Literal[
    "global",
    "cis",
    "europe",
    "usa",
    "latam",
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
    provider_id: str | None = None
    monetization_mode: DealMonetizationMode = "direct"
    rating: float = Field(ge=0, le=5)
    review_count: int = 0
    free_shipping: bool = False
    verified: bool = False
    ships_to: list[str] = Field(default_factory=list)
    delivery_regions: list[DealDeliveryRegion] = Field(default_factory=list)
    hot_deal: bool = False
    lowest_price: bool = False
    deal_score: int = Field(default=0, ge=0, le=100)
    updated_at: datetime
    expires_at: datetime | None = None

    @property
    def discount_percent(self) -> int:
        if self.old_price <= 0 or self.current_price <= 0 or self.old_price <= self.current_price:
            return 0
        percent = round(((self.old_price - self.current_price) / self.old_price) * 100)
        if percent < 1:
            return 0
        return min(percent, 100)


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
    provider_id: str | None = None
    monetization_mode: DealMonetizationMode = "direct"
    rating: float
    review_count: int
    free_shipping: bool
    verified: bool
    ships_to: list[str]
    delivery_regions: list[DealDeliveryRegion]
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


class DealFacetItem(ApiModel):
    id: str
    name: str
    count: int


class DealPriceRange(ApiModel):
    min: float | None = None
    max: float | None = None
    currency: str = "USD"


class DealDiscountRange(ApiModel):
    min: int | None = None
    max: int | None = None


class DealsFacetsResponse(ApiModel):
    total: int
    marketplaces: list[DealFacetItem]
    categories: list[DealFacetItem]
    shipping_countries: list[DealFacetItem]
    delivery_regions: list[DealFacetItem]
    currencies: list[DealFacetItem]
    monetization_modes: list[DealFacetItem]
    price_range: DealPriceRange
    discount_range: DealDiscountRange
    generated_at: datetime


class DealUpsertRequest(ApiModel):
    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, value: object) -> float:
        """Accept merchant/feed ratings in 0-5, 0-10, or 0-100 formats.

        Some affiliate feeds, especially Awin product feeds, use `rating` as a
        percentage (80, 95, 100) instead of a 0-5 star value. The public API and
        Flutter filters expect 0-5, so normalize before Pydantic range checks.
        """
        if value is None or value == "":
            return 0
        try:
            if isinstance(value, str):
                cleaned = value.strip().replace("%", "").replace(",", ".")
                rating = float(cleaned)
            else:
                rating = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

        if rating < 0:
            return 0
        if rating <= 5:
            return round(rating, 2)
        if rating <= 10:
            return round(rating / 2, 2)
        if rating <= 100:
            return round(rating / 20, 2)
        return 5

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
    provider_id: str | None = None
    # None means: infer from affiliate_url. Existing feed adapters do not need to change.
    monetization_mode: DealMonetizationMode | None = None
    rating: float = Field(default=0, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    free_shipping: bool = False
    verified: bool = False
    ships_to: list[str] = Field(default_factory=list)
    delivery_regions: list[DealDeliveryRegion] = Field(default_factory=list)
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
    timeout_seconds: int = Field(default=20, ge=3, le=300)


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
