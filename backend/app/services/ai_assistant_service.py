from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import json
import logging
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


logger = logging.getLogger(__name__)


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
        # Optional preferences must never turn an actionable shopping request
        # into a questionnaire, including when the model asks anyway.
        fallback = self._fallback_intent(message, history)
        if intent.needs_clarification and not fallback.needs_clarification:
            intent, provider = fallback, "local_fallback"
        intent = self._normalize_intent(intent, message)
        language = "ru" if intent.language.lower().startswith("ru") or re.search(r"[а-яё]", message.lower()) else "en"
        if intent.needs_clarification:
            question = intent.clarifying_question.strip() or self._clarifying_question(language)
            return question, True, [], self._suggestions(intent.suggestions, language), provider

        # An empty query is valid for store-only or catalogue-wide requests.
        query = self._clean(intent.query)
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
                else "По этим условиям предложений в каталоге нет. Можно расширить поиск или изменить бюджет."
            )
        else:
            reply = (
                f"I found {len(unique)} matching DiscountHub offers. These results come only from our current database."
                if unique
                else "No catalogue offers match these filters. You can broaden the search or change the budget."
            )
        return reply, False, unique, self._suggestions(intent.suggestions, language), provider

    def _extract_intent(
        self,
        message: str,
        history: list[AiChatHistoryItem],
    ) -> tuple[SearchIntent, str]:
        api_key = self.settings.gemini_api_key.strip()
        if not api_key:
            return self._fallback_intent(message, history), "local_fallback"

        history_text = "\n".join(f"{item.role}: {item.content.strip()}" for item in history[-8:])
        prompt = f"""
You parse shopping intent for DiscountHub. DiscountHub has only product deals, store promotions/promo codes, and curated partner offers.
Return JSON search filters only. Never invent an offer, code, price, store, or product. Never use web search.
Search immediately whenever a product, category, store or offer type can be inferred. Budget, country, store and minimum discount are OPTIONAL; never ask for them before searching.
Set needs_clarification=false for broad requests like "laptops", "ноутки", "I need notebook for job", "promo codes" or "show me deals". Ask only when there is no shopping target or understandable search at all.
Use history to resolve follow-ups: "cheaper", "under $500", "до 500", "same store" modify the previous search. Preserve the product and explicit filters unless the user changes/removes them. A new product starts a new search. Assistant suggestions are not user choices.
Keep query to catalogue product keywords, normally English. Correct clear typos and translate common product names (ноутки/ноутбуки/noutbook -> laptop, наушники -> headphones). Remove conversational filler and purpose text like "I need", "for job", "for work". Never put price, discount, country or store into query: use their fields.
Use empty query for store-only or general deals/promo-code requests. Product searches normally include_deals only; promo-code requests include_promotions only. Category must be an actual broad catalogue category (Computers, Electronics, Home, Fashion, Beauty, Sports, Other) or empty; do not invent narrow categories. Country uses ISO two-letter codes or empty, never inferred from the user's language.
Prices and budgets are in USD. Empty string or 0 means unspecified; unspecified min_discount is 1 (any discount), sort is score_desc. "Cheaper" uses price_asc. Return up to three OPTIONAL refinement chips in the user's language, not questions that block results.
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
                "maxOutputTokens": 1024,
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
        ) as exc:
            # Do not log request bodies, keys or the provider's response text.
            logger.warning("AI intent provider failed (%s); using local search", type(exc).__name__)
            return self._fallback_intent(message, history), "local_fallback"

    def _fallback_intent(
        self, message: str, history: list[AiChatHistoryItem] | None = None,
    ) -> SearchIntent:
        # Rebuild only from user turns: suggestions and questions from the
        # assistant must not become filters the shopper never requested.
        previous = None
        for item in (history or [])[-8:]:
            if item.role == "user":
                previous = self._parse_local_turn(item.content, previous)
        return self._parse_local_turn(message, previous)

    def _parse_local_turn(self, message: str, previous: SearchIntent | None) -> SearchIntent:
        lower = message.lower().strip()
        language = "ru" if re.search(r"[а-яё]", lower) else "en"
        budget = re.search(r"(?:under|below|up to|max(?:imum)?|до|не дороже|максимум)\s*\$?\s*(\d+(?:[.,]\d+)?)\s*(?:usd|доллар\w*)?", lower)
        discount = re.search(r"(?:at least|from|от|скидк\w*\s*от)?\s*(\d{1,3})\s*%", lower)
        promo = bool(re.search(r"\b(?:promo(?:tion)?s?|codes?|coupons?|vouchers?|промокод\w*|купон\w*)\b", lower))
        partner = bool(re.search(r"\b(?:partner|lifetime|saas|software|партнёр\w*|сервис\w*|подписк\w*)\b", lower))
        deals = bool(re.search(r"\b(?:deals?|discounts?|товар\w*|скидк\w*)\b", lower))
        cheaper = bool(re.search(r"\b(?:cheaper|cheapest|дешевле|подешевле)\b", lower))
        clear_budget = bool(re.search(r"(?:no budget|any price|без ограничени\w* по цене|любой бюджет)", lower))
        clear_discount = bool(re.search(r"(?:any discount|любой процент|любая скидка|скидка неважна)", lower))
        clear_country = bool(re.search(r"(?:all countries|worldwide|все страны|любая страна)", lower))
        clear_store = bool(re.search(r"(?:all stores|any store|все магазины|любой магазин)", lower))
        country_match = re.search(r"\b(?:in|for|в|для)\s+(US|USA|UK|GB|DE|FR|PL|UZ|united states|germany|poland|uzbekistan|сша|германии|польше|узбекистане)\b", message, re.I)
        country = ""
        if country_match:
            country = self._normalize_country({"германии": "DE", "польше": "PL", "узбекистане": "UZ"}.get(country_match[1].lower(), country_match[1]))
        store_match = re.search(r"\b(ebay(?:\s+(?:us|uk|gb|de|fr|it|es|au))?|aliexpress(?:\s+(?:us|fr|pl|de|es))?|amazon)\b", lower)
        platform = store_match[1] if store_match else ""

        query = lower
        query = re.sub(r"\b(?:biggest|largest|best|maximum)\s+discounts?\b", " ", query)
        for match in (budget, discount, country_match, store_match):
            if match:
                query = query.replace(match[0].lower(), " ")
        query = re.sub(r"(?:for (?:my )?(?:job|work|school|study)|для (?:работы|учёбы|учебы))\b", " ", query)
        query = re.sub(r"(?:no budget|any price|без ограничени\w* по цене|любой бюджет|any discount|любой процент|любая скидка|скидка неважна|all countries|worldwide|все страны|любая страна|all stores|any store|все магазины|любой магазин)", " ", query)
        query = re.sub(r"\b(?:i|me|my|need|want|would|like|please|find|show|give|looking|look|search|buy|some|a|an|the|for|on|in|from|at|with|and|but|instead|only|now|then|useful|online|shopping|cheaper|cheapest|мне|я|нужен|нужна|нужны|хочу|найди|найдите|покажи|покажите|пожалуйста|купить|для|на|в|с|со|а|и|только|теперь|дешевле|подешевле)\b", " ", query)
        query = re.sub(r"\b(?:promo(?:tion)?s?|codes?|coupons?|vouchers?|deals?|discounts?|промокод\w*|купон\w*|скидк\w*|товар\w*)\b", " ", query)
        query = self._product_keywords(query).strip(" .,!?:;-")
        ambiguous = bool(re.fullmatch(r"(?:hi|hello|help|thanks|привет|помоги|спасибо|что посоветуешь|what do you recommend)", lower.strip(" .!?")))
        query = "" if ambiguous else query

        # A filter-only follow-up inherits the previous subject. Naming another
        # product starts a fresh search, so stale laptop filters cannot leak.
        refinement = not query and not ambiguous and bool(budget or discount or cheaper or clear_budget or clear_discount or clear_country or clear_store or country_match or store_match)
        intent = previous.model_copy(deep=True) if previous and refinement and not previous.needs_clarification else SearchIntent(min_discount=1, include_promotions=False, include_partner_offers=False)
        intent.language = language
        if not refinement or not previous:
            intent.query = query
        if budget:
            intent.max_price = float(budget[1].replace(",", "."))
        if clear_budget:
            intent.max_price = 0
        if discount:
            intent.min_discount = max(1, min(100, int(discount[1])))
        if clear_discount:
            intent.min_discount = 1
        if country_match or clear_country:
            intent.country = country
        if store_match or clear_store:
            intent.platform = platform
        if cheaper:
            intent.sort = "price_asc"
        elif discount or "biggest discount" in lower:
            intent.sort = "discount_desc"
        if promo or partner:
            intent.include_deals = False
            intent.include_promotions = promo
            intent.include_partner_offers = partner
        intent.needs_clarification = ambiguous or not bool(intent.query or intent.platform or intent.country or budget or discount or cheaper and previous or promo or partner or deals)
        intent.clarifying_question = self._clarifying_question(language) if intent.needs_clarification else ""
        return intent

    @staticmethod
    def _product_keywords(value: str) -> str:
        aliases = {
            r"\b(?:ноут(?:бук\w*|ки|ы)?|noutbook|laptops?|notebooks?)\b": "laptop",
            r"\bнаушник\w*\b": "headphones",
            r"\b(?:телефон\w*|смартфон\w*)\b": "smartphone",
            r"\bбеспроводн\w*\b": "wireless",
        }
        for pattern, replacement in aliases.items():
            value = re.sub(pattern, replacement, value, flags=re.I)
        return re.sub(r"\s+", " ", value).strip()[:180]

    def _deals(self, intent: SearchIntent, query: str) -> list[AiOfferCard]:
        items = []
        laptop_search = self._wants_laptop(query)
        page_size = 24 if laptop_search else 6
        pages_read = 0

        for candidate_query in self._deal_query_variants(query):
            for page in range(1, 4 if laptop_search else 2):
                if laptop_search and pages_read >= 6:
                    break
                pages_read += 1
                try:
                    candidates, total = deals_service.list_deals(
                        q=candidate_query or None,
                        platform=intent.platform.strip() or None,
                        category=intent.category.strip() or ("Computers" if laptop_search else None),
                        country=intent.country.strip() or None,
                        ships_to=None,
                        delivery_region=None,
                        currency="USD",
                        min_discount=max(1, intent.min_discount),
                        min_rating=None,
                        max_price=intent.max_price or None,
                        free_shipping=None,
                        verified=None,
                        monetization_mode=None,
                        sort=(
                            intent.sort
                            if intent.sort in {
                                "score_desc",
                                "discount_desc",
                                "price_asc",
                                "newest",
                            }
                            else "score_desc"
                        ),
                        page=page,
                        page_size=page_size,
                    )
                except (TypeError, ValueError):
                    break
                items.extend(item for item in candidates if not laptop_search or self._is_laptop_title(item.title))
                if len(items) >= 6 or page * page_size >= total or not candidates:
                    break

            if items or (laptop_search and pages_read >= 6):
                break

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
            for item in items[:6]
        ]

    @staticmethod
    def _wants_laptop(query: str) -> bool:
        # Apply whole-device matching only when the shopper wants a laptop.
        # Explicit accessory searches retain their usual catalogue behavior.
        return bool(re.search(r"\b(?:laptops?|notebooks?|chromebooks?|macbooks?|thinkpads?|ultrabooks?)\b", query, re.I)) and not bool(re.search(
            r"\b(?:chargers?|adapters?|cables?|batter(?:y|ies)|screens?|monitors?|keyboards?|parts?|accessor\w*|cases?|bags?|sleeves?|stands?|заряд\w*|адаптер\w*|кабел\w*|аккумулятор\w*|экран\w*|чехол\w*|сумк\w*)\b", query, re.I
        ))

    @staticmethod
    def _is_laptop_title(title: str) -> bool:
        # A mention in "for Laptop/MacBook" describes compatibility, not the
        # product being sold. Catalogue categories also contain peripherals.
        subject = re.split(r"\b(?:for|compatible|pour|für|для)\b", title, maxsplit=1, flags=re.I)[0]
        if re.search(r"\b(?:adapters?|chargers?|cables?|readers?|stylus|controllers?|converters?|hubs?|sleeves?|bags?|covers?|stands?|protectors?|replacement|monitor|batteries|battery|keyboard|cooling|cleaning)\b", subject, re.I):
            return False
        return bool(re.search(r"\b(?:laptops?|notebooks?|chromebooks?|macbooks?|thinkpads?|ultrabooks?|elitebook|probook|latitude|vivobook|zenbook|omnibook)\b", subject, re.I))

    def _promotions(self, intent: SearchIntent, query: str) -> list[AiOfferCard]:
        try:
            items, _ = promotions_service.list_promotions(
                q=query or None,
                type=None,
                store=intent.platform.strip() or None,
                country=intent.country.strip() or None,
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
        message: str = "",
    ) -> SearchIntent:
        platform = cls._optional_filter(
            intent.platform,
            {
                "all",
                "any",
                "all stores",
                "all marketplaces",
                "all platforms",
                "\u0432\u0441\u0435",
                "\u043b\u044e\u0431\u043e\u0439",
                "\u043b\u044e\u0431\u0430\u044f",
                "\u0432\u0441\u0435 \u043c\u0430\u0433\u0430\u0437\u0438\u043d\u044b",
                "\u0432\u0441\u0435 \u043c\u0430\u0440\u043a\u0435\u0442\u043f\u043b\u0435\u0439\u0441\u044b",
            },
        )

        country = cls._normalize_country(
            intent.country,
        )

        platform, country = cls._normalize_marketplace_region(
            platform,
            country,
            message,
        )

        category = cls._normalize_category(
            intent.category,
            intent.query,
        )

        return intent.model_copy(
            update={
                "query": cls._product_keywords(intent.query),
                "min_discount": max(1, intent.min_discount),
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
    def _normalize_marketplace_region(
        cls,
        platform: str,
        country: str,
        message: str,
    ) -> tuple[str, str]:
        def normalize_text(value: str) -> str:
            normalized = (
                str(value or "")
                .casefold()
                .replace("_", " ")
                .replace("-", " ")
                .replace(".", " ")
            )

            return re.sub(
                r"\s+",
                " ",
                normalized,
            ).strip()

        normalized_platform = normalize_text(platform)
        normalized_message = normalize_text(message)

        regional_marketplaces = {
            "DE": (
                "eBay DE",
                {
                    "ebay de",
                    "ebay germany",
                    "ebay deutschland",
                },
            ),
            "US": (
                "eBay US",
                {
                    "ebay us",
                    "ebay usa",
                    "ebay united states",
                    "ebay com",
                },
            ),
            "GB": (
                "eBay GB",
                {
                    "ebay gb",
                    "ebay uk",
                    "ebay united kingdom",
                    "ebay co uk",
                },
            ),
            "ES": (
                "eBay ES",
                {
                    "ebay es",
                    "ebay spain",
                    "ebay espa\u00f1a",
                },
            ),
            "FR": (
                "eBay FR",
                {
                    "ebay fr",
                    "ebay france",
                },
            ),
            "IT": (
                "eBay IT",
                {
                    "ebay it",
                    "ebay italy",
                    "ebay italia",
                },
            ),
            "AU": (
                "eBay AU",
                {
                    "ebay au",
                    "ebay australia",
                    "ebay com au",
                },
            ),
        }

        for country_code, (
            canonical_platform,
            aliases,
        ) in regional_marketplaces.items():
            normalized_canonical = normalize_text(
                canonical_platform,
            )

            platform_is_regional = (
                normalized_platform == normalized_canonical
                or normalized_platform in aliases
            )

            region_is_explicit = any(
                alias in normalized_message
                for alias in aliases
            )

            if platform_is_regional:
                return canonical_platform, ""

            if (
                normalized_platform == "ebay"
                and country == country_code
                and region_is_explicit
            ):
                return canonical_platform, ""

        return platform, country

    @classmethod
    def _normalize_category(
        cls,
        value: str,
        query: str = "",
    ) -> str:
        cleaned = cls._optional_filter(
            value,
            {
                "all",
                "any",
                "all categories",
                "all products",
                "\u0432\u0441\u0435",
                "\u043b\u044e\u0431\u0430\u044f",
                "\u043b\u044e\u0431\u044b\u0435",
                "\u0432\u0441\u0435 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438",
                "\u0432\u0441\u0435 \u0442\u043e\u0432\u0430\u0440\u044b",
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

        laptop_terms = {
            "laptop",
            "laptops",
            "notebook",
            "notebooks",
            "ultrabook",
            "ultrabooks",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438",
        }

        laptop_modifiers = {
            "gaming",
            "refurbished",
            "used",
            "cheap",
            "affordable",
            "budget",
            "business",
            "student",
            "lightweight",
            "best",
            "new",
            "deal",
            "deals",
            "\u0438\u0433\u0440\u043e\u0432\u043e\u0439",
            "\u0438\u0433\u0440\u043e\u0432\u044b\u0435",
            "\u0431\u044e\u0434\u0436\u0435\u0442\u043d\u044b\u0439",
            "\u0431\u044e\u0434\u0436\u0435\u0442\u043d\u044b\u0435",
            "\u043d\u0435\u0434\u043e\u0440\u043e\u0433\u043e\u0439",
            "\u043d\u0435\u0434\u043e\u0440\u043e\u0433\u0438\u0435",
            "\u043d\u043e\u0432\u044b\u0439",
            "\u043d\u043e\u0432\u044b\u0435",
        }

        normalized_query = (
            str(query or "")
            .casefold()
            .replace("_", " ")
            .replace("-", " ")
        )
        normalized_query = re.sub(
            r"\s+",
            " ",
            normalized_query,
        ).strip()

        query_words = {
            word
            for word in re.findall(
                r"[^\W_]+",
                normalized_query,
            )
            if not word.isdigit()
        }

        if (
            query_words
            and query_words & laptop_terms
            and query_words.issubset(
                laptop_terms | laptop_modifiers
            )
        ):
            return "Computers"

        aliases = {
            "laptop": "Computers",
            "laptops": "Computers",
            "notebook": "Computers",
            "notebooks": "Computers",
            "ultrabook": "Computers",
            "ultrabooks": "Computers",
            "computer": "Computers",
            "computers": "Computers",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a": "Computers",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438": "Computers",
            "\u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440": "Computers",
            "\u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440\u044b": "Computers",
        }

        return aliases.get(
            normalized,
            cleaned,
        )

    @classmethod
    def _deal_query_variants(cls, value: str) -> list[str]:
        cleaned = cls._clean(value)

        if not cleaned:
            return [""]

        normalized = (
            cleaned.casefold()
            .replace("_", " ")
            .replace("-", " ")
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()

        variants = [cleaned]

        if normalized.endswith("s") and len(normalized) > 3:
            variants.append(normalized[:-1])

        laptop_terms = {
            "laptop",
            "laptops",
            "notebook",
            "notebooks",
            "ultrabook",
            "ultrabooks",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a",
            "\u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438",
        }

        words = set(re.findall(r"[^\W_]+", normalized))

        if words & laptop_terms:
            synonyms = [
                "notebook",
                "thinkpad",
                "latitude",
                "macbook",
                "chromebook",
                "ultrabook",
            ]

            for synonym in synonyms:
                candidate = normalized

                for term in laptop_terms:
                    candidate = re.sub(
                        rf"(?<!\w){re.escape(term)}(?!\w)",
                        synonym,
                        candidate,
                    )

                variants.append(candidate)

            if words.issubset(laptop_terms):
                variants.extend(synonyms)

        unique = []

        for variant in variants:
            candidate = cls._clean(variant)

            if candidate and candidate.casefold() not in {
                item.casefold() for item in unique
            }:
                unique.append(candidate)

        return unique

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
                "\u0432\u0441\u0435",
                "\u0432\u0435\u0437\u0434\u0435",
                "\u0433\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u043e",
                "\u043f\u043e \u0432\u0441\u0435\u043c\u0443 \u043c\u0438\u0440\u0443",
                "\u0432\u0441\u0435 \u0441\u0442\u0440\u0430\u043d\u044b",
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
            "\u0441\u0448\u0430": "US",
            "\u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u043d\u044b\u0435 \u0448\u0442\u0430\u0442\u044b": "US",

            "united kingdom": "GB",
            "great britain": "GB",
            "uk": "GB",
            "gb": "GB",
            "\u0432\u0435\u043b\u0438\u043a\u043e\u0431\u0440\u0438\u0442\u0430\u043d\u0438\u044f": "GB",

            "germany": "DE",
            "\u0433\u0435\u0440\u043c\u0430\u043d\u0438\u044f": "DE",
            "france": "FR",
            "\u0444\u0440\u0430\u043d\u0446\u0438\u044f": "FR",
            "spain": "ES",
            "\u0438\u0441\u043f\u0430\u043d\u0438\u044f": "ES",
            "italy": "IT",
            "\u0438\u0442\u0430\u043b\u0438\u044f": "IT",
            "poland": "PL",
            "\u043f\u043e\u043b\u044c\u0448\u0430": "PL",
            "australia": "AU",
            "\u0430\u0432\u0441\u0442\u0440\u0430\u043b\u0438\u044f": "AU",
            "canada": "CA",
            "\u043a\u0430\u043d\u0430\u0434\u0430": "CA",
            "mexico": "MX",
            "\u043c\u0435\u043a\u0441\u0438\u043a\u0430": "MX",
            "brazil": "BR",
            "\u0431\u0440\u0430\u0437\u0438\u043b\u0438\u044f": "BR",
            "turkey": "TR",
            "\u0442\u0443\u0440\u0446\u0438\u044f": "TR",
            "uzbekistan": "UZ",
            "\u0443\u0437\u0431\u0435\u043a\u0438\u0441\u0442\u0430\u043d": "UZ",
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
            return "Какой товар или промокод найти?"
        return "Which product or promo code would you like to find?"

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
