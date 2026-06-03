from __future__ import annotations

from app.db.database import get_connection, get_database_path, initialize_database
from app.repositories.deals_repository import BAD_DEAL_KEYWORDS


def _count_deals() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM deals").fetchone()
    return int(row["total"] if row else 0)


def _count_bad_rows() -> int:
    clauses = ["LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '')) LIKE ?" for _ in BAD_DEAL_KEYWORDS]
    params = [f"%{keyword}%" for keyword in BAD_DEAL_KEYWORDS]
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) AS total FROM deals WHERE {' OR '.join(clauses)}",
            params,
        ).fetchone()
    return int(row["total"] if row else 0)


def _delete_bad_rows() -> int:
    clauses = ["LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '')) LIKE ?" for _ in BAD_DEAL_KEYWORDS]
    params = [f"%{keyword}%" for keyword in BAD_DEAL_KEYWORDS]
    with get_connection() as connection:
        cursor = connection.execute(
            f"DELETE FROM deals WHERE {' OR '.join(clauses)}",
            params,
        )
        connection.commit()
        return int(cursor.rowcount if cursor.rowcount is not None else 0)


def _count_duplicate_rows() -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            WITH ranked AS (
                SELECT
                    rowid AS deal_rowid,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            LOWER(TRIM(COALESCE(platform, ''))),
                            LOWER(TRIM(COALESCE(title, ''))),
                            UPPER(TRIM(COALESCE(currency, ''))),
                            printf('%.2f', current_price),
                            printf('%.2f', old_price)
                        ORDER BY deal_score DESC, updated_at DESC, id ASC
                    ) AS duplicate_rank
                FROM deals
            )
            SELECT COUNT(*) AS total
            FROM ranked
            WHERE duplicate_rank > 1
            """
        ).fetchone()
    return int(row["total"] if row else 0)


def _delete_duplicate_rows() -> int:
    duplicate_count = _count_duplicate_rows()
    if duplicate_count <= 0:
        return 0

    with get_connection() as connection:
        connection.execute(
            """
            WITH ranked AS (
                SELECT
                    rowid AS deal_rowid,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            LOWER(TRIM(COALESCE(platform, ''))),
                            LOWER(TRIM(COALESCE(title, ''))),
                            UPPER(TRIM(COALESCE(currency, ''))),
                            printf('%.2f', current_price),
                            printf('%.2f', old_price)
                        ORDER BY deal_score DESC, updated_at DESC, id ASC
                    ) AS duplicate_rank
                FROM deals
            )
            DELETE FROM deals
            WHERE rowid IN (
                SELECT deal_rowid
                FROM ranked
                WHERE duplicate_rank > 1
            )
            """
        )
        connection.commit()
    return duplicate_count


def main() -> None:
    initialize_database()
    before = _count_deals()
    duplicate_before = _count_duplicate_rows()
    bad_before = _count_bad_rows()

    bad_deleted = _delete_bad_rows()
    duplicate_deleted = _delete_duplicate_rows()
    after = _count_deals()

    print("== DiscountHub Stage 55 dedupe cleanup ==")
    print(f"Database: {get_database_path()}")
    print(f"Deals before: {before}")
    print(f"Bad/parts/defect rows before: {bad_before}")
    print(f"Duplicate clone rows before: {duplicate_before}")
    print(f"Deleted bad rows: {bad_deleted}")
    print(f"Deleted duplicate clone rows: {duplicate_deleted}")
    print(f"Deals after: {after}")


if __name__ == "__main__":
    main()
