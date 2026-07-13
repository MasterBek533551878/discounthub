from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import json
import re
from threading import Lock
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from pydantic import BaseModel, Field, ValidationError

from app.core.ai_config import get_ai_settings
from app.models.ai_assistant import AiChatHistoryItem, AiOfferCard
from app.services.deals_service import deals_service
from app.services.partner_offers_service import partner_offers_service
from app.services.promotions_service import promotions_service


class AiAssistantUnavailableError(RuntimeError):
    pass


class AiAssistantRateLimitError(RuntimeError):
    pass


class SearchIntent(BaseModel):
    language: str = "en"
    needs_clarification: bool = False
    clarifying_question: str = ""
    query: str = ""
    category: str = ""
    platform: str = ""
    country: str = ""
    max_price: float = Field(default=0, ge=0)
    min_discount: int = Field(default=0, ge=0, le=100)
    include_deals: bool = True
    include_promotions: bool = True
    include_partner_offers: bool = True
    sort: str = "score_desc"
    suggestions: list[str] = Field(default_factory=list)


class AnonymousRateLimiter:
    def __init__(self) -> None:
        self.events: dict[str, deque[datetime]] = defaultdict(deque)
        self.lock = Lock()

    def consume(self, key: str, limit: int) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        safe_key = key.strip() or "unknown"
        with self.lock:
            events = self.events[safe_key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= max(1, limit):
                raise AiAssistantRateLimitError("Anonymous AI limit reached")
            events.append(now)
            return max(0, max(1, limit) - len(events))


class AiAssistantService:
    def __init__(self) -> None:
        self.rate_limiter = AnonymousRateLimiter()

    @property
    def settings(self):
        return get_ai_settings()

    @property
    def provider_name(self) -> str:
        return "gemini" if self.settings.gemini_api_key.strip() else "local_fallback"

    def consume_rate_limit(self, client_key: str) -> int:
        return self.rate_limiter.consume(client_key, self.settings.ai_assistant_hourly_limit)

    def find_offers(
        self,
        *,
        message: str,
        history: list[AiChatHistoryItem],
    ) -> tuple[str, bool, list[AiOfferCard], list[str], str]:
        if not self.settings.ai_assistant_enabled:
            raise AiAssistantUnavailableError("AI assistant is disabled")

        intent, provider = self._extract_intent(message, history)
        intent = self._normalize_intent(intent)
        language = "ru" if intent.language.lower().startswith("ru") or re.search(r"[а-яё]", message.lower()) else "en"
        if intent.needs_clarification:
            question = intent.clarifying_question.strip() or self._clarifying_question(language)
            return question, True, [], self._suggestions(intent.suggestions, language), provider

        query = self._clean(intent.query) or self._clean(message)
        cards: list[AiOfferCard] = []
        if intent.include_deals:
            cards.extend(self._deals(intent, query))
        if intent.include_promotions:
            cards.extend(self._promotions(intent, query))
        if intent.include_partner_offers:
            cards.extend(self._partners(intent, query))

        unique: list[AiOfferCard] = []
        seen: set[tuple[str, str]] = set()
        for card in cards:
            key = (card.kind, card.id)
            if key not in seen:
                seen.add(key)
                unique.append(card)

        unique = unique[: self.settings.ai_assistant_result_limit]
        if language == "ru":
            reply = (
                f"Я нашёл {len(unique)} подходящих предложений в DiscountHub. Показываю только данные из нашей актуальной базы."
                if unique
                else "Пока не нашёл подтверждённых предложений. Попробуйте изменить товар, бюджет или магазин."
            )
        else:
            reply = (
                f"I found {len(unique)} matching DiscountHub offers. These results come only from our current database."
                if unique
                else "I couldn't find a verified match yet. Try changing the product, budget, or store."
            )
        return reply, False, unique, self._suggestions(intent.suggestions, language), provider

    def _extract_intent(
        self,
        message: str,
        history: list[AiChatHistoryItem],
    ) -> tuple[SearchIntent, str]:
        api_key = self.settings.gemini_api_key.strip()
        if not api_key:
            return self._fallback_intent(message), "local_fallback"

        history_text = "\n".join(f"{item.role}: {item.content.strip()}" for item in history[-6:])
        prompt = f"""
You parse shopping intent for DiscountHub. DiscountHub has only product deals, store promotions/promo codes, and curated partner offers.
Return JSON search filters only. Never invent an offer, code, price, store, or product. Never use web search.
Use the message and history. Ask one short clarification only if no useful search can be inferred.
Keep query short. Empty string or 0 means unspecified. Return up to three suggestion chips in the user's language.
History:\n{history_text or '(none)'}\nMessage:\n{message.strip()}
""".strip()
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "needs_clarification": {"type": "boolean"},
                "clarifying_question": {"type": "string"},
                "query": {"type": "string"},
                "category": {"type": "string"},
                "platform": {"type": "string"},
                "country": {"type": "string"},
                "max_price": {"type": "number"},
                "min_discount": {"type": "integer"},
                "include_deals": {"type": "boolean"},
                "include_promotions": {"type": "boolean"},
                "include_partner_offers": {"type": "boolean"},
                "sort": {"type": "string", "enum": ["score_desc", "discount_desc", "price_asc", "newest"]},
                "suggestions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "language", "needs_clarification", "clarifying_question", "query", "category", "platform",
                "country", "max_price", "min_discount", "include_deals", "include_promotions",
                "include_partner_offers", "sort", "suggestions",
            ],
        }
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 450,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent"
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self.settings.ai_assistant_provider_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(str(part.get("text") or "") for part in parts).strip()
            return SearchIntent.model_validate(json.loads(text)), "gemini"
        except (
            urllib_error.URLError,
            urllib_error.HTTPError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            ValidationError,
            json.JSONDecodeError,
        ):
            return self._fallback_intent(message), "local_fallback"

    def _fallback_intent(self, message: str) -> SearchIntent:
        lower = message.lower().strip()
        language = "ru" if re.search(r"[а-яё]", lower) else "en"
        max_price = 0.0
        match = re.search(r"(?:under|below|up to|max(?:imum)?|до|не дороже|максимум)\s*[$€£]?\s*(\d+(?:[.,]\d+)?)", lower)
        if match:
            max_price = float(match.group(1).replace(",", "."))
        discount_match = re.search(r"(\d{1,3})\s*%", lower)
        min_discount = min(100, int(discount_match.group(1))) if discount_match else 0

        promo = any(term in lower for term in ("promo", "coupon", "voucher", "code", "промокод", "купон"))
        partner = any(term in lower for term in ("partner", "lifetime", "saas", "software", "партнёр", "сервис", "подписк"))
        deal = any(term in lower for term in ("product", "buy", "price", "deal", "товар", "купить", "цена", "скидк"))
        selected = promo or partner or deal
        query = self._clean(message)
        return SearchIntent(
            language=language,
            needs_clarification=len(query) < 2,
            clarifying_question=self._clarifying_question(language),
            query=query,
            max_price=max_price,
            min_discount=min_discount,
            include_deals=deal if selected else True,
            include_promotions=promo if selected else True,
            include_partner_offers=partner if selected else True,
            sort="discount_desc" if min_discount else "score_desc",
        )

    def _deals(self, intent: SearchIntent, query: str) -> list[AiOfferCard]:
        try:
            items, _ = deals_service.list_deals(
                q=query or None,
                platform=intent.platform.strip() or None,
                category=intent.category.strip() or None,
                ships_to=intent.country.strip() or None,
                delivery_region=None,
                currency="USD",
                min_discount=intent.min_discount or None,
                min_rating=None,
                max_price=intent.max_price or None,
                free_shipping=None,
                verified=None,
                monetization_mode=None,
                sort=intent.sort if intent.sort in {"score_desc", "discount_desc", "price_asc", "newest"} else "score_desc",
                page=1,
                page_size=6,
            )
        except (TypeError, ValueError):
            return []
        return [
            AiOfferCard(
                kind="deal",
                id=item.id,
                title=item.title,
                merchant=item.platform,
                description=item.description,
                badge=f"-{item.discount_percent}%" if item.discount_percent else "Deal",
                current_price=item.current_price,
                old_price=item.old_price,
                currency=item.currency,
                discount_percent=item.discount_percent,
                image_url=item.image_url or None,
                click_url=f"https://api.discounthub.uz/deals/{item.id}/click",
                page_url=f"https://discounthub.uz/deals/?deal_id={item.id}",
            )
            for item in items
        ]

    def _promotions(self, intent: SearchIntent, query: str) -> list[AiOfferCard]:
        try:
            items, _ = promotions_service.list_promotions(
                q=query or None,
                type=None,
                store=intent.platform.strip() or None,
                sort="featured",
                page=1,
                page_size=4,
            )
        except (TypeError, ValueError):
            return []
        return [
            AiOfferCard(
                kind="promotion",
                id=item.id,
                title=item.title,
                merchant=item.store,
                description=item.description,
                badge=item.discount_text or ("Promo code" if item.code else "Promotion"),
                code=item.code,
                image_url=item.image_url,
                click_url=f"https://api.discounthub.uz/promotions/{item.id}/click",
                page_url=f"https://discounthub.uz/promo-codes/?promotion_id={item.id}",
            )
            for item in items
        ]

    def _partners(self, intent: SearchIntent, query: str) -> list[AiOfferCard]:
        try:
            items, _ = partner_offers_service.list_offers(
                q=query or None,
                category=intent.category.strip() or None,
                sort="featured",
                page=1,
                page_size=4,
            )
        except (TypeError, ValueError):
            return []
        return [
            AiOfferCard(
                kind="partner_offer",
                id=item.id,
                title=item.title,
                merchant=item.partner_name,
                description=item.subtitle or item.description,
                badge=item.offer_text or item.current_price_text or "Partner offer",
                code=item.code,
                image_url=item.image_url or item.logo_url,
                click_url=f"https://api.discounthub.uz/partner-offers/{item.id}/click",
                page_url=f"https://discounthub.uz/partner-offers/?offer_id={item.id}",
            )
            for item in items
        ]

    @classmethod
    def _normalize_intent(
        cls,
        intent: SearchIntent,
    ) -> SearchIntent:
        platform = cls._optional_filter(
            intent.platform,
            {
                "all",
                "any",
                "all stores",
                "all marketplaces",
                "all platforms",
                "???",
                "?????",
                "?????",
                "??? ????????",
                "??? ????????????",
            },
        )

        category = cls._optional_filter(
            intent.category,
            {
                "all",
                "any",
                "all categories",
                "all products",
                "???",
                "?????",
                "?????",
                "??? ?????????",
                "??? ??????",
            },
        )

        country = cls._normalize_country(intent.country)

        return intent.model_copy(
            update={
                "platform": platform,
                "category": category,
                "country": country,
            }
        )

    @staticmethod
    def _optional_filter(
        value: str,
        empty_values: set[str],
    ) -> str:
        cleaned = re.sub(
            r"\s+",
            " ",
            str(value or ""),
        ).strip()

        normalized = (
            cleaned.casefold()
            .replace("_", " ")
            .replace("-", " ")
        )
        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        if normalized in empty_values:
            return ""

        return cleaned

    @classmethod
    def _normalize_country(
        cls,
        value: str,
    ) -> str:
        cleaned = cls._optional_filter(
            value,
            {
                "all",
                "any",
                "global",
                "worldwide",
                "international",
                "everywhere",
                "all countries",
                "???",
                "?????",
                "?????????",
                "?? ????? ????",
                "??? ??????",
            },
        )

        if not cleaned:
            return ""

        normalized = (
            cleaned.casefold()
            .replace("_", " ")
            .replace("-", " ")
        )
        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        aliases = {
            "united states": "US",
            "united states of america": "US",
            "usa": "US",
            "us": "US",
            "united kingdom": "GB",
            "great britain": "GB",
            "uk": "GB",
            "gb": "GB",
            "germany": "DE",
            "france": "FR",
            "spain": "ES",
            "italy": "IT",
            "poland": "PL",
            "australia": "AU",
            "canada": "CA",
            "mexico": "MX",
            "brazil": "BR",
            "turkey": "TR",
            "uzbekistan": "UZ",
        }

        if normalized in aliases:
            return aliases[normalized]

        if len(cleaned) == 2 and cleaned.isalpha():
            return cleaned.upper()

        return cleaned

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()[:180]

    @staticmethod
    def _clarifying_question(language: str) -> str:
        if language == "ru":
            return "Что именно вы ищете и есть ли желаемая цена, магазин или размер скидки?"
        return "What are you looking for, and do you have a preferred price, store, or discount?"

    @staticmethod
    def _suggestions(items: list[str], language: str) -> list[str]:
        cleaned = []
        for item in items[:3]:
            value = re.sub(r"\s+", " ", str(item or "")).strip()[:70]
            if value and value not in cleaned:
                cleaned.append(value)
        if cleaned:
            return cleaned
        if language == "ru":
            return ["Техника до $50", "Промокоды для покупок", "Партнёрские lifetime-предложения"]
        return ["Tech deals under $50", "Shopping promo codes", "Lifetime partner offers"]


ai_assistant_service = AiAssistantService()
