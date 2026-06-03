from __future__ import annotations

import argparse
import csv
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EBAY_DOMAIN_BY_PLATFORM = {
    "ebay us": "www.ebay.com",
    "ebay motors_us": "www.ebay.com",
    "ebay gb": "www.ebay.co.uk",
    "ebay uk": "www.ebay.co.uk",
    "ebay de": "www.ebay.de",
    "ebay germany": "www.ebay.de",
    "ebay fr": "www.ebay.fr",
    "ebay france": "www.ebay.fr",
    "ebay it": "www.ebay.it",
    "ebay italy": "www.ebay.it",
    "ebay es": "www.ebay.es",
    "ebay spain": "www.ebay.es",
    "ebay au": "www.ebay.com.au",
    "ebay australia": "www.ebay.com.au",
    "ebay ca": "www.ebay.ca",
    "ebay": "www.ebay.com",
}

BAD_MARKERS = (
    "we looked everywhere",
    "page not found",
    "this listing was ended",
    "this listing has ended",
    "listing has ended",
    "listing was ended",
    "the listing you're looking for is no longer available",
    "the listing you\u2019re looking for is no longer available",
    "this item is out of stock",
    "this item is no longer available",
    "sorry, this item is unavailable",
    "sorry, this item isn't available",
    "sorry, this item isn\u2019t available",
    "this item isn't available",
    "this item isn\u2019t available",
    "item not found",
    "unable to retrieve the listing",
    "we couldn't find this page",
    "we couldn\u2019t find this page",
    "this page does not exist",
)

UNCERTAIN_MARKERS = (
    "captcha",
    "verify you're human",
    "verify you\u2019re human",
    "checking your browser",
    "access denied",
    "robot check",
)


@dataclass
class EbayDeal:
    id: str
    title: str
    platform: str
    product_url: str
    affiliate_url: str | None


@dataclass
class CheckResult:
    id: str
    title: str
    platform: str
    item_id: str
    clean_url: str
    final_url: str
    http_status: str
    status: str
    reason: str


def _extract_item_id(deal: EbayDeal) -> str:
    parts = deal.id.split("|")
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[1]

    for value in (deal.product_url, deal.affiliate_url or ""):
        match = re.search(r"/itm/(?:[^/?#]+/)?(\d{9,})", value)
        if match:
            return match.group(1)
        match = re.search(r"\b(?:item|itemId|legacyItemId)=(\d{9,})\b", value)
        if match:
            return match.group(1)
    return ""


def _domain_for_platform(platform: str) -> str:
    return EBAY_DOMAIN_BY_PLATFORM.get(platform.strip().lower(), "www.ebay.com")


def _clean_url_for_deal(deal: EbayDeal) -> tuple[str, str]:
    item_id = _extract_item_id(deal)
    if not item_id:
        return "", ""
    return item_id, f"https://{_domain_for_platform(deal.platform)}/itm/{item_id}"


def _load_ebay_deals(db_path: Path, limit: int) -> list[EbayDeal]:
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        sql = """
        SELECT id, title, platform, product_url, affiliate_url
        FROM deals
        WHERE id LIKE 'ebay_%' OR LOWER(platform) LIKE 'ebay%'
        ORDER BY platform ASC, updated_at DESC, id ASC
        """
        if limit and limit > 0:
            sql += " LIMIT ?"
            rows = con.execute(sql, (limit,)).fetchall()
        else:
            rows = con.execute(sql).fetchall()
    return [
        EbayDeal(
            id=str(row["id"]),
            title=str(row["title"]),
            platform=str(row["platform"]),
            product_url=str(row["product_url"]),
            affiliate_url=str(row["affiliate_url"] or ""),
        )
        for row in rows
    ]


def _read_http(url: str, timeout_seconds: int) -> tuple[str, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        final_url = response.geturl()
        status_code = int(getattr(response, "status", 200))
        content = response.read(250_000)
    text = content.decode("utf-8", errors="ignore")
    return final_url, status_code, text


def _classify_response(deal: EbayDeal, timeout_seconds: int) -> CheckResult:
    item_id, clean_url = _clean_url_for_deal(deal)
    if not item_id:
        return CheckResult(
            id=deal.id,
            title=deal.title,
            platform=deal.platform,
            item_id="",
            clean_url="",
            final_url="",
            http_status="",
            status="uncertain",
            reason="could_not_extract_item_id",
        )

    try:
        final_url, status_code, text = _read_http(clean_url, timeout_seconds=timeout_seconds)
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        try:
            text = exc.read(120_000).decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        final_url = exc.geturl() or clean_url
        if status_code in {404, 410}:
            return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "bad", f"http_{status_code}")
        return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "uncertain", f"http_{status_code}")
    except Exception as exc:
        return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, "", "", "uncertain", f"network_error:{type(exc).__name__}")

    lower_text = text.lower()
    lower_final = final_url.lower()

    if status_code >= 500:
        return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "uncertain", f"http_{status_code}")
    if status_code in {404, 410}:
        return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "bad", f"http_{status_code}")

    for marker in UNCERTAIN_MARKERS:
        if marker in lower_text:
            return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "uncertain", f"blocked_or_challenge:{marker}")

    for marker in BAD_MARKERS:
        if marker in lower_text:
            return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "bad", f"bad_page:{marker}")

    if "/itm/" not in lower_final and item_id not in lower_final:
        # eBay may redirect unavailable items to category/search/home pages.
        if any(path in lower_final for path in ("/sch/", "/n/", "/b/")) or lower_final.rstrip("/").endswith(("ebay.com", "ebay.co.uk", "ebay.de", "ebay.fr", "ebay.it", "ebay.es", "ebay.com.au")):
            return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "bad", "redirected_away_from_item")
        return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "uncertain", "unexpected_final_url")

    return CheckResult(deal.id, deal.title, deal.platform, item_id, clean_url, final_url, str(status_code), "ok", "item_page_reachable")


def _write_report(path: Path, results: Iterable[CheckResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["status", "reason", "platform", "id", "item_id", "title", "clean_url", "final_url", "http_status"])
        for result in results:
            writer.writerow([
                result.status,
                result.reason,
                result.platform,
                result.id,
                result.item_id,
                result.title,
                result.clean_url,
                result.final_url,
                result.http_status,
            ])


def _delete_bad_deals(db_path: Path, bad_ids: list[str]) -> int:
    if not bad_ids:
        return 0
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.executemany("DELETE FROM deals WHERE id = ?", [(deal_id,) for deal_id in bad_ids])
        con.commit()
        return cur.rowcount if cur.rowcount is not None else len(bad_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and optionally remove stale/broken eBay deals from DiscountHub SQLite storage.")
    parser.add_argument("--db", default="backend/data/discounthub.sqlite3", help="Path to DiscountHub SQLite DB.")
    parser.add_argument("--report", default="backend/data/stage69_ebay_link_report.csv", help="CSV report output path.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of eBay rows to scan. 0 means all.")
    parser.add_argument("--timeout", type=int, default=12, help="HTTP timeout per eBay item in seconds.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay between eBay requests in seconds.")
    parser.add_argument("--delete", action="store_true", help="Delete deals classified as bad. Uncertain deals are never deleted.")
    args = parser.parse_args()

    db_path = Path(args.db)
    report_path = Path(args.report)
    if not db_path.exists():
        print(f"ERROR: DB file not found: {db_path}", file=sys.stderr)
        return 2

    deals = _load_ebay_deals(db_path, limit=args.limit)
    print(f"Loaded eBay-like deals: {len(deals)}")
    if not deals:
        _write_report(report_path, [])
        print(f"Report: {report_path}")
        return 0

    results: list[CheckResult] = []
    for index, deal in enumerate(deals, start=1):
        result = _classify_response(deal, timeout_seconds=args.timeout)
        results.append(result)
        print(f"[{index}/{len(deals)}] {result.status.upper():9} {deal.platform:14} {result.item_id or '-'} {result.reason}")
        if args.sleep > 0:
            time.sleep(args.sleep)

    _write_report(report_path, results)

    bad = [result for result in results if result.status == "bad"]
    ok = [result for result in results if result.status == "ok"]
    uncertain = [result for result in results if result.status == "uncertain"]

    print("")
    print(f"OK:        {len(ok)}")
    print(f"Bad:       {len(bad)}")
    print(f"Uncertain: {len(uncertain)}")
    print(f"Report:    {report_path}")

    if bad[:10]:
        print("")
        print("Bad sample:")
        for result in bad[:10]:
            print(f"- {result.platform} {result.item_id}: {result.title[:90]} [{result.reason}]")

    if args.delete:
        backup_path = db_path.with_name(f"{db_path.name}.before_stage69_ebay_cleanup")
        if not backup_path.exists():
            shutil.copy2(db_path, backup_path)
            print(f"Backup:    {backup_path}")
        deleted = _delete_bad_deals(db_path, [result.id for result in bad])
        print(f"Deleted:   {deleted}")
    else:
        print("")
        print("Dry run only. Re-run with --delete to remove bad deals.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
