from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import threading

from app.db.database import get_connection


AWIN_OFFERS_PROVIDER_PREFIX = "awin_offers_"

# These are not useful DiscountHub promotions. Keep the terms lowercase.
HARD_BLOCK_TERMS: tuple[str, ...] = (
    "free shipping",
    "free delivery",
    "free mainland uk delivery",
    "free uk delivery",
    "free gift",
    "gift with purchase",
    "buy one get one",
    "bogo",
    "2 for 1",
    "3 for 2",
    "alibaba lens",
    "one image search",
    "image search for price comparison",
    "saving spotlight",
    "below retail price",
    "ai & app subscription",
    "ai & app subspriction",
)

GENERIC_DISCOUNT_TEXTS: set[str] = {"", "sale", "promo code", "promotion", "offer"}
TEXT_COLUMNS: tuple[str, ...] = ("title", "description", "store", "discount_text", "code")


@dataclass(frozen=True)
class PromotionCleanupResult:
    checked_count: int
    deleted_count: int
    remaining_count: int
    deleted_reasons: dict[str, int] = field(default_factory=dict)
    updated_text_count: int = 0
    skipped: bool = False
    error: str | None = None


class PromotionCleanupService:
    """Keeps promotion rows healthy.

    This removes expired/low-value promo rows and normalizes text mojibake in
    stored promotions. It is safe to call after every Awin sync and periodically
    from public /promotions requests.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_cleanup_at: datetime | None = None

    def cleanup_if_due(self, *, min_interval_seconds: int = 1800) -> PromotionCleanupResult:
        now = datetime.now(timezone.utc)
        last = self._last_cleanup_at
        if last is not None and (now - last).total_seconds() < min_interval_seconds:
            return PromotionCleanupResult(checked_count=0, deleted_count=0, remaining_count=0, skipped=True)

        if not self._lock.acquire(blocking=False):
            return PromotionCleanupResult(checked_count=0, deleted_count=0, remaining_count=0, skipped=True)

        try:
            return self._cleanup_promotions_locked(now=now)
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            return PromotionCleanupResult(
                checked_count=0,
                deleted_count=0,
                remaining_count=0,
                skipped=True,
                error=str(exc),
            )
        finally:
            self._lock.release()

    def cleanup_promotions(self) -> PromotionCleanupResult:
        with self._lock:
            return self._cleanup_promotions_locked(now=datetime.now(timezone.utc))

    def _cleanup_promotions_locked(self, *, now: datetime) -> PromotionCleanupResult:
        deleted_reasons: dict[str, int] = {}
        checked_count = 0
        deleted_count = 0
        updated_text_count = 0

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, type, title, description, store, discount_text, code,
                       provider_id, valid_until
                FROM promotions
                """
            ).fetchall()
            checked_count = len(rows)

            for row in rows:
                normalized_values = self._normalized_row_values(row)
                if normalized_values:
                    assignments = ", ".join(f"{column} = ?" for column in normalized_values)
                    params = list(normalized_values.values()) + [row["id"]]
                    connection.execute(
                        f"UPDATE promotions SET {assignments} WHERE id = ?",
                        params,
                    )
                    updated_text_count += 1

                # Re-check delete reason on normalized text so hard-block terms
                # are caught even if they originally arrived as mojibake.
                effective_row = dict(row)
                effective_row.update(normalized_values)
                reason = self._delete_reason(effective_row, now=now)
                if reason is None:
                    continue

                connection.execute("DELETE FROM promotions WHERE id = ?", (row["id"],))
                deleted_count += 1
                deleted_reasons[reason] = deleted_reasons.get(reason, 0) + 1

            connection.commit()
            remaining_row = connection.execute("SELECT COUNT(*) AS total FROM promotions").fetchone()

        self._last_cleanup_at = now
        remaining_count = int(remaining_row["total"] if remaining_row is not None else 0)
        return PromotionCleanupResult(
            checked_count=checked_count,
            deleted_count=deleted_count,
            remaining_count=remaining_count,
            deleted_reasons=deleted_reasons,
            updated_text_count=updated_text_count,
        )

    def _normalized_row_values(self, row) -> dict[str, object | None]:
        updates: dict[str, object | None] = {}
        for column in TEXT_COLUMNS:
            original = row[column]
            if original is None:
                continue
            normalized = self.normalize_text(str(original))
            if normalized != str(original):
                updates[column] = normalized
        return updates

    def normalize_text(self, value: str) -> str:
        """Repair common Awin mojibake while leaving valid UTF-8 alone."""
        if not value:
            return ""

        text = value

        # Common mojibake sequences seen in Awin Offers API / PowerShell output.
        replacements = {
            "â¬": "€",
            "â‚¬": "€",
            chr(0x00E2) + chr(0x0082) + chr(0x00AC): "€",
            chr(0x00E2) + chr(0x20AC) + chr(0x00AC): "€",
            "Â£": "£",
            "￡": "£",
            "Â$": "$",
            "â€“": "–",
            "â€”": "—",
            "â€˜": "'",
            "â€™": "'",
            "â€œ": '"',
            "â€�": '"',
            "â€¦": "…",
            "Â ": " ",
            "Â ": " ",
            chr(0x00C2) + chr(0x00A0): " ",
            chr(0xFEFF): "",
            chr(0xFFFD): "",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)

        # If the text still contains mojibake markers, try a conservative
        # latin1/cp1252 -> utf-8 repair. Do this at most twice.
        markers = ("Ã", "Å", "â", "Â", "ï¼")
        for _ in range(2):
            if not any(marker in text for marker in markers):
                break
            repaired = None
            for encoding in ("cp1252", "latin1"):
                try:
                    candidate = text.encode(encoding).decode("utf-8")
                except UnicodeError:
                    continue
                if candidate and candidate != text:
                    repaired = candidate
                    break
            if repaired is None:
                break
            text = repaired
            for bad, good in replacements.items():
                text = text.replace(bad, good)

        text = text.replace("ï¼š", ":").replace("ï¼", ":").replace("：", ":")
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _delete_reason(self, row, *, now: datetime) -> str | None:
        valid_until = self._parse_datetime(row.get("valid_until") if isinstance(row, dict) else row["valid_until"])
        if valid_until is not None and valid_until < now:
            return "expired"

        provider_id = str(row.get("provider_id") if isinstance(row, dict) else row["provider_id"] or "").strip()
        is_awin_offer = provider_id.startswith(AWIN_OFFERS_PROVIDER_PREFIX)
        if not is_awin_offer:
            return None

        title = self.normalize_text(str((row.get("title") if isinstance(row, dict) else row["title"]) or ""))
        description = self.normalize_text(str((row.get("description") if isinstance(row, dict) else row["description"]) or ""))
        discount_text = self.normalize_text(str((row.get("discount_text") if isinstance(row, dict) else row["discount_text"]) or ""))
        code = self.normalize_text(str((row.get("code") if isinstance(row, dict) else row["code"]) or "")).strip()
        full_text = f"{title} {description} {discount_text}".lower()

        for term in HARD_BLOCK_TERMS:
            if term in full_text:
                return f"blocked:{term}"

        if not code and discount_text.lower().strip() in GENERIC_DISCOUNT_TEXTS:
            if not self._has_concrete_discount(f"{title} {description} {discount_text}"):
                return "generic_sale_without_discount"

        return None

    def _has_concrete_discount(self, text: str) -> bool:
        normalized = self.normalize_text(text).lower()
        if re.search(r"\b\d{1,3}\s*%\s*(?:off|discount)?\b", normalized):
            return True
        if re.search(r"(?:[€£$]\s*\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s*[€£$])\s*(?:off|discount|save)?\b", normalized):
            return True
        if re.search(r"\b(?:save|get)\s+(?:up\s+to\s+)?(?:[€£$]\s*\d+|\d+\s*[€£$]|\d{1,3}\s*%)", normalized):
            return True
        return False

    def _parse_datetime(self, value: object | None) -> datetime | None:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None

        raw = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


promotion_cleanup_service = PromotionCleanupService()
