from typing import Literal

from pydantic import Field

from app.models.common import ApiModel


AiOfferKind = Literal["deal", "promotion", "partner_offer"]
AiChatRole = Literal["user", "assistant"]


class AiChatHistoryItem(ApiModel):
    role: AiChatRole
    content: str = Field(min_length=1, max_length=500)


class AiChatRequest(ApiModel):
    message: str = Field(min_length=2, max_length=500)
    history: list[AiChatHistoryItem] = Field(default_factory=list, max_length=8)
    session_id: str = Field(default="", max_length=80)


class AiOfferCard(ApiModel):
    kind: AiOfferKind
    id: str
    title: str
    merchant: str
    description: str = ""
    badge: str = ""
    code: str | None = None
    current_price: float | None = None
    old_price: float | None = None
    currency: str | None = None
    discount_percent: int | None = None
    image_url: str | None = None
    click_url: str
    page_url: str


class AiChatResponse(ApiModel):
    reply: str
    needs_clarification: bool = False
    items: list[AiOfferCard] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    provider: str
    remaining_requests: int


class AiAssistantStatus(ApiModel):
    enabled: bool
    provider: str
    ai_configured: bool
    anonymous: bool = True
    registration_required: bool = False
    hourly_limit: int
