from fastapi import APIRouter, HTTPException, Request, status

from app.core.ai_config import get_ai_settings
from app.models.ai_assistant import (
    AiAssistantStatus,
    AiChatRequest,
    AiChatResponse,
)
from app.services.ai_assistant_service import (
    AiAssistantRateLimitError,
    AiAssistantUnavailableError,
    ai_assistant_service,
)


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


def _client_key(request: Request) -> str:
    cloudflare_ip = request.headers.get("cf-connecting-ip", "").strip()
    forwarded_ip = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    direct_ip = request.client.host if request.client else ""
    return cloudflare_ip or forwarded_ip or direct_ip or "unknown"


@router.get("/status", response_model=AiAssistantStatus, response_model_by_alias=True)
def ai_status() -> AiAssistantStatus:
    settings = get_ai_settings()
    return AiAssistantStatus(
        enabled=settings.ai_assistant_enabled,
        provider=ai_assistant_service.provider_name,
        ai_configured=bool(settings.gemini_api_key.strip()),
        hourly_limit=settings.ai_assistant_hourly_limit,
    )


@router.post("/chat", response_model=AiChatResponse, response_model_by_alias=True)
def ai_chat(payload: AiChatRequest, request: Request) -> AiChatResponse:
    try:
        remaining = ai_assistant_service.consume_rate_limit(_client_key(request))
        reply, needs_clarification, items, suggestions, provider = (
            ai_assistant_service.find_offers(
                message=payload.message,
                history=payload.history,
            )
        )
    except AiAssistantRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Anonymous AI limit reached. Please try again later or use the normal DiscountHub search.",
            headers={"Retry-After": "3600"},
        ) from exc
    except AiAssistantUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is temporarily unavailable.",
        ) from exc

    return AiChatResponse(
        reply=reply,
        needs_clarification=needs_clarification,
        items=items,
        suggestions=suggestions,
        provider=provider,
        remaining_requests=remaining,
    )
