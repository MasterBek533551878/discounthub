from __future__ import annotations

from datetime import datetime, timezone

from app.db.database import get_connection
from app.models.deal import DealMonetizationMode
from app.models.promotion import Promotion, PromotionSort, PromotionType


SQL_ACTIVE_PROMOTION_ONLY = """
(
    (valid_from IS NULL OR datetime(valid_from) <= datetime('now'))
    AND (valid_until IS NULL OR datetime(valid_until) >= datetime('now'))
)
""".strip()


class PromotionsRepository:
    def query_promotions(
        self,
        *,
        q: str | None = None,
        type: PromotionType | None = None,
        store: str | None = None,
        sort: PromotionSort = "featured",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Promotion], int]:
        where_sql, params = self._build_filter_sql(q=q, type=type, store=store)
        order_sql = self._sort_sql(sort)
        offset = max(page - 1, 0) * page_size

        with get_connection() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM promotions {where_sql}",
                params,
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT *
                FROM promotions
                {where_sql}
                {order_sql}
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()

        total = int(total_row["total"] if total_row is not None else 0)
        return [self._row_to_promotion(row) for row in rows], total

    def get_promotion(self, promotion_id: str) -> Promotion | None:
        with get_connection() as connection:
            row = connection.execute(
                f"""
                SELECT *
                FROM promotions
                WHERE id = ? AND {SQL_ACTIVE_PROMOTION_ONLY}
                """,
                (promotion_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_promotion(row)

    def upsert_many(self, promotions: list[Promotion]) -> int:
        if not promotions:
            return 0

        rows = [self._promotion_to_row(promotion) for promotion in promotions]
        with get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO promotions (
                    id, type, title, description, store, discount_text, code,
                    landing_url, affiliate_url, image_url, provider_id,
                    monetization_mode, valid_from, valid_until, featured,
                    updated_at, search_text
                ) VALUES (
                    :id, :type, :title, :description, :store, :discount_text, :code,
                    :landing_url, :affiliate_url, :image_url, :provider_id,
                    :monetization_mode, :valid_from, :valid_until, :featured,
                    :updated_at, :search_text
                )
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    title = excluded.title,
                    description = excluded.description,
                    store = excluded.store,
                    discount_text = excluded.discount_text,
                    code = excluded.code,
                    landing_url = excluded.landing_url,
                    affiliate_url = excluded.affiliate_url,
                    image_url = excluded.image_url,
                    provider_id = excluded.provider_id,
                    monetization_mode = excluded.monetization_mode,
                    valid_from = excluded.valid_from,
                    valid_until = excluded.valid_until,
                    featured = excluded.featured,
                    updated_at = excluded.updated_at,
                    search_text = excluded.search_text
                """,
                rows,
            )
            connection.commit()
        return len(rows)

    def count_promotions(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM promotions").fetchone()
        return int(row["total"] if row is not None else 0)

    def record_click(
        self,
        *,
        promotion_id: str,
        store: str,
        type: PromotionType,
        provider_id: str | None,
        monetization_mode: DealMonetizationMode,
        target_url: str,
        referrer: str | None,
        user_agent: str | None,
        ip_address: str | None,
        clicked_at: datetime,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO promotion_click_events (
                    promotion_id, store, type, provider_id, monetization_mode,
                    target_url, referrer, user_agent, ip_address, clicked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    promotion_id,
                    store,
                    type,
                    provider_id,
                    monetization_mode,
                    target_url,
                    referrer,
                    user_agent,
                    ip_address,
                    clicked_at.astimezone(timezone.utc).isoformat(),
                ),
            )
            connection.commit()

    def _build_filter_sql(
        self,
        *,
        q: str | None,
        type: PromotionType | None,
        store: str | None,
    ) -> tuple[str, tuple[object, ...]]:
        clauses = [SQL_ACTIVE_PROMOTION_ONLY]
        params: list[object] = []

        if q and q.strip():
            clauses.append("search_text LIKE ?")
            params.append(f"%{q.strip().lower()}%")

        if type:
            clauses.append("type = ?")
            params.append(type)

        store_values = self._split_filter_values(store)
        if store_values:
            placeholders = ", ".join("?" for _ in store_values)
            clauses.append(f"LOWER(TRIM(store)) IN ({placeholders})")
            params.extend(value.lower() for value in store_values)

        return f"WHERE {' AND '.join(clauses)}", tuple(params)

    def _split_filter_values(self, value: str | None) -> list[str]:
        if not value:
            return []

        values: list[str] = []
        for raw_item in str(value).split(","):
            item = raw_item.strip()
            if not item or item.lower() == "all":
                continue
            normalized = item.lower()
            if normalized not in values:
                values.append(normalized)
        return values

    def _sort_sql(self, sort: PromotionSort) -> str:
        if sort == "ending_soon":
            return """
            ORDER BY
                CASE WHEN valid_until IS NULL THEN 1 ELSE 0 END ASC,
                datetime(valid_until) ASC,
                featured DESC,
                datetime(updated_at) DESC
            """
        if sort == "newest":
            return "ORDER BY datetime(updated_at) DESC, featured DESC, title ASC"
        return """
        ORDER BY
            featured DESC,
            CASE WHEN valid_until IS NULL THEN 1 ELSE 0 END ASC,
            datetime(valid_until) ASC,
            datetime(updated_at) DESC,
            title ASC
        """

    def _promotion_to_row(self, promotion: Promotion) -> dict[str, object | None]:
        search_text = " ".join(
            [
                promotion.title,
                promotion.description,
                promotion.store,
                promotion.discount_text,
                promotion.code or "",
                promotion.type,
            ]
        ).lower()

        return {
            "id": promotion.id,
            "type": promotion.type,
            "title": promotion.title,
            "description": promotion.description,
            "store": promotion.store,
            "discount_text": promotion.discount_text,
            "code": promotion.code,
            "landing_url": promotion.landing_url,
            "affiliate_url": promotion.affiliate_url,
            "image_url": promotion.image_url,
            "provider_id": promotion.provider_id,
            "monetization_mode": promotion.monetization_mode,
            "valid_from": self._datetime_to_iso(promotion.valid_from),
            "valid_until": self._datetime_to_iso(promotion.valid_until),
            "featured": 1 if promotion.featured else 0,
            "updated_at": self._datetime_to_iso(promotion.updated_at),
            "search_text": search_text,
        }

    def _row_to_promotion(self, row) -> Promotion:
        return Promotion(
            id=str(row["id"]),
            type=str(row["type"]),
            title=str(row["title"]),
            description=str(row["description"] or ""),
            store=str(row["store"]),
            discount_text=str(row["discount_text"] or ""),
            code=row["code"],
            landing_url=str(row["landing_url"]),
            affiliate_url=row["affiliate_url"],
            image_url=row["image_url"],
            provider_id=row["provider_id"],
            monetization_mode=str(row["monetization_mode"] or "affiliate"),
            valid_from=self._parse_datetime(row["valid_from"]),
            valid_until=self._parse_datetime(row["valid_until"]),
            featured=bool(row["featured"]),
            updated_at=self._parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def _parse_datetime(self, value: object) -> datetime | None:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _datetime_to_iso(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat()
