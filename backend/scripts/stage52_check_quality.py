from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

BAD_KEYWORDS = [
    "for parts",
    "parts only",
    "spares",
    "broken",
    "not working",
    "for repair",
    "faulty",
    "defective",
    "damaged",
    "replacement",
    "ersatz",
    "mainboard",
    "screen protector",
    "case only",
    "manual only",
    "charger only",
    "empty box",
]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def database_path(root: Path) -> Path:
    return root / "data" / "discounthub.sqlite3"


def parse_datetime(value: str | None):
    try:
        text = str(value or "").strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def discount_percent(old_price: float, current_price: float) -> float:
    if old_price <= 0:
        return 0.0
    return ((old_price - current_price) / old_price) * 100.0


def main() -> None:
    db_path = database_path(backend_root())
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM deals").fetchall()

    ebay_rows = [row for row in rows if str(row["platform"] or "").lower().startswith("ebay") or str(row["id"] or "").lower().startswith("ebay_")]
    low_discount = []
    stale = []
    bad_keyword = []
    category_counts: dict[str, int] = {}
    platform_counts: dict[str, int] = {}

    for row in ebay_rows:
        category = str(row["category"] or "Other")
        platform = str(row["platform"] or "eBay")
        category_counts[category] = category_counts.get(category, 0) + 1
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        discount = discount_percent(float(row["old_price"] or 0), float(row["current_price"] or 0))
        if discount + 0.1 < 15:
            low_discount.append(row)
        updated = parse_datetime(row["updated_at"])
        if updated is None or updated < cutoff:
            stale.append(row)
        text = " ".join(str(row[key] or "") for key in ("title", "description", "category", "product_url", "affiliate_url")).lower()
        if any(keyword in text for keyword in BAD_KEYWORDS):
            bad_keyword.append(row)

    print("Stage 52 quality check")
    print(f"- total deals: {len(rows)}")
    print(f"- eBay deals: {len(ebay_rows)}")
    print(f"- eBay deals below 15% discount: {len(low_discount)}")
    print(f"- eBay stale/missing updated_at older than 72h: {len(stale)}")
    print(f"- eBay rows with known bad keywords: {len(bad_keyword)}")

    print("\nTop categories:")
    for category, count in sorted(category_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:12]:
        print(f"- {category}: {count}")

    print("\nTop marketplaces:")
    for platform, count in sorted(platform_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:12]:
        print(f"- {platform}: {count}")

    if bad_keyword:
        print("\nSample bad keyword rows still present:")
        for row in bad_keyword[:8]:
            print(f"- {row['platform']} / {row['category']} / {str(row['title'])[:100]}")


if __name__ == "__main__":
    main()
