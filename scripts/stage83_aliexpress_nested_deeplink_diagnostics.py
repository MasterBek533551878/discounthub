#!/usr/bin/env python3
import argparse
import csv
import io
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DB_PATH = "/opt/discounthub/backend/data/discounthub.sqlite3"
ITEM_RE = re.compile(r"/item/(\d+)\.html", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--provider-id", default="admitad_6115_aliexpress_ww_v1")
    p.add_argument("--max-rows", type=int, default=20)
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()


def mask_affiliate_url(url: str) -> str:
    if not url:
        return url
    url = re.sub(r"(https?://(?:rzekl\.com|rztekl\.com|ad\.admitad\.com)/g/)[^/?#]+", r"\1***TOKEN***", url)
    url = re.sub(r"([?&](?:code|token|key)=)[^&#]+", r"\1***", url, flags=re.IGNORECASE)
    return url


def maybe_json(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return value


def find_feed_url(row: sqlite3.Row) -> str | None:
    d = dict(row)
    preferred = ["url", "feed_url", "feedUrl", "source_url", "sourceUrl", "config_json"]
    values: list[Any] = []
    for k in preferred:
        if k in d:
            values.append(d[k])
    for k, v in d.items():
        if k not in preferred:
            values.append(v)

    def walk(v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, dict):
            for x in v.values():
                found = walk(x)
                if found:
                    return found
            return None
        if isinstance(v, list):
            for x in v:
                found = walk(x)
                if found:
                    return found
            return None
        if not isinstance(v, str):
            return None
        s = v.strip()
        if s.startswith("{") or s.startswith("["):
            parsed = maybe_json(s)
            if parsed is not s:
                found = walk(parsed)
                if found:
                    return found
        if s.startswith("http://") or s.startswith("https://"):
            if "export.admitad.com" in s or "products" in s or "feed" in s:
                return s
        return None

    for v in values:
        found = walk(v)
        if found:
            return found
    return None


def parse_price(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace("\u00a0", " ")
    m = re.search(r"[-+]?\d+(?:[.,]\d+)?(?:[.,]\d+)?", s)
    if not m:
        return None
    val = m.group(0)
    if val.count(",") and val.count("."):
        val = val.replace(",", "")
    else:
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def parse_param_field(param: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not param:
        return out
    for part in str(param).split(";"):
        chunks = part.split("|")
        if len(chunks) >= 2:
            key = chunks[0].strip()
            val = chunks[1].strip()
            if key:
                out[key] = val
    return out


def unquote_deep(value: str, max_depth: int = 5) -> str:
    old = value
    for _ in range(max_depth):
        new = urllib.parse.unquote(old)
        if new == old:
            return new
        old = new
    return old


@dataclass
class Extracted:
    raw: str
    ulp: str | None
    s_click_url: str | None
    dl_target_url: str | None
    clean_product_url: str | None
    item_id: str | None


def extract_nested_aliexpress(raw_url: str) -> Extracted:
    raw = raw_url or ""
    ulp = None
    s_click = None
    dl_target = None
    clean = None
    item_id = None

    def item_from_url(u: str) -> tuple[str | None, str | None]:
        decoded = unquote_deep(u)
        m = ITEM_RE.search(decoded)
        if not m:
            return None, None
        iid = m.group(1)
        return f"https://www.aliexpress.com/item/{iid}.html", iid

    clean, item_id = item_from_url(raw)
    if clean:
        return Extracted(raw, ulp, s_click, dl_target, clean, item_id)

    try:
        p = urllib.parse.urlparse(raw)
        q = urllib.parse.parse_qs(p.query, keep_blank_values=True)
        if q.get("ulp"):
            ulp = unquote_deep(q["ulp"][0])
            if "s.click.aliexpress.com" in urllib.parse.urlparse(ulp).netloc.lower():
                s_click = ulp
            clean, item_id = item_from_url(ulp)
            if clean:
                return Extracted(raw, ulp, s_click, dl_target, clean, item_id)

            sp = urllib.parse.urlparse(ulp)
            sq = urllib.parse.parse_qs(sp.query, keep_blank_values=True)
            if sq.get("dl_target_url"):
                dl_target = unquote_deep(sq["dl_target_url"][0])
                clean, item_id = item_from_url(dl_target)
                return Extracted(raw, ulp, s_click, dl_target, clean, item_id)
    except Exception:
        pass

    return Extracted(raw, ulp, s_click, dl_target, clean, item_id)


def fetch_stream(url: str, timeout: int):
    req = urllib.request.Request(url, headers={"User-Agent": "DiscountHubStage83/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def main() -> int:
    args = parse_args()
    print("== Stage 83 AliExpress nested deeplink diagnostics ==")
    print(f"Provider: {args.provider_id}")
    print(f"DB: {DB_PATH}")
    print(f"Max rows: {args.max_rows}")
    print("Mode: dry-run only; no import, no delete")
    print("")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM feed_providers WHERE id = ?", (args.provider_id,)).fetchone()
    if not row:
        print("Provider not found.")
        return 1

    print("Provider row:")
    for k, v in dict(row).items():
        if k == "url" and isinstance(v, str):
            print(f"  {k}: {mask_affiliate_url(v)[:240]}")
        else:
            print(f"  {k}: {v}")
    print("")

    feed_url = find_feed_url(row)
    if not feed_url:
        print("No feed URL found.")
        return 1

    print("Feed URL found: yes (not printed to avoid leaking tokens)")
    print("Fetching feed stream...")

    with fetch_stream(feed_url, timeout=args.timeout) as resp:
        print("HTTP:", getattr(resp, "status", "unknown"))
        print("Content-Type:", resp.headers.get("content-type"))
        text = io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline="")
        reader = csv.DictReader(text, delimiter=";")

        print("Headers:", ", ".join(reader.fieldnames or []))
        print("")

        scanned = 0
        ulp_found = 0
        s_click_found = 0
        dl_target_found = 0
        clean_item_found = 0
        discount_param_10 = 0
        oldprice_price_discount_10 = 0
        samples: list[dict[str, Any]] = []

        for rec in reader:
            scanned += 1
            if scanned > args.max_rows:
                break

            raw = rec.get("url") or rec.get("link") or ""
            ex = extract_nested_aliexpress(raw)

            if ex.ulp:
                ulp_found += 1
            if ex.s_click_url:
                s_click_found += 1
            if ex.dl_target_url:
                dl_target_found += 1
            if ex.clean_product_url:
                clean_item_found += 1

            params = parse_param_field(rec.get("param"))
            discount_raw = params.get("discount") or ""
            try:
                discount_val = float(discount_raw.replace("%", "").strip())
            except Exception:
                discount_val = None
            if discount_val is not None and discount_val >= 10:
                discount_param_10 += 1

            oldp = parse_price(rec.get("oldprice"))
            price = parse_price(rec.get("price"))
            calc_discount = None
            if oldp and price and oldp > price:
                calc_discount = round(((oldp - price) / oldp) * 100, 2)
                if calc_discount >= 10:
                    oldprice_price_discount_10 += 1

            if len(samples) < 8 and (ex.clean_product_url or discount_val is not None):
                samples.append({
                    "id": rec.get("id"),
                    "title": (rec.get("name") or rec.get("title") or "")[:120],
                    "oldprice": rec.get("oldprice"),
                    "price": rec.get("price"),
                    "param_discount": discount_raw,
                    "calc_discount": calc_discount,
                    "item_id": ex.item_id,
                    "product_url": ex.clean_product_url,
                    "has_s_click": bool(ex.s_click_url),
                    "has_dl_target": bool(ex.dl_target_url),
                    "affiliate_url": raw,
                })

        shown_scanned = min(scanned, args.max_rows)
        print("Stats:")
        print(f"  scanned: {shown_scanned}")
        print(f"  ulp_found: {ulp_found}")
        print(f"  s_click_found: {s_click_found}")
        print(f"  dl_target_found: {dl_target_found}")
        print(f"  clean_item_found: {clean_item_found}")
        print(f"  discount_param >=10: {discount_param_10}")
        print(f"  oldprice/price discount >=10: {oldprice_price_discount_10}")
        print("")

        print("Sample extracted rows:")
        for i, s in enumerate(samples, 1):
            print("-" * 100)
            print(f"[{i}] id: {s['id']}")
            print(f"title: {s['title']}")
            print(f"oldprice: {s['oldprice']} | price: {s['price']} | param_discount: {s['param_discount']} | calc_discount: {s['calc_discount']}")
            print(f"item_id: {s['item_id']}")
            print(f"product_url: {s['product_url']}")
            print(f"has_s_click: {s['has_s_click']} | has_dl_target: {s['has_dl_target']}")
            print("affiliate_url_original:")
            print(s["affiliate_url"])
            print("PowerShell browser test:")
            print(f'Start-Process "{s["affiliate_url"]}"')
            if s["product_url"]:
                print(f'Start-Process "{s["product_url"]}"')

        print("")
        if clean_item_found > 0 and dl_target_found > 0:
            print("Conclusion:")
            print("  AliExpress WW feed contains nested s.click.aliexpress.com deeplinks with dl_target_url pointing to real aliexpress.com/item URLs.")
            print("  The safe fix is to preserve original affiliate_url from feed and extract productUrl from nested dl_target_url.")
        else:
            print("Conclusion:")
            print("  No nested product URLs found in this sample. Do not change production based on this provider yet.")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
