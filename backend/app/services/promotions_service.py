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
from app.services.promotion_cleanup_service import promotion_cleanup_service


class PromotionNotFoundError(Exception):
    pass


PROVIDER_STORE_NAMES: dict[str, str] = {
    "awin_offers_17940": "Alibaba US",
    "awin_offers_17942": "Alibaba UK",
    "awin_offers_17943": "Alibaba EU",
    "awin_offers_123746": "Navimow FR",
    "awin_offers_3134": "Startrite",
}


def provider_store_name(provider_id: str | None) -> str | None:
    if not provider_id:
        return None
    return PROVIDER_STORE_NAMES.get(str(provider_id).strip())


def _replace_known_mojibake(text: str) -> str:
    euro = chr(0x20AC)
    pound = chr(0x00A3)
    bullet = chr(0x2022)
    apostrophe = "'"
    dash = chr(0x2013)
    long_dash = chr(0x2014)

    # Build mojibake tokens with chr(...) so Windows PowerShell cannot corrupt
    # this source file during copy/paste.
    c2 = chr(0x00C2)
    e2 = chr(0x00E2)
    ac = chr(0x00AC)
    lsq = chr(0x2018)
    rsq = chr(0x2019)
    ldq = chr(0x201C)
    rdq = chr(0x201D)

    replacements = {
        e2 + chr(0x0082) + ac: euro,
        e2 + chr(0x201A) + ac: euro,
        e2 + ac: euro,
        c2 + chr(0x00A3): pound,
        c2 + "$": "$",
        c2 + " ": " ",
        c2 + chr(0x00A0): " ",
        e2 + chr(0x0080) + chr(0x0099): apostrophe,
        e2 + chr(0x20AC) + chr(0x2122): apostrophe,
        e2 + rsq: apostrophe,
        e2 + chr(0x0080) + chr(0x0098): apostrophe,
        e2 + chr(0x20AC) + chr(0x02DC): apostrophe,
        e2 + lsq: apostrophe,
        e2 + chr(0x0080) + chr(0x009C): '"',
        e2 + chr(0x20AC) + chr(0x0153): '"',
        e2 + ldq: '"',
        e2 + chr(0x0080) + chr(0x009D): '"',
        e2 + chr(0x20AC) + chr(0x009D): '"',
        e2 + rdq: '"',
        e2 + chr(0x0080) + chr(0x0093): dash,
        e2 + chr(0x20AC) + chr(0x201C): dash,
        e2 + chr(0x0080) + chr(0x0094): long_dash,
        e2 + chr(0x20AC) + chr(0x201D): long_dash,
        e2 + chr(0x0080) + chr(0x00A2): bullet,
        e2 + chr(0x20AC) + chr(0x00A2): bullet,
        e2 + chr(0x00A2): bullet,
        chr(0x00EF) + chr(0x00BB) + chr(0x00BF): "",
        chr(0xFEFF): "",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Extra real-world Awin cases from production are built from chr(...)
    # tokens above to keep this source safe across Windows terminals.
    text = text.replace(e2 + ac, euro)
    text = text.replace(c2 + chr(0x00A3), pound)
    text = re.sub(e2 + r"(?=s\b)", apostrophe, text)
    text = re.sub(r"(?m)^\s*" + e2 + r"\s+", bullet + " ", text)

    return text


def clean_promotion_text(value: str | None) -> str:
    if value is None:
        return ""

    text = html.unescape(str(value)).strip()
    if not text:
        return ""

    text = _replace_known_mojibake(text)

    # Try generic repair for common UTF-8-as-Latin1/CP1252 mojibake.
    for _ in range(2):
        before_score = len(re.findall(r"[\u00c2\u00c3\u00e2\ufffd]", text))
        best = text

        for encoding in ("latin1", "cp1252"):
            try:
                candidate = text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue

            candidate = _replace_known_mojibake(candidate)
            candidate_score = len(re.findall(r"[\u00c2\u00c3\u00e2\ufffd]", candidate))

            if candidate_score < before_score:
                best = candidate
                before_score = candidate_score

        if best == text:
            break

        text = best

    text = _replace_known_mojibake(text)

    # Keep this in English for app display.
    text = text.replace("Letnia Wyprzeda\u017c", "Summer Sale")
    text = text.replace("Letnia Wyprzeda\u00c5\u00bc", "Summer Sale")
    text = text.replace("Warto\u015b\u0107", "Value")
    text = text.replace("Warto\u00c5\u009b\u00c4\u0087", "Value")
    text = text.replace("Min. Zam\u00f3wienie", "Min. order")
    text = text.replace("Min. Zam\u00c3\u00b3wienie", "Min. order")

    text = re.sub(r"(?m)^-\s*Method", "\u2022 Method", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_promotion_store(store: str | None, provider_id: str | None) -> str:
    mapped = provider_store_name(provider_id)
    if mapped:
        return mapped

    cleaned = clean_promotion_text(store)
    return cleaned or "Unknown store"


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
        promotion_cleanup_service.cleanup_if_due()
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
        promotion_cleanup_service.cleanup_if_due()
        promotion = self._repository.get_promotion(promotion_id)
        if promotion is None:
            raise PromotionNotFoundError(promotion_id)
        return self._to_response(promotion)

    def count_promotions(self) -> int:
        return self._repository.count_promotions()

    def get_store_facets(
        self,
        *,
        q: str | None = None,
        type: PromotionType | None = None,
    ) -> list[dict[str, object]]:
        promotion_cleanup_service.cleanup_if_due()
        return self._repository.get_store_facets(q=q, type=type)

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
            store=clean_promotion_store(payload.store, payload.provider_id),
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
        return PromotionResponse(
            id=promotion.id,
            type=promotion.type,
            title=clean_promotion_text(promotion.title),
            description=clean_promotion_text(promotion.description),
            store=clean_promotion_store(promotion.store, promotion.provider_id),
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
