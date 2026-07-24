from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from app.db.database import get_connection
from app.models.deal import Deal, DealMonetizationMode, DealSort
from app.services.country_availability import (
    SUPPORTED_FILTER_COUNTRIES,
    country_name,
    normalize_country_code,
)


SQL_RATE_CASE = """
CASE UPPER(currency)
    WHEN 'USD' THEN 1.0
    WHEN 'EUR' THEN 0.92
    WHEN 'GBP' THEN 0.78
    WHEN 'AUD' THEN 1.52
    WHEN 'CNY' THEN 6.76
    WHEN 'UZS' THEN 12650.0
    WHEN 'TRY' THEN 32.5
    WHEN 'AED' THEN 3.67
    WHEN 'MXN' THEN 18.5
    WHEN 'BRL' THEN 5.4
    WHEN 'ARS' THEN 1100.0
    WHEN 'CLP' THEN 950.0
    WHEN 'COP' THEN 4200.0
    WHEN 'PEN' THEN 3.7
    WHEN 'UYU' THEN 40.0
    ELSE 1.0
END
""".strip()

# Materialized performance columns are maintained by database migrations and
# DealsRepository.upsert_many(). They make /deals and /deals/facets avoid
# recalculating FX prices and discounts for every row on every request.
SQL_CURRENT_PRICE_USD = "current_price_usd"
SQL_DISCOUNT_PERCENT = "discount_percent"
SQL_REAL_DISCOUNT_ONLY = "(current_price > 0.01 AND old_price > current_price AND discount_percent >= 1 AND COALESCE(LOWER(TRIM(platform)), '') <> 'el corte ingles es')"
SQL_PUBLIC_FRESH_DEAL_ONLY = (
    "("
    "updated_at IS NOT NULL AND ("
    # AliExpress catalogue rows expire very quickly in real life. Keep them
    # stricter than other affiliate feeds so deleted/ended products disappear
    # from the public app before users click into unavailable item pages.
    "("
    "monetization_mode = 'affiliate' "
    "AND (public_platform = 'AliExpress' OR LOWER(platform) LIKE 'aliexpress%') "
    "AND datetime(updated_at) >= datetime('now', '-48 hours')"
    ") OR ("
    "monetization_mode = 'affiliate' "
    "AND NOT (public_platform = 'AliExpress' OR LOWER(platform) LIKE 'aliexpress%') "
    "AND datetime(updated_at) >= datetime('now', '-7 days')"
    ") OR ("
    "COALESCE(monetization_mode, 'direct') != 'affiliate' "
    "AND datetime(updated_at) >= datetime('now', '-72 hours')"
    ")"
    ")"
    ")"
)
SQL_NOT_EXPIRED_DEAL_ONLY = "(expires_at IS NULL OR datetime(expires_at) >= datetime('now'))"
SQL_DEDUPE_KEY = """
LOWER(TRIM(COALESCE(platform, ''))) || '|' ||
LOWER(TRIM(COALESCE(title, ''))) || '|' ||
UPPER(TRIM(COALESCE(currency, ''))) || '|' ||
printf('%.2f', current_price) || '|' ||
printf('%.2f', old_price)
""".strip()

BAD_DEAL_KEYWORDS = (
    "as is",
    "box only",
    "broken",
    "cable only",
    "case only",
    "charger only",
    "cover only",
    "damaged",
    "defect",
    "defective",
    "display only",
    "empty box",
    "faulty",
    "for parts",
    "for repair",
    "housing only",
    "lcd screen only",
    "logic board",
    "mainboard",
    "manual only",
    "motherboard",
    "non working",
    "not working",
    "parts only",
    "read description",
    "read listing",
    "repair only",
    "replacement",
    "screen protector",
    "shell only",
    "spare parts",
    "spares",
    "tempered glass",
    "untested",
    "unknown condition",
)



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


def _public_marketplace_sql(column: str = "platform") -> str:
    """Return SQL that groups technical feed/platform names for the UI.

    Example: eBay US/eBay ES/eBay MOTORS_US become one public marketplace
    called eBay; AliExpress PL/EU/WW become AliExpress. Source regions stay
    internal to providers and links, not exposed as separate stores.
    """
    expression = f"LOWER(TRIM(COALESCE({column}, '')))"
    cases = ["CASE"]
    for pattern, label in PUBLIC_MARKETPLACE_RULES:
        escaped_pattern = pattern.replace("'", "''")
        escaped_label = label.replace("'", "''")
        cases.append(f"WHEN {expression} LIKE '{escaped_pattern}%' THEN '{escaped_label}'")
    cases.append(f"ELSE TRIM(COALESCE({column}, ''))")
    cases.append("END")
    return "\n".join(cases)

class DealsRepository:
    def list_deals(self) -> list[Deal]:
        with get_connection() as connection:
            rows = connection.execute("SELECT * FROM deals").fetchall()
        return [self._row_to_deal(row) for row in rows]

    def query_deals(
        self,
        *,
        q: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        country: str | None = None,
        ships_to: str | None = None,
        delivery_region: str | None = None,
        min_discount: int | None = None,
        min_rating: float | None = None,
        max_price_usd: float | None = None,
        free_shipping: bool | None = None,
        verified: bool | None = None,
        monetization_mode: DealMonetizationMode | None = None,
        sort: DealSort = "score_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Deal], int]:
        where_sql, params = self._build_filter_sql(
            q=q,
            platform=platform,
            category=category,
            country=country,
            ships_to=ships_to,
            delivery_region=delivery_region,
            min_discount=min_discount,
            min_rating=min_rating,
            max_price_usd=max_price_usd,
            free_shipping=free_shipping,
            verified=verified,
            monetization_mode=monetization_mode,
        )
        cte_sql = self._dedupe_cte_sql(where_sql)
        order_sql = self._sort_sql(sort)
        offset = max(page - 1, 0) * page_size

        with get_connection() as connection:
            # Build the expensive filtered/deduplicated set once. The old path
            # evaluated the same window-function CTE twice: once for COUNT(*)
            # and again for the requested page. COUNT(*) OVER() gives each page
            # row the total without repeating the full catalogue scan.
            rows = connection.execute(
                f"""
                {cte_sql},
                unique_deals AS (
                    SELECT *
                    FROM ranked_deals
                    WHERE dedupe_rank = 1
                )
                SELECT
                    unique_deals.*,
                    COUNT(*) OVER() AS _total_count
                FROM unique_deals
                {order_sql}
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()

            if rows:
                total = int(rows[0]["_total_count"] or 0)
            elif offset > 0:
                # A request beyond the final page has no row from which to read
                # the window count. Keep pagination semantics correct with a
                # count-only fallback for this uncommon edge case.
                total_row = connection.execute(
                    f"""
                    {cte_sql}
                    SELECT COUNT(*) AS total
                    FROM ranked_deals
                    WHERE dedupe_rank = 1
                    """,
                    params,
                ).fetchone()
                total = int(total_row["total"] if total_row is not None else 0)
            else:
                total = 0

        return [self._row_to_deal(row) for row in rows], total

    def get_facets(
        self,
        *,
        q: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        country: str | None = None,
        ships_to: str | None = None,
        delivery_region: str | None = None,
        min_discount: int | None = None,
        min_rating: float | None = None,
        max_price_usd: float | None = None,
        free_shipping: bool | None = None,
        verified: bool | None = None,
        monetization_mode: DealMonetizationMode | None = None,
    ) -> dict[str, object]:
        where_sql, params = self._build_filter_sql(
            q=q,
            platform=platform,
            category=category,
            country=country,
            ships_to=ships_to,
            delivery_region=delivery_region,
            min_discount=min_discount,
            min_rating=min_rating,
            max_price_usd=max_price_usd,
            free_shipping=free_shipping,
            verified=verified,
            monetization_mode=monetization_mode,
        )

        with get_connection() as connection:
            # Facets need only a small subset of deal columns. Materializing the
            # complete rows copied descriptions, image URLs, affiliate URLs, and
            # other large text fields into a temporary table on every cold request.
            # Keep the exact same filter and dedupe semantics, but rank and retain
            # only the columns required by the facet calculations.
            connection.execute("DROP TABLE IF EXISTS temp_facet_deals")
            connection.execute(
                f"""
                CREATE TEMP TABLE temp_facet_deals AS
                WITH filtered_facet_deals AS (
                    SELECT
                        id,
                        platform,
                        category,
                        currency,
                        monetization_mode,
                        availability_countries,
                        is_global,
                        delivery_regions,
                        ships_to,
                        current_price_usd,
                        discount_percent,
                        deal_score,
                        updated_at,
                        {SQL_DEDUPE_KEY} AS dedupe_key
                    FROM deals
                    {where_sql}
                ),
                ranked_facet_deals AS (
                    SELECT
                        platform,
                        category,
                        currency,
                        monetization_mode,
                        availability_countries,
                        is_global,
                        delivery_regions,
                        ships_to,
                        current_price_usd,
                        discount_percent,
                        ROW_NUMBER() OVER (
                            PARTITION BY dedupe_key
                            ORDER BY deal_score DESC, updated_at DESC, id ASC
                        ) AS dedupe_rank
                    FROM filtered_facet_deals
                )
                SELECT
                    platform,
                    category,
                    currency,
                    monetization_mode,
                    availability_countries,
                    is_global,
                    delivery_regions,
                    ships_to,
                    current_price_usd,
                    discount_percent
                FROM ranked_facet_deals
                WHERE dedupe_rank = 1
                """,
                params,
            )

            total_row = connection.execute(
                "SELECT COUNT(*) AS total FROM temp_facet_deals"
            ).fetchone()
            range_row = connection.execute(
                """
                SELECT
                    MIN(current_price_usd) AS min_price_usd,
                    MAX(current_price_usd) AS max_price_usd,
                    MIN(discount_percent) AS min_discount,
                    MAX(discount_percent) AS max_discount
                FROM temp_facet_deals
                """
            ).fetchone()

            platforms = self._facet_counts_from_temp(connection, "platform")
            categories = self._facet_counts_from_temp(connection, "category")
            currencies = self._facet_counts_from_temp(connection, "currency")
            monetization_modes = self._facet_counts_from_temp(connection, "monetization_mode")

            country_rows = connection.execute(
                "SELECT availability_countries, is_global FROM temp_facet_deals"
            ).fetchall()

            delivery_region_rows = connection.execute(
                "SELECT delivery_regions FROM temp_facet_deals"
            ).fetchall()

            ships_rows = connection.execute(
                "SELECT ships_to FROM temp_facet_deals"
            ).fetchall()

        countries = self._availability_country_counts(country_rows)
        shipping_countries = self._shipping_country_counts(ships_rows)
        delivery_regions = self._delivery_region_counts(delivery_region_rows)
        total = int(total_row["total"] if total_row is not None else 0)

        return {
            "total": total,
            "marketplaces": platforms,
            "categories": categories,
            "countries": countries,
            "shipping_countries": shipping_countries,
            "delivery_regions": delivery_regions,
            "currencies": currencies,
            "monetization_modes": monetization_modes,
            "min_price_usd": self._optional_float(range_row, "min_price_usd"),
            "max_price_usd": self._optional_float(range_row, "max_price_usd"),
            "min_discount": self._optional_int(range_row, "min_discount"),
            "max_discount": self._optional_int(range_row, "max_discount"),
        }

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
                f"SELECT DISTINCT category FROM deals WHERE TRIM(category) <> '' AND {SQL_REAL_DISCOUNT_ONLY} AND {SQL_NOT_EXPIRED_DEAL_ONLY} AND {SQL_PUBLIC_FRESH_DEAL_ONLY} ORDER BY category ASC"
            ).fetchall()
        return [str(row["category"]) for row in rows]

    def get_marketplaces(self) -> list[str]:
        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT platform AS platform, COUNT(*) AS count
                FROM deals
                WHERE TRIM(platform) <> '' AND {SQL_REAL_DISCOUNT_ONLY} AND {SQL_NOT_EXPIRED_DEAL_ONLY} AND {SQL_PUBLIC_FRESH_DEAL_ONLY}
                GROUP BY platform
                ORDER BY count DESC, platform ASC
                """
            ).fetchall()
        return [str(row["platform"]) for row in rows]

    def record_click(
        self,
        *,
        deal_id: str,
        platform: str,
        category: str,
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
                INSERT INTO click_events (
                    deal_id, platform, category, provider_id, monetization_mode,
                    target_url, referrer, user_agent, ip_address, clicked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deal_id,
                    platform,
                    category,
                    provider_id,
                    monetization_mode,
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
                    provider_id,
                    monetization_mode,
                    COUNT(*) AS clicks,
                    MAX(clicked_at) AS last_clicked_at
                FROM click_events
                GROUP BY deal_id, platform, category, provider_id, monetization_mode
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

    def delete_stale_provider_deals(self, *, provider_id: str, older_than: datetime) -> int:
        """Delete provider rows that were not refreshed by recent successful syncs.

        Feed providers are incremental by design, but affiliate catalogues such as
        AliExpress can remove products without sending an explicit tombstone. This
        cleanup prevents the database from accumulating product cards that have
        disappeared from the source feed.
        """
        provider = str(provider_id or "").strip()
        if not provider:
            return 0

        with get_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM deals
                WHERE provider_id = ?
                  AND datetime(updated_at) < datetime(?)
                """,
                (provider, older_than.astimezone(timezone.utc).isoformat()),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

    def delete_provider_deals(self, *, provider_id: str) -> int:
        provider = str(provider_id or "").strip()
        if not provider:
            return 0
        with get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM deals WHERE provider_id = ?",
                (provider,),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

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
                    provider_id,
                    monetization_mode,
                    rating,
                    review_count,
                    free_shipping,
                    verified,
                    ships_to,
                    availability_countries,
                    is_global,
                    delivery_regions,
                    hot_deal,
                    lowest_price,
                    deal_score,
                    updated_at,
                    expires_at,
                    public_platform,
                    discount_percent,
                    current_price_usd,
                    search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    provider_id = excluded.provider_id,
                    monetization_mode = excluded.monetization_mode,
                    rating = excluded.rating,
                    review_count = excluded.review_count,
                    free_shipping = excluded.free_shipping,
                    verified = excluded.verified,
                    ships_to = excluded.ships_to,
                    availability_countries = excluded.availability_countries,
                    is_global = excluded.is_global,
                    delivery_regions = excluded.delivery_regions,
                    hot_deal = excluded.hot_deal,
                    lowest_price = excluded.lowest_price,
                    deal_score = excluded.deal_score,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at,
                    public_platform = excluded.public_platform,
                    discount_percent = excluded.discount_percent,
                    current_price_usd = excluded.current_price_usd,
                    search_text = excluded.search_text
                """,
                [self._deal_to_values(deal) for deal in deals],
            )
            connection.commit()

    def _build_filter_sql(
        self,
        *,
        q: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        country: str | None = None,
        ships_to: str | None = None,
        delivery_region: str | None = None,
        min_discount: int | None = None,
        min_rating: float | None = None,
        max_price_usd: float | None = None,
        free_shipping: bool | None = None,
        verified: bool | None = None,
        monetization_mode: DealMonetizationMode | None = None,
    ) -> tuple[str, tuple[object, ...]]:
        clauses: list[str] = [SQL_REAL_DISCOUNT_ONLY, SQL_NOT_EXPIRED_DEAL_ONLY]
        params: list[object] = []

        for keyword in BAD_DEAL_KEYWORDS:
            clauses.append("search_text NOT LIKE ?")
            params.append(f"%{keyword}%")

        if q:
            query = f"%{q.strip().lower()}%"
            clauses.append("search_text LIKE ?")
            params.append(query)

        platform_values = self._split_filter_values(platform)
        if platform_values:
            placeholders = ", ".join("?" for _ in platform_values)
            clauses.append(f"(LOWER(platform) IN ({placeholders}) OR LOWER(public_platform) IN ({placeholders}))")
            lowered_platform_values = [value.lower() for value in platform_values]
            params.extend(lowered_platform_values)
            params.extend(lowered_platform_values)

        category_values = self._split_filter_values(category)
        if category_values:
            placeholders = ", ".join("?" for _ in category_values)
            clauses.append(f"LOWER(category) IN ({placeholders})")
            params.extend(value.lower() for value in category_values)

        country_code = normalize_country_code(country)
        if country_code:
            clauses.append("(is_global = 1 OR availability_countries LIKE ?)")
            params.append(f'%"{country_code}"%')

        if ships_to:
            shipping_country = normalize_country_code(ships_to)
            if shipping_country:
                clauses.append("ships_to LIKE ?")
                params.append(f'%"{shipping_country}"%')

        delivery_region_values = self._delivery_region_filter_values(delivery_region)
        if delivery_region_values:
            clauses.append("(" + " OR ".join("delivery_regions LIKE ?" for _ in delivery_region_values) + ")")
            params.extend(f'%"{region}"%' for region in delivery_region_values)

        if min_discount is not None:
            clauses.append(f"{SQL_DISCOUNT_PERCENT} >= ?")
            params.append(min_discount)

        if min_rating is not None:
            clauses.append("rating >= ?")
            params.append(min_rating)

        if max_price_usd is not None:
            clauses.append(f"{SQL_CURRENT_PRICE_USD} <= ?")
            params.append(max_price_usd)

        if free_shipping is not None:
            clauses.append("free_shipping = ?")
            params.append(1 if free_shipping else 0)

        if verified is not None:
            clauses.append("verified = ?")
            params.append(1 if verified else 0)

        if monetization_mode is not None:
            clauses.append("monetization_mode = ?")
            params.append(monetization_mode)

        clauses.append(SQL_PUBLIC_FRESH_DEAL_ONLY)

        where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where_sql, tuple(params)

    def _sort_sql(self, sort: DealSort) -> str:
        # Always include id as a final tie-breaker. Without a stable order, SQLite can
        # return equal-score/equal-discount rows in different order between pages,
        # which looks like duplicated cards in infinite scroll.
        if sort == "discount_desc":
            return "ORDER BY discount_percent DESC, deal_score DESC, updated_at DESC, id ASC"
        if sort == "price_asc":
            return "ORDER BY current_price_usd ASC, deal_score DESC, updated_at DESC, id ASC"
        if sort == "price_desc":
            return "ORDER BY current_price_usd DESC, deal_score DESC, updated_at DESC, id ASC"
        if sort == "rating_desc":
            return "ORDER BY rating DESC, review_count DESC, deal_score DESC, updated_at DESC, id ASC"
        if sort == "newest":
            return "ORDER BY updated_at DESC, deal_score DESC, id ASC"
        return "ORDER BY deal_score DESC, updated_at DESC, id ASC"

    def _dedupe_cte_sql(self, where_sql: str) -> str:
        return f"""
        WITH filtered_deals AS (
            SELECT
                *,
                {SQL_DEDUPE_KEY} AS dedupe_key
            FROM deals
            {where_sql}
        ),
        ranked_deals AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedupe_key
                    ORDER BY deal_score DESC, updated_at DESC, id ASC
                ) AS dedupe_rank
            FROM filtered_deals
        )
        """

    def _facet_counts_from_temp(
        self,
        connection: sqlite3.Connection,
        column: str,
    ) -> list[dict[str, object]]:
        allowed_columns = {"platform", "category", "currency", "monetization_mode"}
        if column not in allowed_columns:
            raise ValueError(f"Unsupported facet column: {column}")

        value_sql = column
        rows = connection.execute(
            f"""
            SELECT {value_sql} AS value, COUNT(*) AS count
            FROM temp_facet_deals
            GROUP BY {value_sql}
            HAVING TRIM(COALESCE({value_sql}, '')) <> ''
            ORDER BY count DESC, value ASC
            LIMIT 200
            """
        ).fetchall()

        return [
            {
                "id": str(row["value"]),
                "name": str(row["value"]),
                "count": int(row["count"]),
            }
            for row in rows
        ]

    def _facet_counts(
        self,
        connection: sqlite3.Connection,
        column: str,
        where_sql: str,
        params: tuple[object, ...],
    ) -> list[dict[str, object]]:
        allowed_columns = {"platform", "category", "currency", "monetization_mode"}
        if column not in allowed_columns:
            raise ValueError(f"Unsupported facet column: {column}")

        value_sql = column

        rows = connection.execute(
            f"""
            {where_sql}
            SELECT {value_sql} AS value, COUNT(*) AS count
            FROM ranked_deals
            WHERE dedupe_rank = 1
            GROUP BY {value_sql}
            HAVING TRIM(COALESCE({value_sql}, '')) <> ''
            ORDER BY count DESC, value ASC
            LIMIT 200
            """,
            params,
        ).fetchall()

        return [
            {
                "id": str(row["value"]),
                "name": str(row["value"]),
                "count": int(row["count"]),
            }
            for row in rows
        ]

    def _availability_country_counts(self, rows: list[sqlite3.Row]) -> list[dict[str, object]]:
        explicit: Counter[str] = Counter()
        global_count = 0
        for row in rows:
            if bool(row["is_global"]):
                global_count += 1
            raw = row["availability_countries"] or "[]"
            try:
                values = json.loads(raw)
            except json.JSONDecodeError:
                values = []
            if not isinstance(values, list):
                continue
            for value in values:
                code = normalize_country_code(value)
                if code:
                    explicit[code] += 1

        candidate_codes = set(explicit)
        if global_count:
            candidate_codes.update(SUPPORTED_FILTER_COUNTRIES)

        ranked = sorted(
            candidate_codes,
            key=lambda code: (-(explicit[code] + global_count), country_name(code), code),
        )
        return [
            {
                "id": code,
                "name": country_name(code),
                "count": explicit[code] + global_count,
            }
            for code in ranked[:200]
            if explicit[code] + global_count > 0
        ]

    def _shipping_country_counts(self, rows: list[sqlite3.Row]) -> list[dict[str, object]]:
        counter: Counter[str] = Counter()
        for row in rows:
            ships_to_raw = row["ships_to"] or "[]"
            try:
                countries = json.loads(ships_to_raw)
            except json.JSONDecodeError:
                countries = []
            if not isinstance(countries, list):
                continue
            for country in countries:
                value = str(country).strip().upper()
                if value:
                    counter[value] += 1

        return [
            {"id": country, "name": country, "count": count}
            for country, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:200]
        ]

    def _delivery_region_counts(self, rows: list[sqlite3.Row]) -> list[dict[str, object]]:
        counter: Counter[str] = Counter()
        names = {
            "global": "Global",
            "cis": "CIS",
            "europe": "Europe",
            "usa": "USA",
            "latam": "Latin America",
        }
        order = ["global", "cis", "europe", "usa", "latam"]

        for row in rows:
            raw = row["delivery_regions"] if "delivery_regions" in row.keys() else "[]"
            try:
                values = json.loads(raw or "[]")
            except json.JSONDecodeError:
                values = []
            for value in self._normalize_delivery_regions(values):
                counter[value] += 1

        return [
            {"id": region, "name": names[region], "count": counter[region]}
            for region in order
            if counter[region] > 0
        ]

    def _split_filter_values(self, value: str | None) -> list[str]:
        if not value:
            return []

        values: list[str] = []
        for raw_item in str(value).split(","):
            item = raw_item.strip()
            if not item or item.lower() == "all":
                continue
            if item not in values:
                values.append(item)
        return values

    def _delivery_region_filter_values(self, value: str | None) -> list[str]:
        if value is None:
            return []
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "all": "",
            "any": "",
            "global": "global",
            "worldwide": "global",
            "cis": "cis",
            "sng": "cis",
            "снг": "cis",
            "europe": "europe",
            "eu": "europe",
            "usa": "usa",
            "us": "usa",
            "latam": "latam",
            "latin_america": "latam",
        }
        region = aliases.get(normalized, normalized)
        if not region:
            return []
        if region == "global":
            return ["global"]
        if region in {"cis", "europe", "usa", "latam"}:
            return [region, "global"]
        return []

    def _normalize_delivery_regions(self, raw_values: object) -> list[str]:
        if not isinstance(raw_values, list):
            return []

        aliases = {
            "global": "global",
            "worldwide": "global",
            "international": "global",
            "cis": "cis",
            "sng": "cis",
            "снг": "cis",
            "europe": "europe",
            "eu": "europe",
            "usa": "usa",
            "us": "usa",
            "united_states": "usa",
            "latam": "latam",
            "latin_america": "latam",
        }
        normalized: list[str] = []
        for value in raw_values:
            key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
            mapped = aliases.get(key)
            if mapped and mapped not in normalized:
                normalized.append(mapped)
        return normalized

    def _delivery_regions_for_deal(self, deal: Deal) -> list[str]:
        explicit = self._normalize_delivery_regions(deal.delivery_regions)
        if explicit:
            return explicit

        text = " ".join(
            str(part or "")
            for part in (deal.platform, deal.provider_id, deal.product_url, deal.affiliate_url)
        ).lower().replace("-", "_")

        if "aliexpress" in text:
            return ["global", "cis", "europe", "usa", "latam"]
        if "mercado libre" in text or "mercadolibre" in text:
            return ["latam"]
        if "ebay_us" in text or "ebay us" in text or "motors_us" in text:
            return ["usa"]
        if any(value in text for value in ("ebay_gb", "ebay gb", "ebay_de", "ebay de", "ebay_fr", "ebay fr", "ebay_it", "ebay it", "ebay_es", "ebay es")):
            return ["europe"]
        if "ebay_au" in text or "ebay au" in text:
            return ["global"]

        countries = {str(country).upper().strip() for country in deal.ships_to}
        if countries & {"UZ", "KZ", "KG", "TJ", "TM", "AZ", "AM", "GE", "MD", "BY"}:
            return ["cis"]
        if countries & {"US", "USA"}:
            return ["usa"]
        if countries & {"GB", "UK", "DE", "FR", "IT", "ES", "PL", "NL", "BE", "AT", "SE", "NO", "DK", "FI", "IE", "PT", "CZ", "SK", "HU", "RO", "BG", "GR"}:
            return ["europe"]
        if countries & {"MX", "BR", "AR", "CL", "CO", "PE", "UY", "EC", "VE", "PY", "BO"}:
            return ["latam"]

        return ["global"]

    def _optional_float(self, row: sqlite3.Row | None, key: str) -> float | None:
        if row is None or row[key] is None:
            return None
        return float(row[key])

    def _optional_int(self, row: sqlite3.Row | None, key: str) -> int | None:
        if row is None or row[key] is None:
            return None
        return round(float(row[key]))

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
            deal.provider_id,
            deal.monetization_mode,
            deal.rating,
            deal.review_count,
            int(deal.free_shipping),
            int(deal.verified),
            json.dumps(deal.ships_to),
            json.dumps(deal.availability_countries),
            int(deal.is_global),
            json.dumps(self._delivery_regions_for_deal(deal)),
            int(deal.hot_deal),
            int(deal.lowest_price),
            deal.deal_score,
            deal.updated_at.isoformat(),
            deal.expires_at.isoformat() if deal.expires_at else None,
            self._public_marketplace_label(deal.platform),
            self._discount_percent(deal.old_price, deal.current_price),
            self._current_price_usd(deal.current_price, deal.currency),
            self._search_text(deal),
        )


    def _public_marketplace_label(self, value: str) -> str:
        platform = str(value or "").strip()
        normalized = platform.lower().replace("-", " ").replace("_", " ")
        for prefix, label in PUBLIC_MARKETPLACE_RULES:
            if normalized.startswith(prefix):
                return label
        return platform

    def _discount_percent(self, old_price: float, current_price: float) -> float:
        if old_price <= 0:
            return 0.0
        return round(((old_price - current_price) / old_price) * 100, 2)

    def _current_price_usd(self, current_price: float, currency: str) -> float:
        rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.78,
            "AUD": 1.52,
            "CNY": 6.76,
            "UZS": 12650.0,
            "TRY": 32.5,
            "AED": 3.67,
            "MXN": 18.5,
            "BRL": 5.4,
            "ARS": 1100.0,
            "CLP": 950.0,
            "COP": 4200.0,
            "PEN": 3.7,
            "UYU": 40.0,
        }
        rate = rates.get(str(currency or "USD").upper(), 1.0)
        return round(current_price / rate, 6)

    def _search_text(self, deal: Deal) -> str:
        return " ".join(
            [
                deal.title,
                deal.description,
                deal.platform,
                self._public_marketplace_label(deal.platform),
                deal.category,
            ]
        ).lower()

    def _row_to_deal(self, row: sqlite3.Row) -> Deal:
        ships_to_raw = row["ships_to"] or "[]"
        try:
            ships_to = json.loads(ships_to_raw)
        except json.JSONDecodeError:
            ships_to = []

        availability_raw = row["availability_countries"] if "availability_countries" in row.keys() else "[]"
        try:
            parsed_availability = json.loads(availability_raw or "[]")
        except json.JSONDecodeError:
            parsed_availability = []
        if not isinstance(parsed_availability, list):
            parsed_availability = []

        delivery_regions_raw = row["delivery_regions"] if "delivery_regions" in row.keys() else "[]"
        try:
            parsed_delivery_regions = json.loads(delivery_regions_raw or "[]")
        except json.JSONDecodeError:
            parsed_delivery_regions = []
        if not isinstance(parsed_delivery_regions, list):
            parsed_delivery_regions = []

        raw_monetization_mode = str(row["monetization_mode"] or "direct").strip()
        if raw_monetization_mode not in ("affiliate", "direct", "pending_affiliate"):
            raw_monetization_mode = "direct"

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
            provider_id=str(row["provider_id"]) if row["provider_id"] else None,
            monetization_mode=raw_monetization_mode,  # type: ignore[arg-type]
            rating=float(row["rating"]),
            review_count=int(row["review_count"]),
            free_shipping=bool(row["free_shipping"]),
            verified=bool(row["verified"]),
            ships_to=[str(item).upper() for item in ships_to],
            availability_countries=[
                code for item in parsed_availability if (code := normalize_country_code(item))
            ],
            is_global=bool(row["is_global"]) if "is_global" in row.keys() else False,
            delivery_regions=self._normalize_delivery_regions(parsed_delivery_regions),
            hot_deal=bool(row["hot_deal"]),
            lowest_price=bool(row["lowest_price"]),
            deal_score=int(row["deal_score"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])) if row["expires_at"] else None,
        )
