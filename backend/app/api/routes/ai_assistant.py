from hashlib import sha256
import re

from fastapi import APIRouter, HTTPException, Request, status

from app.core.ai_config import get_ai_settings
from app.models.ai_assistant import (
    AiAssistantStatus,
    AiChatRequest,
    AiChatResponse,
)
from app.services.ai_assistant_service import (
    AiAssistantUnavailableError,
    ai_assistant_service,
)
from app.services.ai_rate_limit_service import (
    AiRateLimitExceeded,
    AiRateLimitReservation,
    ai_rate_limiter,
)


router = APIRouter(prefix="/ai", tags=["ai-assistant"])
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{16,80}$")


def _client_ip(request: Request) -> str:
    cloudflare_ip = request.headers.get("cf-connecting-ip", "").strip()
    forwarded_ip = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    direct_ip = request.client.host if request.client else ""
    return cloudflare_ip or forwarded_ip or direct_ip or "unknown"


def _hashed_key(namespace: str, value: str) -> str:
    digest = sha256(value.encode("utf-8", errors="ignore")).hexdigest()
    return f"{namespace}:{digest}"


def _browser_key(payload: AiChatRequest, client_ip: str) -> str:
    session_id = payload.session_id.strip()
    if _SESSION_ID_PATTERN.fullmatch(session_id):
        return _hashed_key("browser", session_id)
    return _hashed_key("browser-ip-fallback", client_ip)


@router.get("/status", response_model=AiAssistantStatus, response_model_by_alias=True)
def ai_status() -> AiAssistantStatus:
    settings = get_ai_settings()
    return AiAssistantStatus(
        enabled=settings.ai_assistant_enabled,
        provider=ai_assistant_service.provider_name,
        ai_configured=bool(settings.gemini_api_key.strip()),
        hourly_limit=settings.ai_assistant_browser_hourly_limit,
    )


@router.post("/chat", response_model=AiChatResponse, response_model_by_alias=True)
def ai_chat(payload: AiChatRequest, request: Request) -> AiChatResponse:
    settings = get_ai_settings()
    client_ip = _client_ip(request)
    reservation: AiRateLimitReservation | None = None

    try:
        remaining, reservation = ai_rate_limiter.consume(
            browser_key=_browser_key(payload, client_ip),
            ip_key=_hashed_key("ip", client_ip),
            browser_limit=settings.ai_assistant_browser_hourly_limit,
            ip_limit=settings.ai_assistant_ip_hourly_limit,
        )
        reply, needs_clarification, items, suggestions, provider = (
            ai_assistant_service.find_offers(
                message=payload.message,
                history=payload.history,
            )
        )
    except AiRateLimitExceeded as exc:
        if exc.scope == "network":
            detail = (
                "This network has temporarily reached the AI fair-use limit. "
                "Please try again later or use the normal DiscountHub search."
            )
        else:
            detail = (
                "This browser has reached its hourly AI message limit. "
                "Please try again later or use the normal DiscountHub search."
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "3600"},
        ) from exc
    except AiAssistantUnavailableError as exc:
        if reservation is not None:
            ai_rate_limiter.refund(reservation)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is temporarily unavailable.",
        ) from exc
    except Exception:
        if reservation is not None:
            ai_rate_limiter.refund(reservation)
        raise

    return AiChatResponse(
        reply=reply,
        needs_clarification=needs_clarification,
        items=items,
        suggestions=suggestions,
        provider=provider,
        remaining_requests=remaining,
    )
