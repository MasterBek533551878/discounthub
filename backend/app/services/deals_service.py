from datetime import datetime, timezone

from app.data.mock_deals import MOCK_DEALS
from app.models.deal import Deal, DealResponse, DealSort, DealUpsertRequest
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


class DealNotFoundError(Exception):
    pass


class DealsService:
    def __init__(self, repository: DealsRepository | None = None) -> None:
        self._repository = repository or DealsRepository()

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
        sort: DealSort = "score_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DealResponse], int]:
        deals = self._repository.list_deals()

        if q:
            query = q.strip().lower()
            deals = [
                deal
                for deal in deals
                if query in deal.title.lower()
                or query in deal.description.lower()
                or query in deal.platform.lower()
                or query in deal.category.lower()
                or query in normalize_category(deal.category).lower()
            ]

        if platform:
            deals = [deal for deal in deals if deal.platform.lower() == platform.lower()]

        if category:
            normalized_category = normalize_category(category).lower()
            deals = [
                deal
                for deal in deals
                if normalize_category(deal.category).lower() == normalized_category
            ]

        if ships_to:
            country = ships_to.upper()
            deals = [deal for deal in deals if country in [item.upper() for item in deal.ships_to]]

        if min_discount is not None:
            deals = [deal for deal in deals if deal.discount_percent >= min_discount]

        if min_rating is not None:
            deals = [deal for deal in deals if deal.rating >= min_rating]

        if max_price is not None:
            # max_price is interpreted in requested currency.
            deals = [
                deal
                for deal in deals
                if self._convert_amount(deal.current_price, deal.currency, currency) <= max_price
            ]

        if free_shipping is not None:
            deals = [deal for deal in deals if deal.free_shipping == free_shipping]

        if verified is not None:
            deals = [deal for deal in deals if deal.verified == verified]

        deals = self._sort(deals, sort)

        total = len(deals)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        page_items = deals[start:end]

        return [self._to_response(deal, currency) for deal in page_items], total

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

        return Deal(
            id=payload.id.strip(),
            title=payload.title.strip(),
            description=payload.description.strip(),
            image_url=str(payload.image_url).strip(),
            platform=payload.platform.strip(),
            category=normalize_category(payload.category),
            old_price=float(payload.old_price),
            current_price=float(payload.current_price),
            currency=payload.currency.upper().strip(),
            product_url=str(payload.product_url).strip(),
            affiliate_url=str(payload.affiliate_url).strip() if payload.affiliate_url else None,
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
            platform=deal.platform,
            category=deal.category,
            old_price=round(old_price, 2),
            current_price=round(current_price, 2),
            currency=target_currency,
            product_url=deal.product_url,
            affiliate_url=deal.affiliate_url,
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
