from __future__ import annotations

import sqlite3
from datetime import datetime

from app.db.database import get_connection
from app.models.feed_provider import FeedSyncRunResponse


class FeedSyncRunsRepository:
    def add_run(
        self,
        *,
        provider_id: str,
        provider_name: str | None,
        url: str,
        status: str,
        message: str,
        imported_count: int,
        deal_count: int | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
        created_at = finished_at

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO feed_sync_runs (
                    provider_id,
                    provider_name,
                    url,
                    status,
                    message,
                    imported_count,
                    deal_count,
                    started_at,
                    finished_at,
                    duration_ms,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_id,
                    provider_name,
                    url,
                    status,
                    message,
                    imported_count,
                    deal_count,
                    started_at.isoformat(),
                    finished_at.isoformat(),
                    duration_ms,
                    created_at.isoformat(),
                ),
            )
            connection.commit()

    def list_runs(
        self,
        *,
        limit: int = 50,
        provider_id: str | None = None,
        status: str | None = None,
    ) -> list[FeedSyncRunResponse]:
        clauses: list[str] = []
        params: list[object] = []

        if provider_id:
            clauses.append("provider_id = ?")
            params.append(provider_id)
        if status:
            clauses.append("status = ?")
            params.append(status)

        query = "SELECT * FROM feed_sync_runs"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY started_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with get_connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_response(row) for row in rows]

    def clear_runs(self) -> int:
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM feed_sync_runs")
            connection.commit()
        return int(cursor.rowcount)

    def count_runs(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM feed_sync_runs").fetchone()
        return int(row["total"] if row is not None else 0)

    def _row_to_response(self, row: sqlite3.Row) -> FeedSyncRunResponse:
        return FeedSyncRunResponse(
            id=int(row["id"]),
            provider_id=str(row["provider_id"]),
            provider_name=str(row["provider_name"]) if row["provider_name"] else None,
            url=str(row["url"]),
            status=str(row["status"]),
            message=str(row["message"]),
            imported_count=int(row["imported_count"]),
            deal_count=int(row["deal_count"]) if row["deal_count"] is not None else None,
            started_at=datetime.fromisoformat(str(row["started_at"])),
            finished_at=datetime.fromisoformat(str(row["finished_at"])),
            duration_ms=int(row["duration_ms"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


feed_sync_runs_repository = FeedSyncRunsRepository()
