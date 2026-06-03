from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
DEFAULT_API_BASE_URL = "https://api.ebay.com"
DEFAULT_SCOPE = "https://api.ebay.com/oauth/api_scope"

MARKETPLACE_BY_PLATFORM = {
    "ebay us": "EBAY_US",
    "ebay gb": "EBAY_GB",
    "ebay uk": "EBAY_GB",
    "ebay de": "EBAY_DE",
    "ebay fr": "EBAY_FR",
    "ebay it": "EBAY_IT",
    "ebay es": "EBAY_ES",
    "ebay au": "EBAY_AU",
    "ebay ca": "EBAY_CA",
    "ebay motors_us": "EBAY_MOTORS_US",
    "ebay motors us": "EBAY_MOTORS_US",
}

CANONICAL_HOST_BY_MARKETPLACE = {
    "EBAY_US": "www.ebay.com",
    "EBAY_GB": "www.ebay.co.uk",
    "EBAY_DE": "www.ebay.de",
    "EBAY_FR": "www.ebay.fr",
    "EBAY_IT": "www.ebay.it",
    "EBAY_ES": "www.ebay.es",
    "EBAY_AU": "www.ebay.com.au",
    "EBAY_CA": "www.ebay.ca",
    "EBAY_MOTORS_US": "www.ebay.com",
}

@dataclass
class CheckResult:
    status: str
    reason: str
    http_status: int | str
    candidate_item_id: str
    item_web_url: str
    affiliate_web_url: str
    availability: str


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = dict(os.environ)
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            values[key] = value
    return values


def fetch_json(url: str, *, headers: dict[str, str], timeout: int, data: bytes | None = None) -> tuple[int, Any, str]:
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {}
            return int(resp.status), payload, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {}
        return int(exc.code), payload, body
    except urllib.error.URLError as exc:
        return 0, {}, str(exc)


def get_ebay_token(env: dict[str, str], *, timeout: int) -> str:
    client_id = env.get("EBAY_CLIENT_ID", "").strip()
    client_secret = env.get("EBAY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required in backend/.env")

    oauth_url = env.get("EBAY_OAUTH_URL", DEFAULT_OAUTH_URL).strip() or DEFAULT_OAUTH_URL
    scope = env.get("EBAY_SCOPE", DEFAULT_SCOPE).strip() or DEFAULT_SCOPE
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    basic = base64.b64encode(credentials).decode("ascii")
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": scope}).encode("utf-8")
    status, payload, raw = fetch_json(
        oauth_url,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "DiscountHub-Stage70-eBay-Cleanup/0.1",
        },
        timeout=timeout,
        data=body,
    )
    if status != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
        raise RuntimeError(f"Could not get eBay OAuth token. HTTP {status}: {raw[:500]}")
    return str(payload["access_token"])


def marketplace_for_platform(platform: str) -> str:
    key = re.sub(r"\s+", " ", str(platform or "").strip().lower())
    return MARKETPLACE_BY_PLATFORM.get(key, "EBAY_US")


def legacy_id_from_url(url: str) -> str:
    match = re.search(r"/itm/(?:[^/?#]+/)?(\d{9,15})", str(url or ""), flags=re.I)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{9,15})\b", str(url or ""))
    return match.group(1) if match else ""


def legacy_id_from_deal_id(deal_id: str) -> str:
    match = re.search(r"v1\|(\d{9,15})\|", str(deal_id or ""))
    if match:
        return match.group(1)
    match = re.search(r"\|(\d{9,15})\|", str(deal_id or ""))
    if match:
        return match.group(1)
    return ""


def item_candidates(row: sqlite3.Row) -> list[str]:
    candidates: list[str] = []
    deal_id = str(row["id"] or "")
    for value in re.findall(r"v1\|\d{9,15}\|\d+", deal_id):
        candidates.append(value)

    legacy = legacy_id_from_deal_id(deal_id) or legacy_id_from_url(row["product_url"] or "") or legacy_id_from_url(row["affiliate_url"] or "")
    if legacy:
        candidates.append(f"v1|{legacy}|0")
        candidates.append(legacy)

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def canonical_ebay_url(marketplace_id: str, legacy_id: str) -> str:
    host = CANONICAL_HOST_BY_MARKETPLACE.get(marketplace_id, "www.ebay.com")
    return f"https://{host}/itm/{legacy_id}" if legacy_id else ""


def extract_availability(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    statuses: list[str] = []
    values = payload.get("estimatedAvailabilities")
    if isinstance(values, list):
        for value in values:
            if isinstance(value, dict):
                status = str(value.get("estimatedAvailabilityStatus") or "").strip()
                if status:
                    statuses.append(status)
    return ",".join(statuses)


def is_bad_availability(availability: str) -> bool:
    if not availability:
        return False
    parts = [part.strip().upper() for part in availability.split(",") if part.strip()]
    return bool(parts) and all(part in {"OUT_OF_STOCK", "SOLD_OUT"} for part in parts)


def parse_ebay_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_past_end_date(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    end_at = parse_ebay_datetime(str(payload.get("itemEndDate") or ""))
    return bool(end_at and end_at < datetime.now(timezone.utc))


def check_item(row: sqlite3.Row, *, token: str, api_base_url: str, timeout: int) -> CheckResult:
    platform = str(row["platform"] or "")
    marketplace_id = marketplace_for_platform(platform)
    candidates = item_candidates(row)
    if not candidates:
        return CheckResult("bad", "missing_item_id", "n/a", "", "", "", "")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "DiscountHub-Stage70-eBay-Cleanup/0.1",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
    }

    last_status: int | str = "n/a"
    last_body = ""
    for candidate in candidates:
        encoded = urllib.parse.quote(candidate, safe="")
        url = f"{api_base_url.rstrip('/')}/buy/browse/v1/item/{encoded}"
        status, payload, raw = fetch_json(url, headers=headers, timeout=timeout)
        last_status = status
        last_body = raw
        if status == 200 and isinstance(payload, dict):
            availability = extract_availability(payload)
            item_web_url = str(payload.get("itemWebUrl") or "").strip()
            affiliate_web_url = str(payload.get("itemAffiliateWebUrl") or "").strip()
            if is_bad_availability(availability):
                return CheckResult("bad", "out_of_stock", status, candidate, item_web_url, affiliate_web_url, availability)
            if is_past_end_date(payload):
                return CheckResult("bad", "ended_listing", status, candidate, item_web_url, affiliate_web_url, availability)
            return CheckResult("ok", "active_in_browse_api", status, candidate, item_web_url, affiliate_web_url, availability)
        if status in {404, 410}:
            continue
        if status == 400:
            # Try the next candidate first. If all candidates fail with 400, classify below using the error text.
            continue
        if status in {401, 403, 429, 500, 502, 503, 504, 0}:
            return CheckResult("uncertain", f"api_http_{status}", status, candidate, "", "", "")

    body_lower = last_body.lower()
    if "not found" in body_lower or "invalid item" in body_lower or "not exist" in body_lower:
        reason = "not_found_or_invalid_item"
    elif last_status in {400, 404, 410}:
        reason = f"api_http_{last_status}"
    else:
        return CheckResult("uncertain", f"api_http_{last_status}", last_status, candidates[-1], "", "", "")
    return CheckResult("bad", reason, last_status, candidates[-1], "", "", "")


def fetch_ebay_rows(connection: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    sql = """
        SELECT id, title, platform, provider_id, product_url, affiliate_url, updated_at
        FROM deals
        WHERE platform LIKE 'eBay%'
           OR provider_id LIKE 'ebay_%'
           OR id LIKE 'ebay_%'
        ORDER BY platform ASC, updated_at ASC, id ASC
    """
    if limit and limit > 0:
        sql += " LIMIT ?"
        return list(connection.execute(sql, (limit,)).fetchall())
    return list(connection.execute(sql).fetchall())


def update_ok_links(connection: sqlite3.Connection, row: sqlite3.Row, result: CheckResult) -> int:
    legacy = legacy_id_from_deal_id(str(row["id"] or "")) or legacy_id_from_url(str(row["product_url"] or ""))
    marketplace_id = marketplace_for_platform(str(row["platform"] or ""))
    canonical = canonical_ebay_url(marketplace_id, legacy)
    product_url = result.item_web_url or canonical
    affiliate_url = result.affiliate_web_url or product_url
    if not product_url:
        return 0
    return connection.execute(
        "UPDATE deals SET product_url = ?, affiliate_url = ? WHERE id = ?",
        (product_url, affiliate_url, row["id"]),
    ).rowcount


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--env", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.08)
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--update-links", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    env_path = Path(args.env)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    env = read_env(env_path)
    api_base_url = env.get("EBAY_API_BASE_URL", DEFAULT_API_BASE_URL).strip() or DEFAULT_API_BASE_URL
    print("Getting eBay OAuth token...")
    token = get_ebay_token(env, timeout=args.timeout)
    print("Token: OK (not printed)")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    rows = fetch_ebay_rows(connection, args.limit)
    total = len(rows)
    print(f"eBay rows to check: {total}")

    ok = bad = uncertain = 0
    deleted = 0
    updated_links = 0
    bad_ids: list[str] = []

    with report_path.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(
            report_file,
            fieldnames=[
                "deal_id",
                "platform",
                "status",
                "reason",
                "http_status",
                "candidate_item_id",
                "availability",
                "title",
                "product_url",
                "affiliate_url",
                "item_web_url",
                "item_affiliate_web_url",
            ],
        )
        writer.writeheader()

        for index, row in enumerate(rows, start=1):
            result = check_item(row, token=token, api_base_url=api_base_url, timeout=args.timeout)
            if result.status == "ok":
                ok += 1
                if args.update_links:
                    updated_links += update_ok_links(connection, row, result)
            elif result.status == "bad":
                bad += 1
                bad_ids.append(str(row["id"]))
            else:
                uncertain += 1

            item_label = legacy_id_from_deal_id(str(row["id"] or "")) or result.candidate_item_id or "?"
            print(f"[{index}/{total}] {result.status.upper():9} {str(row['platform'])[:14]:14} {item_label:15} {result.reason}")

            writer.writerow(
                {
                    "deal_id": row["id"],
                    "platform": row["platform"],
                    "status": result.status,
                    "reason": result.reason,
                    "http_status": result.http_status,
                    "candidate_item_id": result.candidate_item_id,
                    "availability": result.availability,
                    "title": row["title"],
                    "product_url": row["product_url"],
                    "affiliate_url": row["affiliate_url"],
                    "item_web_url": result.item_web_url,
                    "item_affiliate_web_url": result.affiliate_web_url,
                }
            )

            if args.sleep > 0:
                time.sleep(args.sleep)

    if args.delete and bad_ids:
        backup_path = db_path.with_name(db_path.name + ".before_stage70_ebay_api_cleanup")
        shutil.copy2(db_path, backup_path)
        for deal_id in bad_ids:
            deleted += connection.execute("DELETE FROM deals WHERE id = ?", (deal_id,)).rowcount
        print(f"Backup: {backup_path}")
    elif args.delete:
        print("No bad eBay rows to delete.")

    connection.commit()
    connection.close()

    print("")
    print(f"OK:            {ok}")
    print(f"Bad:           {bad}")
    print(f"Uncertain:     {uncertain}")
    print(f"Updated links: {updated_links}")
    print(f"Report:        {report_path}")
    if not args.delete:
        print("Dry run only. Re-run with -Delete to remove only rows marked Bad.")
    else:
        print(f"Deleted:       {deleted}")

    if uncertain and not ok and not bad:
        print("")
        print("WARNING: The API check could not verify any eBay rows. Do not delete uncertain rows.")
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
