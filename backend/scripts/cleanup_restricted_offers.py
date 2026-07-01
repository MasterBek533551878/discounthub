from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.db.database import get_connection
from app.services.restricted_offer_filter import restricted_offer_match


@dataclass(frozen=True)
class MatchedRow:
    table: str
    row_id: str
    title: str
    source: str
    reason: str


def _deal_match(row: Any) -> str | None:
    match = restricted_offer_match(
        (
            row["title"],
            row["description"],
            row["platform"],
            row["category"],
            row["product_url"],
            row["affiliate_url"],
        )
    )
    return match.reason if match is not None else None


def _promotion_match(row: Any) -> str | None:
    match = restricted_offer_match(
        (
            row["title"],
            row["description"],
            row["store"],
            row["discount_text"],
            row["code"],
            row["landing_url"],
            row["affiliate_url"],
        )
    )
    return match.reason if match is not None else None


def find_matches() -> list[MatchedRow]:
    matches: list[MatchedRow] = []
    with get_connection() as connection:
        deal_rows = connection.execute(
            """
            SELECT id, title, description, platform, category, product_url, affiliate_url
            FROM deals
            """
        ).fetchall()
        for row in deal_rows:
            reason = _deal_match(row)
            if reason is None:
                continue
            matches.append(
                MatchedRow(
                    table="deals",
                    row_id=str(row["id"]),
                    title=str(row["title"] or ""),
                    source=str(row["platform"] or ""),
                    reason=reason,
                )
            )

        promotion_rows = connection.execute(
            """
            SELECT id, title, description, store, discount_text, code, landing_url, affiliate_url
            FROM promotions
            """
        ).fetchall()
        for row in promotion_rows:
            reason = _promotion_match(row)
            if reason is None:
                continue
            matches.append(
                MatchedRow(
                    table="promotions",
                    row_id=str(row["id"]),
                    title=str(row["title"] or ""),
                    source=str(row["store"] or ""),
                    reason=reason,
                )
            )
    return matches


def delete_matches(matches: list[MatchedRow]) -> tuple[int, int]:
    deal_ids = [row.row_id for row in matches if row.table == "deals"]
    promotion_ids = [row.row_id for row in matches if row.table == "promotions"]
    deleted_deals = 0
    deleted_promotions = 0
    with get_connection() as connection:
        if deal_ids:
            connection.executemany("DELETE FROM deals WHERE id = ?", [(value,) for value in deal_ids])
            deleted_deals = len(deal_ids)
        if promotion_ids:
            connection.executemany("DELETE FROM promotions WHERE id = ?", [(value,) for value in promotion_ids])
            deleted_promotions = len(promotion_ids)
        connection.commit()
    return deleted_deals, deleted_promotions


def print_report(matches: list[MatchedRow], *, sample_limit: int) -> None:
    by_table = Counter(row.table for row in matches)
    by_reason = Counter(row.reason for row in matches)
    print("Restricted offers audit")
    print(f"matched_total={len(matches)}")
    print(f"matched_deals={by_table.get('deals', 0)}")
    print(f"matched_promotions={by_table.get('promotions', 0)}")
    if by_reason:
        print("reasons:")
        for reason, count in by_reason.most_common():
            print(f"  {reason}: {count}")
    if matches:
        print("samples:")
        for row in matches[:sample_limit]:
            title = row.title.replace("\n", " ").strip()
            if len(title) > 120:
                title = title[:117] + "..."
            print(f"  [{row.table}] {row.row_id} | {row.source} | {row.reason} | {title}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit/delete pork/ham and alcohol offers already stored in DiscountHub SQLite."
    )
    parser.add_argument("--apply", action="store_true", help="Delete matched rows. Without this, audit only.")
    parser.add_argument("--sample-limit", type=int, default=25, help="How many matched rows to print.")
    args = parser.parse_args()

    matches = find_matches()
    print_report(matches, sample_limit=max(args.sample_limit, 0))

    if not args.apply:
        print("dry_run=true")
        print("Run again with --apply to delete matched rows.")
        return 0

    deleted_deals, deleted_promotions = delete_matches(matches)
    print("dry_run=false")
    print(f"deleted_deals={deleted_deals}")
    print(f"deleted_promotions={deleted_promotions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
