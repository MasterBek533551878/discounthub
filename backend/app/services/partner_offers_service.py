from datetime import datetime, timezone

from app.models.partner_offer import (
    PartnerOffer,
    PartnerOfferResponse,
    PartnerOfferSort,
    PartnerOfferUpsertRequest,
)
from app.repositories.partner_offers_repository import PartnerOffersRepository
from app.services.promotions_service import clean_promotion_text


class PartnerOfferNotFoundError(Exception):
    pass


def clean_partner_offer_category(value: str | None) -> str:
    cleaned = clean_promotion_text(value).lower().strip()
    if not cleaned:
        return "other"
    cleaned = cleaned.replace("&", "and").replace("/", "-")
    cleaned = "-".join(part for part in cleaned.replace("_", "-").split() if part)
    return cleaned[:80] or "other"


class PartnerOffersService:
    def __init__(self, repository: PartnerOffersRepository | None = None) -> None:
        self._repository = repository or PartnerOffersRepository()

    def list_offers(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        sort: PartnerOfferSort = "featured",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PartnerOfferResponse], int]:
        offers, total = self._repository.query_offers(
            q=q,
            category=category,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return [self._to_response(offer) for offer in offers], total

    def get_offer(self, offer_id: str) -> PartnerOfferResponse:
        offer = self._repository.get_offer(offer_id)
        if offer is None:
            raise PartnerOfferNotFoundError(offer_id)
        return self._to_response(offer)

    def get_category_facets(self, *, q: str | None = None) -> list[dict[str, object]]:
        return self._repository.get_category_facets(q=q)

    def upsert_offer(self, payload: PartnerOfferUpsertRequest) -> PartnerOfferResponse:
        offer = self._request_to_offer(payload)
        self._repository.upsert_many([offer])
        return self._to_response(offer)

    def upsert_offers(self, payloads: list[PartnerOfferUpsertRequest]) -> int:
        offers = [self._request_to_offer(payload) for payload in payloads]
        return self._repository.upsert_many(offers)

    def delete_offer(self, offer_id: str) -> bool:
        return self._repository.delete_offer(offer_id)

    def count_offers(self) -> int:
        return self._repository.count_offers()

    def _request_to_offer(self, payload: PartnerOfferUpsertRequest) -> PartnerOffer:
        monetization_mode = payload.monetization_mode or "direct"

        return PartnerOffer(
            id=payload.id.strip(),
            title=clean_promotion_text(payload.title),
            subtitle=clean_promotion_text(payload.subtitle),
            description=clean_promotion_text(payload.description),
            partner_name=clean_promotion_text(payload.partner_name),
            category=clean_partner_offer_category(payload.category),
            tags=[clean_promotion_text(tag) for tag in payload.tags if clean_promotion_text(tag)],
            offer_text=clean_promotion_text(payload.offer_text),
            original_price_text=clean_promotion_text(payload.original_price_text),
            current_price_text=clean_promotion_text(payload.current_price_text),
            code=clean_promotion_text(payload.code) if payload.code else None,
            landing_url=payload.landing_url.strip(),
            checkout_url=payload.checkout_url.strip() if payload.checkout_url else None,
            image_url=payload.image_url.strip() if payload.image_url else None,
            logo_url=payload.logo_url.strip() if payload.logo_url else None,
            countries=clean_promotion_text(payload.countries) or "Global",
            monetization_mode=monetization_mode,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            featured=payload.featured,
            verified=payload.verified,
            updated_at=payload.updated_at or datetime.now(timezone.utc),
        )

    def _to_response(self, offer: PartnerOffer) -> PartnerOfferResponse:
        return PartnerOfferResponse(
            id=offer.id,
            title=clean_promotion_text(offer.title),
            subtitle=clean_promotion_text(offer.subtitle),
            description=clean_promotion_text(offer.description),
            partner_name=clean_promotion_text(offer.partner_name),
            category=offer.category,
            tags=[clean_promotion_text(tag) for tag in offer.tags if clean_promotion_text(tag)],
            offer_text=clean_promotion_text(offer.offer_text),
            original_price_text=clean_promotion_text(offer.original_price_text),
            current_price_text=clean_promotion_text(offer.current_price_text),
            code=clean_promotion_text(offer.code) if offer.code else None,
            landing_url=offer.landing_url,
            checkout_url=offer.checkout_url,
            image_url=offer.image_url,
            logo_url=offer.logo_url,
            countries=clean_promotion_text(offer.countries) or "Global",
            monetization_mode=offer.monetization_mode,
            valid_from=offer.valid_from,
            valid_until=offer.valid_until,
            featured=offer.featured,
            verified=offer.verified,
            updated_at=offer.updated_at,
        )


partner_offers_service = PartnerOffersService()
