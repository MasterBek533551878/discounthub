from datetime import datetime, timezone

from app.models.promotion import (
    Promotion,
    PromotionsPage,
    PromotionResponse,
    PromotionSort,
    PromotionType,
    PromotionUpsertRequest,
)
from app.repositories.promotions_repository import PromotionsRepository


class PromotionNotFoundError(Exception):
    pass


class PromotionsService:
    def __init__(self, repository: PromotionsRepository | None = None) -> None:
        self._repository = repository or PromotionsRepository()

    def list_promotions(
        self,
        *,
        q: str | None = None,
        type: PromotionType | None = None,
        store: str | None = None,
        sort: PromotionSort = "featured",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PromotionResponse], int]:
        promotions, total = self._repository.query_promotions(
            q=q,
            type=type,
            store=store,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return [self._to_response(promotion) for promotion in promotions], total

    def get_promotion(self, promotion_id: str) -> PromotionResponse:
        promotion = self._repository.get_promotion(promotion_id)
        if promotion is None:
            raise PromotionNotFoundError(promotion_id)
        return self._to_response(promotion)

    def upsert_promotions(self, payloads: list[PromotionUpsertRequest]) -> int:
        promotions = [self._request_to_promotion(payload) for payload in payloads]
        return self._repository.upsert_many(promotions)

    def _request_to_promotion(self, payload: PromotionUpsertRequest) -> Promotion:
        monetization_mode = payload.monetization_mode
        if monetization_mode is None:
            monetization_mode = "affiliate" if (payload.affiliate_url or "").strip() else "direct"

        return Promotion(
            id=payload.id,
            type=payload.type,
            title=payload.title,
            description=payload.description,
            store=payload.store,
            discount_text=payload.discount_text,
            code=payload.code,
            landing_url=payload.landing_url,
            affiliate_url=payload.affiliate_url,
            image_url=payload.image_url,
            provider_id=payload.provider_id,
            monetization_mode=monetization_mode,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            featured=payload.featured,
            updated_at=payload.updated_at or datetime.now(timezone.utc),
        )

    def _to_response(self, promotion: Promotion) -> PromotionResponse:
        return PromotionResponse(
            id=promotion.id,
            type=promotion.type,
            title=promotion.title,
            description=promotion.description,
            store=promotion.store,
            discount_text=promotion.discount_text,
            code=promotion.code,
            landing_url=promotion.landing_url,
            affiliate_url=promotion.affiliate_url,
            image_url=promotion.image_url,
            provider_id=promotion.provider_id,
            monetization_mode=promotion.monetization_mode,
            valid_from=promotion.valid_from,
            valid_until=promotion.valid_until,
            featured=promotion.featured,
            updated_at=promotion.updated_at,
        )


promotions_service = PromotionsService()
