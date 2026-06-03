from datetime import datetime
from typing import Literal

from pydantic import Field


# Keep feed provider adapters as plain strings at the API/storage boundary.
# Older local databases may contain legacy/experimental adapter ids such as
# "awin_feed_list_api". Listing providers must never crash because of those
# rows; unsupported adapters are rejected during sync by the importer instead.
FeedProviderAdapter = str

FeedProviderMonetizationMode = Literal[
    "affiliate",
    "direct",
    "pending_affiliate",
]

from app.models.common import ApiModel


class FeedProvider(ApiModel):
    id: str
    name: str
    url: str
    adapter: FeedProviderAdapter = "auto"
    enabled: bool = True
    replace_on_sync: bool = False
    monetization_mode: FeedProviderMonetizationMode = "direct"
    last_sync_at: datetime | None = None
    last_status: str | None = None
    last_message: str | None = None
    last_imported_count: int = 0
    created_at: datetime
    updated_at: datetime


class FeedProviderResponse(ApiModel):
    id: str
    name: str
    url: str
    adapter: FeedProviderAdapter
    enabled: bool
    replace_on_sync: bool
    monetization_mode: FeedProviderMonetizationMode = "direct"
    last_sync_at: datetime | None = None
    last_status: str | None = None
    last_message: str | None = None
    last_imported_count: int
    created_at: datetime
    updated_at: datetime


class FeedProviderUpsertRequest(ApiModel):
    id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    url: str = Field(min_length=8, max_length=2048)
    adapter: FeedProviderAdapter = "auto"
    enabled: bool = True
    replace_on_sync: bool = False
    monetization_mode: FeedProviderMonetizationMode = "direct"


class FeedProviderListResponse(ApiModel):
    items: list[FeedProviderResponse]
    total: int


class FeedProviderSyncResponse(ApiModel):
    status: str
    message: str
    provider_id: str | None = None
    imported_count: int = 0
    deal_count: int | None = None


class FeedSyncRunResponse(ApiModel):
    id: int
    provider_id: str
    provider_name: str | None = None
    url: str
    status: str
    message: str
    imported_count: int
    deal_count: int | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    created_at: datetime


class FeedSyncRunListResponse(ApiModel):
    items: list[FeedSyncRunResponse]
    total: int
