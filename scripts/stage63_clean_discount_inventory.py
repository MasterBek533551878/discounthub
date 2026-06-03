from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def main() -> None:
    db_path = Path(os.environ.get("DISCOUNTHUB_DB_PATH", "backend/data/discounthub.sqlite3"))
    min_discount = float(os.environ.get("DISCOUNTHUB_MIN_DISCOUNT", "1"))
    if min_discount < 1:
        min_discount = 1

    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.stage63_backup_{stamp}")
    shutil.copy2(db_path, backup)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    before = int(cur.execute("SELECT COUNT(*) AS total FROM deals").fetchone()["total"])
    bad_by_platform = cur.execute(
        """
        SELECT platform, COUNT(*) AS count
        FROM deals
        WHERE old_price <= current_price
           OR old_price <= 0
           OR current_price <= 0
           OR (((old_price - current_price) / old_price) * 100) < ?
        GROUP BY platform
        ORDER BY count DESC, platform ASC
        LIMIT 30
        """,
        (min_discount,),
    ).fetchall()

    deleted = cur.execute(
        """
        DELETE FROM deals
        WHERE old_price <= current_price
           OR old_price <= 0
           OR current_price <= 0
           OR (((old_price - current_price) / old_price) * 100) < ?
        """,
        (min_discount,),
    ).rowcount

    conn.commit()
    after = int(cur.execute("SELECT COUNT(*) AS total FROM deals").fetchone()["total"])

    platforms = cur.execute(
        """
        SELECT platform, COUNT(*) AS count
        FROM deals
        GROUP BY platform
        ORDER BY count DESC, platform ASC
        LIMIT 20
        """
    ).fetchall()
    modes = cur.execute(
        """
        SELECT COALESCE(monetization_mode, 'direct') AS mode, COUNT(*) AS count
        FROM deals
        GROUP BY COALESCE(monetization_mode, 'direct')
        ORDER BY count DESC, mode ASC
        """
    ).fetchall()
    remaining_bad = int(
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM deals
            WHERE old_price <= current_price
               OR old_price <= 0
               OR current_price <= 0
               OR (((old_price - current_price) / old_price) * 100) < ?
            """,
            (min_discount,),
        ).fetchone()["total"]
    )
    conn.close()

    print(f"Backup created       : {backup}")
    print(f"Minimum discount     : {min_discount:g}%")
    print(f"Deals before         : {before}")
    print(f"Deleted non-discounts: {deleted}")
    print(f"Deals after          : {after}")
    print(f"Remaining bad rows   : {remaining_bad}")

    if bad_by_platform:
        print("Bad rows removed by platform:")
        for row in bad_by_platform:
            print(f"  {row['platform']}: {row['count']}")
    else:
        print("Bad rows removed by platform: none")

    print("Top platforms after cleanup:")
    for row in platforms:
        print(f"  {row['platform']}: {row['count']}")

    print("Monetization modes after cleanup:")
    for row in modes:
        print(f"  {row['mode']}: {row['count']}")

    if remaining_bad:
        raise SystemExit("Discount cleanup failed: remaining bad rows found.")


if __name__ == "__main__":
    main()
