from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import get_settings
from app.db.schema import (
    CREATE_CLICK_EVENTS_INDEXES_SQL,
    CREATE_CLICK_EVENTS_TABLE_SQL,
    CREATE_DEALS_INDEXES_SQL,
    CREATE_DEALS_TABLE_SQL,
    CREATE_FEED_PROVIDERS_INDEXES_SQL,
    CREATE_FEED_PROVIDERS_TABLE_SQL,
    CREATE_FEED_SYNC_RUNS_INDEXES_SQL,
    CREATE_FEED_SYNC_RUNS_TABLE_SQL,
)


def get_database_path() -> Path:
    return get_settings().resolved_database_path


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _column_exists(connection: sqlite3.Connection, *, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row["name"]) == column for row in rows)


def _ensure_column(connection: sqlite3.Connection, *, table: str, column: str, definition: str) -> None:
    if not _column_exists(connection, table=table, column=column):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_database() -> None:
    from app.data.mock_deals import MOCK_DEALS
    from app.repositories.deals_repository import DealsRepository

    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute(CREATE_DEALS_TABLE_SQL)
        for statement in CREATE_DEALS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_FEED_PROVIDERS_TABLE_SQL)
        _ensure_column(
            connection,
            table="feed_providers",
            column="adapter",
            definition="TEXT NOT NULL DEFAULT 'auto'",
        )
        for statement in CREATE_FEED_PROVIDERS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_FEED_SYNC_RUNS_TABLE_SQL)
        for statement in CREATE_FEED_SYNC_RUNS_INDEXES_SQL:
            connection.execute(statement)

        connection.execute(CREATE_CLICK_EVENTS_TABLE_SQL)
        for statement in CREATE_CLICK_EVENTS_INDEXES_SQL:
            connection.execute(statement)

        connection.commit()

    repository = DealsRepository()
    if repository.count_deals() == 0:
        repository.upsert_many(MOCK_DEALS)
