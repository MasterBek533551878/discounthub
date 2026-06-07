from datetime import datetime, timezone
import html
import re

from app.models.promotion import (
    Promotion,
    PromotionResponse,
    PromotionSort,
    PromotionType,
    PromotionUpsertRequest,
)
from app.repositories.promotions_repository import PromotionsRepository


class PromotionNotFoundError(Exception):
    pass


def clean_promotion_text(value: str | None) -> str:
    """Repair narrow Awin promotion mojibake before storing or returning it.

    Awin offers sometimes contain UTF-8 bytes decoded as Latin-1/Windows-1252,
    for example "â\x82¬200 OFF" or "â¬200 OFF" instead of "€200 OFF".
    Keep this helper local to promotions so product titles/deals are not changed.
    """
    if value is None:
        return ""

    text = html.unescape(str(value)).strip()
    if not text:
        return ""

    def replace_known_symbols(raw: str) -> str:
        replacements = {
            # Euro sign variants. The first one includes the hidden U+0082
            # control character often dropped by terminals/log renderers.
            chr(0x00E2) + chr(0x0082) + chr(0x00AC): "€",
            chr(0x00E2) + chr(0x201A) + chr(0x00AC): "€",
            chr(0x00E2) + chr(0x00AC): "€",
            "â‚¬": "€",
            "â¬": "€",
            "Â£": "£",
            chr(0x00C2) + "£": "£",
            "Â$": "$",
            chr(0x00C2) + "$": "$",
            "Â ": " ",
            "Â\xa0": " ",
            chr(0x00C2) + chr(0x00A0): " ",
            "ï¼š": ":",
            "ï¼": ":",
            "：": ":",
            "\ufeff": "",
        }
        for bad, good in replacements.items():
            raw = raw.replace(bad, good)
        return raw

    text = replace_known_symbols(text)

    # Try a narrow mojibake repair loop for common Polish / punctuation cases.
    mojibake_markers = ("Ã", "Å", "â", "Â", "ï¼")
    for _ in range(2):
        if not any(marker in text for marker in mojibake_markers):
            break
        repaired = None
        for encoding in ("latin1", "cp1252"):
            try:
                candidate = text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            if candidate and candidate != text:
                repaired = candidate
                break
        if repaired is None:
            break
        text = replace_known_symbols(repaired)

    text = replace_known_symbols(text)

    replacements = {
        # AliExpress PL labels, normalized to English for current app UI.
        "Letnia Wyprzedaż": "Summer Sale",
        "Letnia WyprzedaÅ": "Summer Sale",
        "Letnia WyprzedaÅ¼": "Summer Sale",
        "Wartość": "Value",
        "WartoÅ": "Value",
        "WartoÅ ": "Value ",
        "Min. Zamówienie": "Min. order",
        "Min. ZamÃ³wienie": "Min. order",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return re.sub(r"[ \t]+", " ", text).strip()


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

    def count_promotions(self) -> int:
        return self._repository.count_promotions()

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
            title=clean_promotion_text(payload.title),
            description=clean_promotion_text(payload.description),
            store=clean_promotion_text(payload.store),
            discount_text=clean_promotion_text(payload.discount_text),
            code=clean_promotion_text(payload.code) if payload.code else None,
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
        # Also clean on output so existing local DB rows created before this fix
        # do not leak mojibake into the Flutter UI.
        return PromotionResponse(
            id=promotion.id,
            type=promotion.type,
            title=clean_promotion_text(promotion.title),
            description=clean_promotion_text(promotion.description),
            store=clean_promotion_text(promotion.store),
            discount_text=clean_promotion_text(promotion.discount_text),
            code=clean_promotion_text(promotion.code) if promotion.code else None,
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
