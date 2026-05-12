from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Iterable

from app.db.database import get_connection
from app.models.deal import Deal


class DealsRepository:
    def list_deals(self) -> list[Deal]:
        with get_connection() as connection:
            rows = connection.execute("SELECT * FROM deals").fetchall()
        return [self._row_to_deal(row) for row in rows]

    def get_deal(self, deal_id: str) -> Deal | None:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_deal(row)

    def count_deals(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM deals").fetchone()
        return int(row["total"] if row is not None else 0)

    def get_categories(self) -> list[str]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT category FROM deals ORDER BY category ASC"
            ).fetchall()
        return [str(row["category"]) for row in rows]

    def get_marketplaces(self) -> list[str]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT platform FROM deals ORDER BY platform ASC"
            ).fetchall()
        return [str(row["platform"]) for row in rows]

    def record_click(
        self,
        *,
        deal_id: str,
        platform: str,
        category: str,
        target_url: str,
        referrer: str | None,
        user_agent: str | None,
        ip_address: str | None,
        clicked_at: datetime,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO click_events (
                    deal_id, platform, category, target_url, referrer,
                    user_agent, ip_address, clicked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deal_id,
                    platform,
                    category,
                    target_url,
                    referrer,
                    user_agent,
                    ip_address,
                    clicked_at.isoformat(),
                ),
            )
            connection.commit()

    def click_summary(self, *, limit: int = 20) -> list[dict[str, object]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    deal_id,
                    platform,
                    category,
                    COUNT(*) AS clicks,
                    MAX(clicked_at) AS last_clicked_at
                FROM click_events
                GROUP BY deal_id, platform, category
                ORDER BY clicks DESC, last_clicked_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]


    def upsert_deal(self, deal: Deal) -> None:
        self.upsert_many([deal])

    def delete_deal(self, deal_id: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
            connection.commit()
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM deals")
            connection.commit()
        return cursor.rowcount

    def upsert_many(self, deals: Iterable[Deal]) -> None:
        with get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO deals (
                    id,
                    title,
                    description,
                    image_url,
                    platform,
                    category,
                    old_price,
                    current_price,
                    currency,
                    product_url,
                    affiliate_url,
                    rating,
                    review_count,
                    free_shipping,
                    verified,
                    ships_to,
                    hot_deal,
                    lowest_price,
                    deal_score,
                    updated_at,
                    expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    image_url = excluded.image_url,
                    platform = excluded.platform,
                    category = excluded.category,
                    old_price = excluded.old_price,
                    current_price = excluded.current_price,
                    currency = excluded.currency,
                    product_url = excluded.product_url,
                    affiliate_url = excluded.affiliate_url,
                    rating = excluded.rating,
                    review_count = excluded.review_count,
                    free_shipping = excluded.free_shipping,
                    verified = excluded.verified,
                    ships_to = excluded.ships_to,
                    hot_deal = excluded.hot_deal,
                    lowest_price = excluded.lowest_price,
                    deal_score = excluded.deal_score,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                [self._deal_to_values(deal) for deal in deals],
            )
            connection.commit()

    def _deal_to_values(self, deal: Deal) -> tuple[object, ...]:
        return (
            deal.id,
            deal.title,
            deal.description,
            deal.image_url,
            deal.platform,
            deal.category,
            deal.old_price,
            deal.current_price,
            deal.currency.upper(),
            deal.product_url,
            deal.affiliate_url,
            deal.rating,
            deal.review_count,
            int(deal.free_shipping),
            int(deal.verified),
            json.dumps(deal.ships_to),
            int(deal.hot_deal),
            int(deal.lowest_price),
            deal.deal_score,
            deal.updated_at.isoformat(),
            deal.expires_at.isoformat() if deal.expires_at else None,
        )

    def _row_to_deal(self, row: sqlite3.Row) -> Deal:
        ships_to_raw = row["ships_to"] or "[]"
        try:
            ships_to = json.loads(ships_to_raw)
        except json.JSONDecodeError:
            ships_to = []

        return Deal(
            id=str(row["id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            image_url=str(row["image_url"]),
            platform=str(row["platform"]),
            category=str(row["category"]),
            old_price=float(row["old_price"]),
            current_price=float(row["current_price"]),
            currency=str(row["currency"]),
            product_url=str(row["product_url"]),
            affiliate_url=str(row["affiliate_url"]) if row["affiliate_url"] else None,
            rating=float(row["rating"]),
            review_count=int(row["review_count"]),
            free_shipping=bool(row["free_shipping"]),
            verified=bool(row["verified"]),
            ships_to=[str(item).upper() for item in ships_to],
            hot_deal=bool(row["hot_deal"]),
            lowest_price=bool(row["lowest_price"]),
            deal_score=int(row["deal_score"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])) if row["expires_at"] else None,
        )
