from __future__ import annotations

import sqlite3
from datetime import datetime

from app.db.database import get_connection
from app.models.feed_provider import FeedProvider


class FeedProvidersRepository:
    def list_providers(self, *, enabled_only: bool = False) -> list[FeedProvider]:
        query = "SELECT * FROM feed_providers"
        params: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY updated_at DESC"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_provider(row) for row in rows]

    def get_provider(self, provider_id: str) -> FeedProvider | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM feed_providers WHERE id = ?",
                (provider_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_provider(row)

    def upsert_provider(self, provider: FeedProvider) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO feed_providers (
                    id,
                    name,
                    url,
                    adapter,
                    enabled,
                    replace_on_sync,
                    last_sync_at,
                    last_status,
                    last_message,
                    last_imported_count,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    url = excluded.url,
                    adapter = excluded.adapter,
                    enabled = excluded.enabled,
                    replace_on_sync = excluded.replace_on_sync,
                    updated_at = excluded.updated_at
                """,
                self._provider_to_values(provider),
            )
            connection.commit()

    def update_sync_result(
        self,
        provider_id: str,
        *,
        status: str,
        message: str,
        imported_count: int,
        synced_at: datetime,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE feed_providers
                SET
                    last_sync_at = ?,
                    last_status = ?,
                    last_message = ?,
                    last_imported_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    synced_at.isoformat(),
                    status,
                    message,
                    imported_count,
                    synced_at.isoformat(),
                    provider_id,
                ),
            )
            connection.commit()

    def delete_provider(self, provider_id: str) -> bool:
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM feed_providers WHERE id = ?", (provider_id,))
            connection.commit()
        return cursor.rowcount > 0

    def count_providers(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM feed_providers").fetchone()
        return int(row["total"] if row is not None else 0)

    def _provider_to_values(self, provider: FeedProvider) -> tuple[object, ...]:
        return (
            provider.id,
            provider.name,
            provider.url,
            provider.adapter,
            int(provider.enabled),
            int(provider.replace_on_sync),
            provider.last_sync_at.isoformat() if provider.last_sync_at else None,
            provider.last_status,
            provider.last_message,
            provider.last_imported_count,
            provider.created_at.isoformat(),
            provider.updated_at.isoformat(),
        )

    def _row_to_provider(self, row: sqlite3.Row) -> FeedProvider:
        return FeedProvider(
            id=str(row["id"]),
            name=str(row["name"]),
            url=str(row["url"]),
            adapter=str(row["adapter"] or "auto"),
            enabled=bool(row["enabled"]),
            replace_on_sync=bool(row["replace_on_sync"]),
            last_sync_at=datetime.fromisoformat(str(row["last_sync_at"])) if row["last_sync_at"] else None,
            last_status=str(row["last_status"]) if row["last_status"] else None,
            last_message=str(row["last_message"]) if row["last_message"] else None,
            last_imported_count=int(row["last_imported_count"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
