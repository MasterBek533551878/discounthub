from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.database import get_connection
from app.models.deal import DealMonetizationMode
from app.models.partner_offer import PartnerOffer, PartnerOfferSort


SQL_ACTIVE_PARTNER_OFFER_ONLY = """
(
    (valid_from IS NULL OR datetime(valid_from) <= datetime('now'))
    AND (valid_until IS NULL OR datetime(valid_until) >= datetime('now'))
)
""".strip()


class PartnerOffersRepository:
    def query_offers(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        sort: PartnerOfferSort = "featured",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PartnerOffer], int]:
        where_sql, params = self._build_filter_sql(q=q, category=category)
        order_sql = self._sort_sql(sort)
        offset = max(page - 1, 0) * page_size

        with get_connection() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM partner_offers {where_sql}",
                params,
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT *
                FROM partner_offers
                {where_sql}
                {order_sql}
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()

        total = int(total_row["total"] if total_row is not None else 0)
        return [self._row_to_offer(row) for row in rows], total

    def get_offer(self, offer_id: str) -> PartnerOffer | None:
        with get_connection() as connection:
            row = connection.execute(
                f"""
                SELECT *
                FROM partner_offers
                WHERE id = ? AND {SQL_ACTIVE_PARTNER_OFFER_ONLY}
                """,
                (offer_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_offer(row)

    def get_category_facets(self, *, q: str | None = None) -> list[dict[str, object]]:
        where_sql, params = self._build_filter_sql(q=q, category=None)
        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT category, COUNT(*) AS count
                FROM partner_offers
                {where_sql}
                GROUP BY category
                HAVING TRIM(COALESCE(category, '')) <> ''
                ORDER BY count DESC, LOWER(category) ASC
                LIMIT 100
                """,
                params,
            ).fetchall()

        return [
            {
                "id": str(row["category"]),
                "name": self._category_label(str(row["category"])),
                "count": int(row["count"]),
            }
            for row in rows
        ]

    def upsert_many(self, offers: list[PartnerOffer]) -> int:
        if not offers:
            return 0

        rows = [self._offer_to_row(offer) for offer in offers]
        with get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO partner_offers (
                    id, title, subtitle, description, partner_name, category,
                    tags, offer_text, original_price_text, current_price_text,
                    code, landing_url, checkout_url, image_url, logo_url,
                    countries, monetization_mode, valid_from, valid_until,
                    featured, verified, updated_at, search_text
                ) VALUES (
                    :id, :title, :subtitle, :description, :partner_name, :category,
                    :tags, :offer_text, :original_price_text, :current_price_text,
                    :code, :landing_url, :checkout_url, :image_url, :logo_url,
                    :countries, :monetization_mode, :valid_from, :valid_until,
                    :featured, :verified, :updated_at, :search_text
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    subtitle = excluded.subtitle,
                    description = excluded.description,
                    partner_name = excluded.partner_name,
                    category = excluded.category,
                    tags = excluded.tags,
                    offer_text = excluded.offer_text,
                    original_price_text = excluded.original_price_text,
                    current_price_text = excluded.current_price_text,
                    code = excluded.code,
                    landing_url = excluded.landing_url,
                    checkout_url = excluded.checkout_url,
                    image_url = excluded.image_url,
                    logo_url = excluded.logo_url,
                    countries = excluded.countries,
                    monetization_mode = excluded.monetization_mode,
                    valid_from = excluded.valid_from,
                    valid_until = excluded.valid_until,
                    featured = excluded.featured,
                    verified = excluded.verified,
                    updated_at = excluded.updated_at,
                    search_text = excluded.search_text
                """,
                rows,
            )
            connection.commit()
        return len(rows)

    def delete_offer(self, offer_id: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM partner_offers WHERE id = ?", (offer_id,))
            connection.commit()
        return cursor.rowcount > 0

    def count_offers(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM partner_offers").fetchone()
        return int(row["total"] if row is not None else 0)

    def record_click(
        self,
        *,
        offer_id: str,
        partner_name: str,
        category: str,
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
                INSERT INTO partner_offer_click_events (
                    offer_id, partner_name, category, monetization_mode,
                    target_url, referrer, user_agent, ip_address, clicked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    offer_id,
                    partner_name,
                    category,
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
        category: str | None,
    ) -> tuple[str, tuple[object, ...]]:
        clauses = [SQL_ACTIVE_PARTNER_OFFER_ONLY]
        params: list[object] = []

        if q and q.strip():
            clauses.append("search_text LIKE ?")
            params.append(f"%{q.strip().lower()}%")

        category_values = self._split_filter_values(category)
        if category_values:
            placeholders = ", ".join("?" for _ in category_values)
            clauses.append(f"LOWER(TRIM(category)) IN ({placeholders})")
            params.extend(value.lower() for value in category_values)

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

    def _sort_sql(self, sort: PartnerOfferSort) -> str:
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
            verified DESC,
            CASE WHEN valid_until IS NULL THEN 1 ELSE 0 END ASC,
            datetime(valid_until) ASC,
            datetime(updated_at) DESC,
            title ASC
        """

    def _offer_to_row(self, offer: PartnerOffer) -> dict[str, object | None]:
        tags = self._normalize_tags(offer.tags)
        search_text = " ".join(
            [
                offer.title,
                offer.subtitle,
                offer.description,
                offer.partner_name,
                offer.category,
                " ".join(tags),
                offer.offer_text,
                offer.original_price_text,
                offer.current_price_text,
                offer.code or "",
                offer.countries,
            ]
        ).lower()

        return {
            "id": offer.id,
            "title": offer.title,
            "subtitle": offer.subtitle,
            "description": offer.description,
            "partner_name": offer.partner_name,
            "category": offer.category,
            "tags": json.dumps(tags, ensure_ascii=False),
            "offer_text": offer.offer_text,
            "original_price_text": offer.original_price_text,
            "current_price_text": offer.current_price_text,
            "code": offer.code,
            "landing_url": offer.landing_url,
            "checkout_url": offer.checkout_url,
            "image_url": offer.image_url,
            "logo_url": offer.logo_url,
            "countries": offer.countries,
            "monetization_mode": offer.monetization_mode,
            "valid_from": self._datetime_to_iso(offer.valid_from),
            "valid_until": self._datetime_to_iso(offer.valid_until),
            "featured": 1 if offer.featured else 0,
            "verified": 1 if offer.verified else 0,
            "updated_at": self._datetime_to_iso(offer.updated_at),
            "search_text": search_text,
        }

    def _row_to_offer(self, row) -> PartnerOffer:
        return PartnerOffer(
            id=str(row["id"]),
            title=str(row["title"]),
            subtitle=str(row["subtitle"] or ""),
            description=str(row["description"] or ""),
            partner_name=str(row["partner_name"]),
            category=str(row["category"] or "other"),
            tags=self._decode_tags(row["tags"]),
            offer_text=str(row["offer_text"] or ""),
            original_price_text=str(row["original_price_text"] or ""),
            current_price_text=str(row["current_price_text"] or ""),
            code=row["code"],
            landing_url=str(row["landing_url"]),
            checkout_url=row["checkout_url"],
            image_url=row["image_url"],
            logo_url=row["logo_url"],
            countries=str(row["countries"] or "Global"),
            monetization_mode=str(row["monetization_mode"] or "direct"),
            valid_from=self._parse_datetime(row["valid_from"]),
            valid_until=self._parse_datetime(row["valid_until"]),
            featured=bool(row["featured"]),
            verified=bool(row["verified"]),
            updated_at=self._parse_datetime(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def _normalize_tags(self, values: list[str]) -> list[str]:
        tags: list[str] = []
        for raw_value in values:
            value = str(raw_value).strip()
            if not value:
                continue
            exists = any(existing.lower() == value.lower() for existing in tags)
            if not exists:
                tags.append(value)
        return tags[:12]

    def _decode_tags(self, value: object) -> list[str]:
        if value is None:
            return []
        raw = str(value).strip()
        if not raw:
            return []
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = [item.strip() for item in raw.split(",")]
        if not isinstance(decoded, list):
            return []
        return self._normalize_tags([str(item) for item in decoded])

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

    def _category_label(self, value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        labels = {
            "devtools": "DevTools",
            "dev-tools": "DevTools",
            "saas": "SaaS",
            "ai-tools": "AI Tools",
            "ai_tools": "AI Tools",
            "startup-tools": "Startup Tools",
            "startup_tools": "Startup Tools",
            "software": "Software",
        }
        return labels.get(normalized, value.strip().replace("_", " ").title() or "Other")
