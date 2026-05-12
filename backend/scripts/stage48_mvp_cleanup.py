from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.category_normalizer import normalize_category  # noqa: E402

KNOWN_SAMPLE_PROVIDER_IDS = (
    "demo_feed",
    "generic_feed",
    "google_merchant_demo",
    "awin_demo",
    "affiliate_csv_global",
    "awin_fashion_global",
)

SAMPLE_PLATFORM_NAMES = (
    "FeedShop",
    "Sample Audio Store",
    "Sample Sport Store",
    "Sample Tech Store",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 48 cleanup for DiscountHub MVP local SQLite database.",
    )
    parser.add_argument(
        "--db",
        default=str(BACKEND_ROOT / "data" / "discounthub.sqlite3"),
        help="Path to SQLite database. Default: backend/data/discounthub.sqlite3",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a .stage48_backup copy before cleanup.",
    )
    parser.add_argument(
        "--trim-sync-runs",
        type=int,
        default=0,
        help="Keep only the newest N feed sync runs. 0 keeps all sync history.",
    )
    return parser.parse_args()


def count_table(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0] if row else 0)


def category_counts(connection: sqlite3.Connection) -> list[tuple[str, int]]:
    return [
        (str(row[0]), int(row[1]))
        for row in connection.execute(
            "SELECT category, COUNT(*) FROM deals GROUP BY category ORDER BY COUNT(*) DESC, category ASC"
        ).fetchall()
    ]


def print_counts(connection: sqlite3.Connection, title: str) -> None:
    print(f"\n{title}")
    for table in ("deals", "feed_providers", "feed_sync_runs", "click_events"):
        try:
            print(f"- {table}: {count_table(connection, table)}")
        except sqlite3.Error:
            print(f"- {table}: missing")

    print("- top categories:")
    for category, total in category_counts(connection)[:12]:
        print(f"  {category}: {total}")


def backup_database(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.stage48_backup_{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def delete_sample_deals(connection: sqlite3.Connection) -> int:
    deleted = 0
    for platform in SAMPLE_PLATFORM_NAMES:
        cursor = connection.execute("DELETE FROM deals WHERE platform = ?", (platform,))
        deleted += int(cursor.rowcount if cursor.rowcount is not None else 0)

    patterns = (
        "feed_demo_%",
        "affiliate_csv_global_%",
        "demo_%",
        "deal_%",
    )
    for pattern in patterns:
        cursor = connection.execute("DELETE FROM deals WHERE id LIKE ?", (pattern,))
        deleted += int(cursor.rowcount if cursor.rowcount is not None else 0)

    cursor = connection.execute("DELETE FROM deals WHERE product_url LIKE '%example.com%'")
    deleted += int(cursor.rowcount if cursor.rowcount is not None else 0)
    return deleted


def delete_sample_providers(connection: sqlite3.Connection) -> int:
    placeholders = ", ".join("?" for _ in KNOWN_SAMPLE_PROVIDER_IDS)
    cursor = connection.execute(
        f"DELETE FROM feed_providers WHERE id IN ({placeholders})",
        KNOWN_SAMPLE_PROVIDER_IDS,
    )
    return int(cursor.rowcount if cursor.rowcount is not None else 0)


def normalize_existing_categories(connection: sqlite3.Connection) -> int:
    rows = connection.execute("SELECT id, category FROM deals").fetchall()
    changed = 0
    for deal_id, category in rows:
        normalized = normalize_category(str(category))
        if normalized != category:
            connection.execute(
                "UPDATE deals SET category = ? WHERE id = ?",
                (normalized, deal_id),
            )
            changed += 1
    return changed


def trim_sync_runs(connection: sqlite3.Connection, keep: int) -> int:
    if keep <= 0:
        return 0

    cursor = connection.execute(
        """
        DELETE FROM feed_sync_runs
        WHERE id NOT IN (
            SELECT id FROM feed_sync_runs ORDER BY started_at DESC, id DESC LIMIT ?
        )
        """,
        (keep,),
    )
    return int(cursor.rowcount if cursor.rowcount is not None else 0)


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).resolve()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    if not args.no_backup:
        backup_path = backup_database(db_path)
        print(f"Backup created: {backup_path}")

    with sqlite3.connect(db_path) as connection:
        print_counts(connection, "Before cleanup")

        deleted_deals = delete_sample_deals(connection)
        deleted_providers = delete_sample_providers(connection)
        normalized_categories = normalize_existing_categories(connection)
        deleted_sync_runs = trim_sync_runs(connection, args.trim_sync_runs)

        connection.commit()

        print("\nCleanup summary")
        print(f"- deleted sample/demo deals: {deleted_deals}")
        print(f"- deleted sample/demo providers: {deleted_providers}")
        print(f"- normalized deal categories: {normalized_categories}")
        if args.trim_sync_runs > 0:
            print(f"- deleted old sync runs: {deleted_sync_runs}")

        print_counts(connection, "After cleanup")

    print("\nStage 48 cleanup completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
