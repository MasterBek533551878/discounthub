from pathlib import Path
import sqlite3
from datetime import datetime, timezone

DB_CANDIDATES = [
    Path("data/discounthub.sqlite3"),
    Path("backend/data/discounthub.sqlite3"),
]
DB = next((p for p in DB_CANDIDATES if p.exists()), DB_CANDIDATES[0])

NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

OFFER = {
    "id": "owl-transfer",
    "slug": "owl-transfer",
    "title": "OWL Transfer",
    "name": "OWL Transfer",
    "brand": "OWL Transfer",
    "company_name": "OWL Transfer",
    "partner_name": "OWL Transfer",

    "headline": "50% off any paid plan",
    "subtitle": "Secure file sharing with PGP encryption and OneTimeView.",
    "short_description": "Get 50% off OWL Transfer paid plans with code DISCOUNTHUB50.",
    "description": (
        "OWL Transfer is a secure file sharing platform for individuals and businesses. "
        "It helps users send large files with end-to-end PGP encryption, password protection, "
        "expiration dates, download limits, and OneTimeView technology for private one-time file viewing."
    ),

    "offer_text": "50% discount on any paid plan until December 31, 2026.",
    "discount": "50%",
    "discount_text": "50% off any paid plan",
    "discount_label": "50% OFF",

    "coupon_code": "DISCOUNTHUB50",
    "promo_code": "DISCOUNTHUB50",
    "code": "DISCOUNTHUB50",

    "category": "Security",
    "website_url": "https://owltransfer.com/",
    "url": "https://owltransfer.com/",
    "landing_url": "https://owltransfer.com/",
    "target_url": "https://owltransfer.com/",
    "cta_url": "https://owltransfer.com/",

    "terms": "Only for users who apply the code when choosing a paid plan.",
    "valid_until": "2026-12-31",
    "expires_on": "2026-12-31",
    "expires_at": "2026-12-31T23:59:59Z",
    "end_date": "2026-12-31",

    "status": "active",
    "is_active": 1,
    "active": 1,
    "enabled": 1,
    "published": 1,
    "featured": 1,

    "created_at": NOW,
    "updated_at": NOW,
    "published_at": NOW,
    "starts_at": NOW,
    "start_date": NOW,

    "type": "coupon",
    "source": "manual",
    "provider": "manual",
    "external_id": "owl-transfer-discounthub50",
}

def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def pick_value(col):
    name = col["name"]
    lower = name.lower()

    if lower in OFFER:
        return OFFER[lower]

    if "coupon" in lower or "promo" in lower:
        return "DISCOUNTHUB50"
    if "discount" in lower:
        return "50% off any paid plan"
    if "expire" in lower or "valid" in lower or lower in {"until", "ends_at"}:
        return "2026-12-31T23:59:59Z" if lower.endswith("_at") else "2026-12-31"
    if "url" in lower or "link" in lower:
        return "https://owltransfer.com/"
    if "desc" in lower:
        return OFFER["description"]
    if "title" in lower or "name" in lower or "brand" in lower or "partner" in lower:
        return "OWL Transfer"
    if "category" in lower:
        return "Security"
    if lower.startswith("is_") or lower in {"active", "enabled", "published", "featured"}:
        return 1
    if lower.endswith("_at") or lower in {"created", "updated"}:
        return NOW

    return None

def is_int_pk(col):
    return col["pk"] and "INT" in (col["type"] or "").upper()

def main():
    if not DB.exists():
        raise SystemExit(f"DB not found. Tried: {', '.join(map(str, DB_CANDIDATES))}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    table = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='partner_offers'"
    ).fetchone()

    if not table:
        raise SystemExit("Table partner_offers not found.")

    cols = [dict(r) for r in cur.execute("PRAGMA table_info(partner_offers)")]
    col_names = [c["name"] for c in cols]

    row = {}
    missing_required = []

    for col in cols:
        name = col["name"]

        if is_int_pk(col):
            continue

        value = pick_value(col)

        if col["pk"] and value is None:
            value = "owl-transfer"

        if value is not None:
            row[name] = value
        elif col["notnull"] and col["dflt_value"] is None and not col["pk"]:
            missing_required.append(name)

    if missing_required:
        print("Cannot safely insert because these NOT NULL columns are unknown:", missing_required)
        print("partner_offers columns:")
        for c in cols:
            print(c)
        raise SystemExit(2)

    lookup = None
    for candidate in ("slug", "external_id", "coupon_code", "promo_code", "code", "title", "name"):
        if candidate in row:
            lookup = (candidate, row[candidate])
            break

    existing = None
    if lookup:
        existing = cur.execute(
            f"SELECT rowid, * FROM partner_offers WHERE {q(lookup[0])} = ? LIMIT 1",
            (lookup[1],),
        ).fetchone()

    if existing:
        update_cols = [
            c for c in row
            if c in col_names and not any(col["name"] == c and col["pk"] for col in cols)
        ]
        cur.execute(
            f"UPDATE partner_offers SET {', '.join(f'{q(c)} = ?' for c in update_cols)} WHERE rowid = ?",
            [row[c] for c in update_cols] + [existing["rowid"]],
        )
        action = "updated"
        rowid = existing["rowid"]
    else:
        insert_cols = [c for c in row if c in col_names]
        cur.execute(
            f"INSERT INTO partner_offers ({', '.join(q(c) for c in insert_cols)}) VALUES ({', '.join('?' for _ in insert_cols)})",
            [row[c] for c in insert_cols],
        )
        action = "inserted"
        rowid = cur.lastrowid

    con.commit()

    result = cur.execute("SELECT rowid, * FROM partner_offers WHERE rowid = ?", (rowid,)).fetchone()
    print(f"OWL Transfer offer {action}. DB: {DB}")
    for key in result.keys():
        if key in {"rowid", "id", "slug", "title", "name", "coupon_code", "promo_code", "code", "discount_label", "website_url", "expires_at", "valid_until", "is_active", "active", "published"}:
            print(f"{key}: {result[key]}")

    con.close()

if __name__ == "__main__":
    main()
