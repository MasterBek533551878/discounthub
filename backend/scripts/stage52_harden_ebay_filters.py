from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

DEFAULT_MIN_DISCOUNT = "15"
DEFAULT_EXCLUDE_KEYWORDS = [
    # Damaged / non-working listings.
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
    # Packaging / accessories instead of the actual product.
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
    # Replacement boards / repair-market terms that polluted the feed.
    "replacement",
    "ersatz",
    "mainboard",
    "logic board",
    "motherboard replacement",
    "lcd screen only",
    "display only",
]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def database_path(root: Path) -> Path:
    return root / "data" / "discounthub.sqlite3"


def config_path(root: Path) -> Path:
    return root / "config" / "feed_providers.json"


def normalize_keyword(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def harden_ebay_url(url: str, *, min_discount: str, extra_keywords: list[str]) -> tuple[str, bool]:
    if not str(url).startswith("ebay://browse"):
        return url, False

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    changed = False

    current_min_discount = (params.get("min_discount") or [""])[0].strip()
    if not current_min_discount:
        params["min_discount"] = [min_discount]
        changed = True

    existing_keywords: list[str] = []
    for raw in (params.get("exclude_keywords") or [""])[0].split("|"):
        keyword = normalize_keyword(raw)
        if keyword:
            existing_keywords.append(keyword)

    merged: list[str] = []
    seen: set[str] = set()
    for keyword in existing_keywords + [normalize_keyword(item) for item in extra_keywords]:
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        merged.append(keyword)

    if merged != existing_keywords:
        params["exclude_keywords"] = ["|".join(merged)]
        changed = True

    if not changed:
        return url, False

    # Keep deterministic param ordering enough for readable diffs.
    query = urlencode({key: values[0] if values else "" for key, values in params.items()})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment)), True


def iter_provider_dicts(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(data, dict):
        for key in ("providers", "items", "feedProviders", "feed_providers"):
            value = data.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield item


def harden_config(root: Path, *, min_discount: str, extra_keywords: list[str]) -> int:
    path = config_path(root)
    if not path.exists():
        return 0

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    updated = 0
    for provider in iter_provider_dicts(data):
        url = str(provider.get("url") or "")
        adapter = str(provider.get("adapter") or "")
        if adapter != "ebay_browse_api" and not url.startswith("ebay://browse"):
            continue
        new_url, changed = harden_ebay_url(url, min_discount=min_discount, extra_keywords=extra_keywords)
        if changed:
            provider["url"] = new_url
            updated += 1

    if updated:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated


def harden_database(root: Path, *, min_discount: str, extra_keywords: list[str]) -> int:
    path = database_path(root)
    if not path.exists():
        return 0

    updated = 0
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, url
            FROM feed_providers
            WHERE adapter = 'ebay_browse_api' OR url LIKE 'ebay://browse%'
            """
        ).fetchall()
        for row in rows:
            new_url, changed = harden_ebay_url(
                str(row["url"]),
                min_discount=min_discount,
                extra_keywords=extra_keywords,
            )
            if not changed:
                continue
            connection.execute(
                "UPDATE feed_providers SET url = ?, updated_at = datetime('now') WHERE id = ?",
                (new_url, row["id"]),
            )
            updated += 1
        connection.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Strengthen eBay provider query filters for DiscountHub V1 quality.")
    parser.add_argument("--min-discount", default=DEFAULT_MIN_DISCOUNT)
    parser.add_argument("--extra-keyword", action="append", default=[])
    args = parser.parse_args()

    root = backend_root()
    keywords = DEFAULT_EXCLUDE_KEYWORDS + list(args.extra_keyword or [])

    config_updated = harden_config(root, min_discount=str(args.min_discount), extra_keywords=keywords)
    db_updated = harden_database(root, min_discount=str(args.min_discount), extra_keywords=keywords)

    print("Stage 52 provider filter hardening completed.")
    print(f"- config providers updated: {config_updated}")
    print(f"- database providers updated: {db_updated}")
    print(f"- enforced min_discount when missing: {args.min_discount}")
    print(f"- exclude keyword count: {len(set(normalize_keyword(item) for item in keywords if normalize_keyword(item)))}")


if __name__ == "__main__":
    main()
