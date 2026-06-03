import json
from datetime import datetime, timezone

from app.data.mock_deals import MOCK_DEALS
from app.models.deal import (
    Deal,
    DealFacetItem,
    DealMonetizationMode,
    DealPriceRange,
    DealDiscountRange,
    DealResponse,
    DealsFacetsResponse,
    DealSort,
    DealUpsertRequest,
)
from app.repositories.deals_repository import DealsRepository
from app.services.category_normalizer import normalize_category

# Demo rates only. Production must use a real exchange-rate source.
DEMO_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "AUD": 1.52,
    "UZS": 12650.0,
    "TRY": 32.5,
    "AED": 3.67,
    # Latin America marketplace demo rates. Production must use a real FX source.
    "MXN": 18.5,
    "BRL": 5.4,
    "ARS": 1100.0,
    "CLP": 950.0,
    "COP": 4200.0,
    "PEN": 3.7,
    "UYU": 40.0,
}



PUBLIC_MARKETPLACE_RULES: tuple[tuple[str, str], ...] = (
    ("ebay", "eBay"),
    ("aliexpress", "AliExpress"),
    ("alibaba", "Alibaba"),
    ("amazon", "Amazon"),
    ("shein", "SHEIN"),
    ("dhgate", "DHgate"),
    ("rakuten", "Rakuten"),
    ("back market", "Back Market"),
    ("backmarket", "Back Market"),
    ("cdiscount", "Cdiscount"),
    ("xiaomi", "Xiaomi"),
    ("geekbuying", "Geekbuying"),
    ("banggood", "Banggood"),
    ("temu", "Temu"),
    ("iherb", "iHerb"),
    ("lookfantastic", "LOOKFANTASTIC"),
    ("myprotein", "Myprotein"),
    ("sephora", "Sephora"),
    ("decathlon", "Decathlon"),
)

class DealNotFoundError(Exception):
    pass


class DealsService:
    def __init__(self, repository: DealsRepository | None = None) -> None:
        self._repository = repository or DealsRepository()
        self._facets_cache: dict[str, tuple[datetime, DealsFacetsResponse]] = {}
        self._facets_cache_ttl_seconds = 45

    def list_deals(
        self,
        *,
        q: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        ships_to: str | None = None,
        currency: str = "USD",
        min_discount: int | None = None,
        min_rating: float | None = None,
        max_price: float | None = None,
        free_shipping: bool | None = None,
        verified: bool | None = None,
        monetization_mode: DealMonetizationMode | None = None,
        sort: DealSort = "score_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DealResponse], int]:
        normalized_category = normalize_category(category) if category else None
        max_price_usd = self._convert_amount(max_price, currency, "USD") if max_price is not None else None

        deals, total = self._repository.query_deals(
            q=q,
            platform=platform,
            category=normalized_category,
            ships_to=ships_to,
            min_discount=min_discount,
            min_rating=min_rating,
            max_price_usd=max_price_usd,
            free_shipping=free_shipping,
            verified=verified,
            monetization_mode=monetization_mode,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        return [self._to_response(deal, currency) for deal in deals], total

    def get_facets(
        self,
        *,
        q: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        ships_to: str | None = None,
        currency: str = "USD",
        min_discount: int | None = None,
        min_rating: float | None = None,
        max_price: float | None = None,
        free_shipping: bool | None = None,
        verified: bool | None = None,
        monetization_mode: DealMonetizationMode | None = None,
    ) -> DealsFacetsResponse:
        target_currency = currency.upper().strip() or "USD"
        normalized_category = normalize_category(category) if category else None
        max_price_usd = self._convert_amount(max_price, target_currency, "USD") if max_price is not None else None

        cache_key = self._facets_cache_key(
            q=q,
            platform=platform,
            category=normalized_category,
            ships_to=ships_to,
            currency=target_currency,
            min_discount=min_discount,
            min_rating=min_rating,
            max_price_usd=max_price_usd,
            free_shipping=free_shipping,
            verified=verified,
            monetization_mode=monetization_mode,
        )
        cached = self._facets_cache.get(cache_key)
        now = datetime.now(timezone.utc)
        if cached is not None:
            cached_at, cached_response = cached
            if (now - cached_at).total_seconds() <= self._facets_cache_ttl_seconds:
                return cached_response

        raw = self._repository.get_facets(
            q=q,
            platform=platform,
            category=normalized_category,
            ships_to=ships_to,
            min_discount=min_discount,
            min_rating=min_rating,
            max_price_usd=max_price_usd,
            free_shipping=free_shipping,
            verified=verified,
            monetization_mode=monetization_mode,
        )

        min_price_usd = raw["min_price_usd"]
        max_price_usd_value = raw["max_price_usd"]
        min_price = (
            round(self._convert_amount(float(min_price_usd), "USD", target_currency), 2)
            if min_price_usd is not None
            else None
        )
        max_price_value = (
            round(self._convert_amount(float(max_price_usd_value), "USD", target_currency), 2)
            if max_price_usd_value is not None
            else None
        )

        response = DealsFacetsResponse(
            total=int(raw["total"]),
            marketplaces=self._to_facet_items(raw["marketplaces"]),
            categories=self._to_facet_items(raw["categories"]),
            shipping_countries=self._to_facet_items(raw["shipping_countries"]),
            currencies=self._to_facet_items(raw["currencies"]),
            monetization_modes=self._to_facet_items(raw["monetization_modes"]),
            price_range=DealPriceRange(
                min=min_price,
                max=max_price_value,
                currency=target_currency,
            ),
            discount_range=DealDiscountRange(
                min=raw["min_discount"],
                max=raw["max_discount"],
            ),
            generated_at=now,
        )
        self._facets_cache[cache_key] = (now, response)
        if len(self._facets_cache) > 64:
            oldest_key = min(
                self._facets_cache,
                key=lambda key: self._facets_cache[key][0],
            )
            self._facets_cache.pop(oldest_key, None)
        return response

    def get_deal(self, deal_id: str, *, currency: str = "USD") -> DealResponse:
        deal = self._repository.get_deal(deal_id)
        if deal is None:
            raise DealNotFoundError(deal_id)
        return self._to_response(deal, currency)

    def upsert_deal(self, payload: DealUpsertRequest, *, currency: str = "USD") -> DealResponse:
        deal = self._request_to_deal(payload)
        self._repository.upsert_deal(deal)
        return self._to_response(deal, currency)

    def upsert_deals(self, payloads: list[DealUpsertRequest]) -> int:
        deals = [self._request_to_deal(payload) for payload in payloads]
        self._repository.upsert_many(deals)
        return len(deals)

    def export_deals(self) -> list[DealUpsertRequest]:
        deals = self._sort(self._repository.list_deals(), "newest")
        return [self._deal_to_upsert_request(deal) for deal in deals]

    def import_deals(self, payloads: list[DealUpsertRequest], *, replace: bool = False) -> int:
        if replace:
            self._repository.delete_all()
        deals = [self._request_to_deal(payload) for payload in payloads]
        self._repository.upsert_many(deals)
        return len(deals)

    def delete_deal(self, deal_id: str) -> bool:
        return self._repository.delete_deal(deal_id)

    def reset_demo_deals(self) -> int:
        self._repository.delete_all()
        self._repository.upsert_many(MOCK_DEALS)
        return self._repository.count_deals()

    def get_categories(self) -> list[str]:
        return self._repository.get_categories()

    def get_marketplaces(self) -> list[str]:
        return self._repository.get_marketplaces()

    def count_deals(self) -> int:
        return self._repository.count_deals()

    def _facets_cache_key(self, **values: object) -> str:
        normalized = {
            key: (str(value).strip() if value is not None else "")
            for key, value in values.items()
        }
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    def _to_facet_items(self, raw_items: object) -> list[DealFacetItem]:
        if not isinstance(raw_items, list):
            return []
        return [DealFacetItem.model_validate(item) for item in raw_items]

    def _deal_to_upsert_request(self, deal: Deal) -> DealUpsertRequest:
        return DealUpsertRequest(
            id=deal.id,
            title=deal.title,
            description=deal.description,
            image_url=deal.image_url,
            platform=deal.platform,
            category=deal.category,
            old_price=deal.old_price,
            current_price=deal.current_price,
            currency=deal.currency,
            product_url=deal.product_url,
            affiliate_url=deal.affiliate_url,
            provider_id=deal.provider_id,
            monetization_mode=deal.monetization_mode,
            rating=deal.rating,
            review_count=deal.review_count,
            free_shipping=deal.free_shipping,
            verified=deal.verified,
            ships_to=deal.ships_to,
            hot_deal=deal.hot_deal,
            lowest_price=deal.lowest_price,
            deal_score=deal.deal_score,
            updated_at=deal.updated_at,
            expires_at=deal.expires_at,
        )

    def _request_to_deal(self, payload: DealUpsertRequest) -> Deal:
        deal_score = payload.deal_score
        if deal_score is None:
            deal_score = self._estimate_deal_score(payload)

        product_url = str(payload.product_url).strip()
        affiliate_url = str(payload.affiliate_url).strip() if payload.affiliate_url else None
        monetization_mode = payload.monetization_mode
        if monetization_mode is None:
            monetization_mode = "affiliate" if affiliate_url and affiliate_url != product_url else "direct"

        return Deal(
            id=payload.id.strip(),
            title=payload.title.strip(),
            description=payload.description.strip(),
            image_url=str(payload.image_url).strip(),
            platform=self._normalize_platform(payload.platform),
            category=normalize_category(payload.category),
            old_price=float(payload.old_price),
            current_price=float(payload.current_price),
            currency=payload.currency.upper().strip(),
            product_url=product_url,
            affiliate_url=affiliate_url,
            provider_id=str(payload.provider_id).strip() if payload.provider_id else None,
            monetization_mode=monetization_mode,
            rating=float(payload.rating),
            review_count=int(payload.review_count),
            free_shipping=payload.free_shipping,
            verified=payload.verified,
            ships_to=[item.upper().strip() for item in payload.ships_to if item.strip()],
            hot_deal=payload.hot_deal,
            lowest_price=payload.lowest_price,
            deal_score=deal_score,
            updated_at=payload.updated_at or datetime.now(timezone.utc),
            expires_at=payload.expires_at,
        )



    def _public_marketplace_label(self, value: str) -> str:
        platform = str(value or "").strip()
        normalized = platform.lower().replace("-", " ").replace("_", " ")
        for prefix, label in PUBLIC_MARKETPLACE_RULES:
            if normalized.startswith(prefix):
                return label
        return platform

    def _normalize_platform(self, value: str) -> str:
        platform = str(value or "").strip()
        normalized = platform.lower().replace("-", "_").replace(" ", "_")
        # For users, eBay Motors is still eBay US. Keep the provider separate in
        # backend storage, but group the marketplace label/filter under eBay US.
        if normalized in {"ebay_motors_us", "ebay_motors_us_v1", "ebay_motors"}:
            return "eBay US"
        return platform

    def _estimate_deal_score(self, payload: DealUpsertRequest) -> int:
        if payload.old_price <= 0:
            discount = 0
        else:
            discount = round(((payload.old_price - payload.current_price) / payload.old_price) * 100)

        score = min(max(discount, 0), 70)
        score += round(payload.rating * 4)
        if payload.free_shipping:
            score += 5
        if payload.verified:
            score += 5
        if payload.lowest_price:
            score += 5
        if payload.hot_deal:
            score += 5
        return min(score, 100)

    def _sort(self, deals: list[Deal], sort: DealSort) -> list[Deal]:
        if sort == "discount_desc":
            return sorted(deals, key=lambda deal: deal.discount_percent, reverse=True)
        if sort == "price_asc":
            return sorted(deals, key=lambda deal: deal.current_price)
        if sort == "price_desc":
            return sorted(deals, key=lambda deal: deal.current_price, reverse=True)
        if sort == "rating_desc":
            return sorted(deals, key=lambda deal: deal.rating, reverse=True)
        if sort == "newest":
            return sorted(deals, key=lambda deal: deal.updated_at, reverse=True)
        return sorted(deals, key=lambda deal: deal.deal_score, reverse=True)

    def _to_response(self, deal: Deal, currency: str) -> DealResponse:
        target_currency = currency.upper()
        old_price = self._convert_amount(deal.old_price, deal.currency, target_currency)
        current_price = self._convert_amount(deal.current_price, deal.currency, target_currency)

        return DealResponse(
            id=deal.id,
            title=deal.title,
            description=deal.description,
            image_url=deal.image_url,
            platform=self._public_marketplace_label(deal.platform),
            category=deal.category,
            old_price=round(old_price, 2),
            current_price=round(current_price, 2),
            currency=target_currency,
            product_url=deal.product_url,
            affiliate_url=deal.affiliate_url,
            provider_id=deal.provider_id,
            monetization_mode=deal.monetization_mode,
            rating=deal.rating,
            review_count=deal.review_count,
            free_shipping=deal.free_shipping,
            verified=deal.verified,
            ships_to=deal.ships_to,
            hot_deal=deal.hot_deal,
            lowest_price=deal.lowest_price,
            deal_score=deal.deal_score,
            discount_percent=deal.discount_percent,
            updated_at=deal.updated_at,
            expires_at=deal.expires_at,
        )

    def _convert_amount(self, amount: float, source_currency: str, target_currency: str) -> float:
        source = source_currency.upper()
        target = target_currency.upper()

        if source not in DEMO_RATES:
            source = "USD"
        if target not in DEMO_RATES:
            target = "USD"

        amount_in_usd = amount / DEMO_RATES[source]
        return amount_in_usd * DEMO_RATES[target]


deals_service = DealsService()
