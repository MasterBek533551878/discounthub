from __future__ import annotations

import argparse
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

BAD_KEYWORDS = [
    "for parts",
    "parts only",
    "spares",
    "spare parts",
    "broken",
    "not working",
    "non working",
    "for repair",
    "repair only",
    "faulty",
    "defective",
    "damaged",
    "untested",
    "unknown condition",
    "as is",
    "read description",
    "read listing",
    "empty box",
    "box only",
    "case only",
    "manual only",
    "charger only",
    "cable only",
    "cover only",
    "shell only",
    "housing only",
    "screen protector",
    "tempered glass",
    "replacement",
    "ersatz",
    "mainboard",
    "logic board",
    "motherboard replacement",
    "lcd screen only",
    "display only",
]

PLACEHOLDER_IMAGE_MARKERS = [
    "images.unsplash.com/photo-1516321318423-f06f85e504b3",
    "example.com",
]


@dataclass(frozen=True)
class DeleteReason:
    deal_id: str
    title: str
    platform: str
    category: str
    discount_percent: float
    updated_at: str
    reason: str


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def database_path(root: Path) -> Path:
    return root / "data" / "discounthub.sqlite3"


def parse_datetime(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def discount_percent(old_price: float, current_price: float) -> float:
    if old_price <= 0:
        return 0.0
    return ((old_price - current_price) / old_price) * 100.0


def searchable(row: sqlite3.Row) -> str:
    parts = [
        row["title"],
        row["description"],
        row["category"],
        row["product_url"],
        row["affiliate_url"],
    ]
    return " ".join(str(item or "") for item in parts).lower()


def is_ebay(row: sqlite3.Row) -> bool:
    platform = str(row["platform"] or "")
    deal_id = str(row["id"] or "")
    return platform.lower().startswith("ebay") or deal_id.lower().startswith("ebay_")


def find_reason(
    row: sqlite3.Row,
    *,
    min_discount: float,
    max_discount: float,
    cutoff: datetime,
) -> tuple[str, float] | None:
    title = str(row["title"] or "")
    description = str(row["description"] or "")
    image_url = str(row["image_url"] or "").strip().lower()
    product_url = str(row["product_url"] or "").strip().lower()
    affiliate_url = str(row["affiliate_url"] or "").strip().lower()
    old_price = float(row["old_price"] or 0)
    current_price = float(row["current_price"] or 0)
    discount = discount_percent(old_price, current_price)
    updated_at = parse_datetime(row["updated_at"])

    if not title.strip() or not description.strip():
        return "missing title/description", discount
    if current_price <= 0 or old_price <= 0 or current_price >= old_price:
        return "not a confirmed discount", discount
    if discount + 0.1 < min_discount:
        return f"discount below {min_discount:g}%", discount
    if discount > max_discount:
        return f"suspicious discount above {max_discount:g}%", discount
    if not product_url.startswith("http") and not affiliate_url.startswith("http"):
        return "missing product URL", discount
    if not image_url.startswith("http"):
        return "missing image URL", discount
    if any(marker in image_url for marker in PLACEHOLDER_IMAGE_MARKERS):
        return "placeholder image", discount
    if updated_at is None:
        return "missing updated_at", discount
    if updated_at < cutoff:
        return "stale listing", discount

    text = searchable(row)
    for keyword in BAD_KEYWORDS:
        if keyword in text:
            return f"bad keyword: {keyword}", discount

    return None


def backup_database(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.stage52_backup_{stamp}")
    shutil.copy2(path, backup)
    return backup


def count_rows(connection: sqlite3.Connection, query: str, params: tuple[object, ...] = ()) -> int:
    row = connection.execute(query, params).fetchone()
    return int(row[0] if row else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove low-quality or stale eBay deals from DiscountHub SQLite storage.")
    parser.add_argument("--min-discount", type=float, default=15.0)
    parser.add_argument("--max-discount", type=float, default=95.0)
    parser.add_argument("--max-age-hours", type=float, default=72.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--sample", type=int, default=15)
    args = parser.parse_args()

    root = backend_root()
    db_path = database_path(root)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.max_age_hours)

    backup_path: Path | None = None
    if not args.dry_run and not args.no_backup:
        backup_path = backup_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        before_total = count_rows(connection, "SELECT COUNT(*) FROM deals")
        before_ebay = count_rows(connection, "SELECT COUNT(*) FROM deals WHERE lower(platform) LIKE 'ebay%' OR lower(id) LIKE 'ebay_%'")
        rows = connection.execute("SELECT * FROM deals").fetchall()

        reasons: list[DeleteReason] = []
        for row in rows:
            if not is_ebay(row):
                continue
            reason = find_reason(
                row,
                min_discount=args.min_discount,
                max_discount=args.max_discount,
                cutoff=cutoff,
            )
            if reason is None:
                continue
            reason_text, discount = reason
            reasons.append(
                DeleteReason(
                    deal_id=str(row["id"]),
                    title=str(row["title"]),
                    platform=str(row["platform"]),
                    category=str(row["category"]),
                    discount_percent=discount,
                    updated_at=str(row["updated_at"]),
                    reason=reason_text,
                )
            )

        if not args.dry_run and reasons:
            connection.executemany("DELETE FROM deals WHERE id = ?", [(item.deal_id,) for item in reasons])
            connection.commit()

        after_total = count_rows(connection, "SELECT COUNT(*) FROM deals")
        after_ebay = count_rows(connection, "SELECT COUNT(*) FROM deals WHERE lower(platform) LIKE 'ebay%' OR lower(id) LIKE 'ebay_%'")

    reason_counts: dict[str, int] = {}
    for item in reasons:
        reason_counts[item.reason] = reason_counts.get(item.reason, 0) + 1

    print("Stage 52 eBay quality + freshness cleanup")
    if backup_path:
        print(f"Backup created: {backup_path}")
    if args.dry_run:
        print("Mode: dry-run, no rows were deleted.")
    print(f"Before: total={before_total}, ebay={before_ebay}")
    print(f"After:  total={after_total}, ebay={after_ebay}")
    print(f"Matched for deletion: {len(reasons)}")
    print(f"Rules: min_discount={args.min_discount:g}%, max_discount={args.max_discount:g}%, max_age_hours={args.max_age_hours:g}")

    if reason_counts:
        print("\nDelete reasons:")
        for reason, count in sorted(reason_counts.items(), key=lambda pair: (-pair[1], pair[0])):
            print(f"- {reason}: {count}")

    if reasons:
        print("\nSample deleted/matched rows:")
        for item in reasons[: max(args.sample, 0)]:
            title = item.title.replace("\n", " ")[:100]
            print(f"- [{item.reason}] {item.platform} / {item.category} / {item.discount_percent:.0f}% / {title}")


if __name__ == "__main__":
    main()
