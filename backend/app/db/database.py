from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import get_settings

SQL_PERF_RATE_CASE = """
CASE UPPER(currency)
    WHEN 'USD' THEN 1.0
    WHEN 'EUR' THEN 0.92
    WHEN 'GBP' THEN 0.78
    WHEN 'AUD' THEN 1.52
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

SQL_PERF_PUBLIC_PLATFORM = """
CASE
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'ebay%' THEN 'eBay'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'aliexpress%' THEN 'AliExpress'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'alibaba%' THEN 'Alibaba'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'amazon%' THEN 'Amazon'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'shein%' THEN 'SHEIN'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'dhgate%' THEN 'DHgate'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'rakuten%' THEN 'Rakuten'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'back market%' THEN 'Back Market'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'backmarket%' THEN 'Back Market'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'cdiscount%' THEN 'Cdiscount'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'xiaomi%' THEN 'Xiaomi'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'geekbuying%' THEN 'Geekbuying'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'banggood%' THEN 'Banggood'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'temu%' THEN 'Temu'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'iherb%' THEN 'iHerb'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'lookfantastic%' THEN 'LOOKFANTASTIC'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'myprotein%' THEN 'Myprotein'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'sephora%' THEN 'Sephora'
    WHEN LOWER(TRIM(COALESCE(platform, ''))) LIKE 'decathlon%' THEN 'Decathlon'
    ELSE TRIM(COALESCE(platform, ''))
END
""".strip()


from app.db.schema import (
    CREATE_CLICK_EVENTS_INDEXES_SQL,
    CREATE_CLICK_EVENTS_TABLE_SQL,
    CREATE_DEALS_INDEXES_SQL,
    CREATE_DEALS_TABLE_SQL,
    CREATE_FEED_PROVIDERS_INDEXES_SQL,
    CREATE_FEED_PROVIDERS_TABLE_SQL,
    CREATE_FEED_SYNC_RUNS_INDEXES_SQL,
    CREATE_FEED_SYNC_RUNS_TABLE_SQL,
    CREATE_PROMOTION_CLICK_EVENTS_INDEXES_SQL,
    CREATE_PROMOTION_CLICK_EVENTS_TABLE_SQL,
    CREATE_PROMOTIONS_INDEXES_SQL,
    CREATE_PROMOTIONS_TABLE_SQL,
)


def get_database_path() -> Path:
    return get_settings().resolved_database_path


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    # These pragmas keep large feed reads and filter queries responsive on the
    # local SQLite database. They are safe for the single-process FastAPI app and
    # reduce stalls during Awin/eBay syncs and live Flutter filters.
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA cache_size=-32000")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _column_exists(connection: sqlite3.Connection, *, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row["name"]) == column for row in rows)


def _ensure_column(connection: sqlite3.Connection, *, table: str, column: str, definition: str) -> None:
    if not _column_exists(connection, table=table, column=column):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_deals_migrations(connection: sqlite3.Connection) -> None:
    _ensure_column(
        connection,
        table="deals",
        column="provider_id",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table="deals",
        column="monetization_mode",
        definition="TEXT NOT NULL DEFAULT 'direct'",
    )

    _ensure_column(
        connection,
        table="deals",
        column="delivery_regions",
        definition="TEXT NOT NULL DEFAULT '[]'",
    )

    # Backfill delivery-region buckets without reading any user location. These
    # are product/source capabilities used by the public catalog filter.
    connection.execute(
        """
        UPDATE deals
        SET delivery_regions = CASE
            WHEN LOWER(COALESCE(platform, '')) LIKE '%aliexpress%'
                THEN '["global","cis","europe","usa","latam"]'
            WHEN LOWER(COALESCE(platform, '')) LIKE '%mercado libre%'
                THEN '["latam"]'
            WHEN LOWER(COALESCE(platform, '')) LIKE 'ebay us%'
              OR LOWER(COALESCE(platform, '')) LIKE '%motors_us%'
              OR LOWER(COALESCE(provider_id, '')) LIKE '%ebay%us%'
                THEN '["usa"]'
            WHEN LOWER(COALESCE(platform, '')) LIKE 'ebay gb%'
              OR LOWER(COALESCE(platform, '')) LIKE 'ebay de%'
              OR LOWER(COALESCE(platform, '')) LIKE 'ebay fr%'
              OR LOWER(COALESCE(platform, '')) LIKE 'ebay it%'
              OR LOWER(COALESCE(platform, '')) LIKE 'ebay es%'
                THEN '["europe"]'
            WHEN LOWER(COALESCE(platform, '')) LIKE 'ebay au%'
                THEN '["global"]'
            ELSE '["global"]'
        END
        WHERE delivery_regions IS NULL
           OR TRIM(delivery_regions) = ''
           OR TRIM(delivery_regions) = '[]'
        """
    )

    # Existing rows from older builds did not know whether a link was affiliate/direct.
    # Use affiliate_url as the safest backwards-compatible signal.
    connection.execute(
        """
        UPDATE deals
        SET monetization_mode = 'affiliate'
        WHERE affiliate_url IS NOT NULL
          AND TRIM(affiliate_url) <> ''
          AND TRIM(affiliate_url) <> TRIM(product_url)
          AND (monetization_mode IS NULL OR TRIM(monetization_mode) = '' OR monetization_mode = 'direct')
        """
    )
    connection.execute(
        """
        UPDATE deals
        SET monetization_mode = 'direct'
        WHERE monetization_mode IS NULL
           OR TRIM(monetization_mode) = ''
           OR monetization_mode NOT IN ('affiliate', 'direct', 'pending_affiliate')
        """
    )




def _ensure_deals_performance_migrations(connection: sqlite3.Connection) -> None:
    _ensure_column(
        connection,
        table="deals",
        column="public_platform",
        definition="TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        connection,
        table="deals",
        column="discount_percent",
        definition="REAL NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table="deals",
        column="current_price_usd",
        definition="REAL NOT NULL DEFAULT 0",
    )
    _ensure_column(
        connection,
        table="deals",
        column="search_text",
        definition="TEXT NOT NULL DEFAULT ''",
    )

    # Backfill existing rows once after the migration. New/updated rows are
    # populated by DealsRepository.upsert_many(). Keeping these values materialized
    # avoids recalculating public marketplace, FX price and discount for every
    # /deals and /deals/facets request.
    connection.execute(
        f"""
        UPDATE deals
        SET
            public_platform = {SQL_PERF_PUBLIC_PLATFORM},
            discount_percent = CASE
                WHEN old_price > 0 THEN ROUND(((old_price - current_price) / old_price) * 100, 2)
                ELSE 0
            END,
            current_price_usd = current_price / ({SQL_PERF_RATE_CASE}),
            search_text = LOWER(
                COALESCE(title, '') || ' ' ||
                COALESCE(description, '') || ' ' ||
                COALESCE(platform, '') || ' ' ||
                COALESCE(category, '')
            )
        WHERE public_platform = ''
           OR search_text = ''
           OR current_price_usd <= 0
        """
    )

def _ensure_click_events_migrations(connection: sqlite3.Connection) -> None:
    _ensure_column(
        connection,
        table="click_events",
        column="provider_id",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table="click_events",
        column="monetization_mode",
        definition="TEXT NOT NULL DEFAULT 'direct'",
    )
    connection.execute(
        """
        UPDATE click_events
        SET monetization_mode = 'direct'
        WHERE monetization_mode IS NULL
           OR TRIM(monetization_mode) = ''
           OR monetization_mode NOT IN ('affiliate', 'direct', 'pending_affiliate')
        """
    )




def _ensure_promotions_migrations(connection: sqlite3.Connection) -> None:
    _ensure_column(
        connection,
        table="promotions",
        column="search_text",
        definition="TEXT NOT NULL DEFAULT ''",
    )
    connection.execute(
        """
        UPDATE promotions
        SET search_text = LOWER(
            COALESCE(title, '') || ' ' ||
            COALESCE(description, '') || ' ' ||
            COALESCE(store, '') || ' ' ||
            COALESCE(discount_text, '') || ' ' ||
            COALESCE(code, '') || ' ' ||
            COALESCE(type, '')
        )
        WHERE search_text IS NULL OR TRIM(search_text) = ''
        """
    )


def _ensure_promotion_click_events_migrations(connection: sqlite3.Connection) -> None:
    _ensure_column(
        connection,
        table="promotion_click_events",
        column="provider_id",
        definition="TEXT",
    )
    _ensure_column(
        connection,
        table="promotion_click_events",
        column="monetization_mode",
        definition="TEXT NOT NULL DEFAULT 'affiliate'",
    )
    connection.execute(
        """
        UPDATE promotion_click_events
        SET monetization_mode = 'affiliate'
        WHERE monetization_mode IS NULL
           OR TRIM(monetization_mode) = ''
           OR monetization_mode NOT IN ('affiliate', 'direct', 'pending_affiliate')
        """
    )

def initialize_database() -> None:
    from app.data.mock_deals import MOCK_DEALS
    from app.repositories.deals_repository import DealsRepository

    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(CREATE_DEALS_TABLE_SQL)
        _ensure_deals_migrations(connection)
        _ensure_deals_performance_migrations(connection)
        for statement in CREATE_DEALS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_FEED_PROVIDERS_TABLE_SQL)
        _ensure_column(
            connection,
            table="feed_providers",
            column="adapter",
            definition="TEXT NOT NULL DEFAULT 'auto'",
        )
        _ensure_column(
            connection,
            table="feed_providers",
            column="monetization_mode",
            definition="TEXT NOT NULL DEFAULT 'direct'",
        )
        connection.execute(
            """
            UPDATE feed_providers
            SET monetization_mode = 'direct'
            WHERE monetization_mode IS NULL
               OR TRIM(monetization_mode) = ''
               OR monetization_mode NOT IN ('affiliate', 'direct', 'pending_affiliate')
            """
        )
        for statement in CREATE_FEED_PROVIDERS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_FEED_SYNC_RUNS_TABLE_SQL)
        for statement in CREATE_FEED_SYNC_RUNS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_CLICK_EVENTS_TABLE_SQL)
        _ensure_click_events_migrations(connection)
        for statement in CREATE_CLICK_EVENTS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_PROMOTIONS_TABLE_SQL)
        _ensure_promotions_migrations(connection)
        for statement in CREATE_PROMOTIONS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_PROMOTION_CLICK_EVENTS_TABLE_SQL)
        _ensure_promotion_click_events_migrations(connection)
        for statement in CREATE_PROMOTION_CLICK_EVENTS_INDEXES_SQL:
            connection.execute(statement)

        connection.commit()

    repository = DealsRepository()
    if repository.count_deals() == 0:
        repository.upsert_many(MOCK_DEALS)
