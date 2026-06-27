from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import ApiModel
from app.models.deal import DealMonetizationMode


PartnerOfferSort = Literal[
    "featured",
    "ending_soon",
    "newest",
]


class PartnerOffer(ApiModel):
    id: str
    title: str
    subtitle: str = ""
    description: str = ""
    partner_name: str
    category: str = "other"
    tags: list[str] = Field(default_factory=list)
    offer_text: str = ""
    original_price_text: str = ""
    current_price_text: str = ""
    code: str | None = None
    landing_url: str
    checkout_url: str | None = None
    image_url: str | None = None
    logo_url: str | None = None
    countries: str = "Global"
    monetization_mode: DealMonetizationMode = "direct"
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    verified: bool = False
    updated_at: datetime


class PartnerOfferResponse(ApiModel):
    id: str
    title: str
    subtitle: str
    description: str
    partner_name: str
    category: str
    tags: list[str]
    offer_text: str
    original_price_text: str
    current_price_text: str
    code: str | None = None
    landing_url: str
    checkout_url: str | None = None
    image_url: str | None = None
    logo_url: str | None = None
    countries: str
    monetization_mode: DealMonetizationMode = "direct"
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    verified: bool = False
    updated_at: datetime


class PartnerOffersPage(ApiModel):
    items: list[PartnerOfferResponse]
    total: int
    page: int
    page_size: int
    has_next_page: bool


class PartnerOfferUpsertRequest(ApiModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    subtitle: str = ""
    description: str = ""
    partner_name: str = Field(min_length=1)
    category: str = "other"
    tags: list[str] = Field(default_factory=list)
    offer_text: str = ""
    original_price_text: str = ""
    current_price_text: str = ""
    code: str | None = None
    landing_url: str = Field(min_length=1)
    checkout_url: str | None = None
    image_url: str | None = None
    logo_url: str | None = None
    countries: str = "Global"
    monetization_mode: DealMonetizationMode | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    featured: bool = False
    verified: bool = False
    updated_at: datetime | None = None


class BulkPartnerOfferUpsertRequest(ApiModel):
    items: list[PartnerOfferUpsertRequest] = Field(default_factory=list)


class PartnerOfferActionResponse(ApiModel):
    status: str
    message: str
    offer_count: int = 0
