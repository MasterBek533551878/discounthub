#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, gzip, io, json, re, sqlite3, urllib.parse, urllib.request
from decimal import Decimal, InvalidOperation
from typing import Any

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
LINK_KEYS = (
    "link", "url", "product_url", "producturl", "aw_deep_link", "merchant_deep_link",
    "gotolink", "go_to_link", "deeplink", "deep_link", "tracking_url", "affiliate_url",
)
TITLE_KEYS = ("title", "name", "product_name", "productname")


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def get_any(row: dict[str, str], keys: tuple[str, ...]) -> str | None:
    normalized = {norm_key(k): v for k, v in row.items()}
    for key in keys:
        nk = norm_key(key)
        if nk in normalized and str(normalized[nk]).strip():
            return str(normalized[nk]).strip()
    for key in keys:
        nk = norm_key(key)
        for rk, value in normalized.items():
            if (nk == rk or rk.endswith("_" + nk) or nk in rk) and str(value).strip():
                return str(value).strip()
    return None


def parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    s = str(value).strip().replace("\u00a0", " ")
    s = re.sub(r"[A-Za-z$€£¥₽₩₺₹₴₸]+", "", s)
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s or s in {"-", ".", ","}:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = ("".join(parts[:-1]) + "." + parts[-1]) if len(parts[-1]) in (1, 2) and len(parts) > 1 else s.replace(",", "")
    try:
        value = Decimal(s)
        return value if value > 0 else None
    except InvalidOperation:
        return None


def urls_in_obj(obj: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            urls.extend(urls_in_obj(v))
    elif isinstance(obj, list):
        for v in obj:
            urls.extend(urls_in_obj(v))
    elif isinstance(obj, str):
        urls.extend(URL_RE.findall(obj))
    return urls


def candidate_urls_from_provider(row: sqlite3.Row) -> list[str]:
    urls: list[str] = []
    for key in row.keys():
        value = row[key]
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        urls.extend(URL_RE.findall(text))
        if text.startswith("{") or text.startswith("["):
            try:
                urls.extend(urls_in_obj(json.loads(text)))
            except Exception:
                pass

    def score(url: str) -> tuple[int, int]:
        u = url.lower()
        s = 0
        if any(x in u for x in ("product", "feed", ".csv", ".gz", "export_adv_products")):
            s += 100
        if "rzekl.com/g/" in u or "ad.admitad.com/g/" in u:
            s -= 50
        return (-s, len(url))

    out, seen = [], set()
    for url in urls:
        clean = url.rstrip(",);]")
        if clean not in seen:
            seen.add(clean)
            out.append(clean)
    return sorted(out, key=score)


def mask_url(url: str) -> str:
    # Hide long feed tokens but keep enough shape for debugging.
    url = re.sub(r"/(?:[A-Za-z0-9_\-]{20,})/", "/***TOKEN***/", url)
    url = re.sub(r"(code=)[^&#]+", r"\1***CODE***", url)
    url = re.sub(r"(user=)[^&#]+", r"\1***USER***", url)
    return url[:260]


def fetch_bytes(url: str, timeout: int) -> tuple[bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "DiscountHub-Stage82-Theory/1.0", "Accept": "text/csv,application/csv,application/gzip,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type")


def decode_feed(data: bytes, url: str, content_type: str | None) -> str:
    if url.lower().endswith(".gz") or data[:2] == b"\x1f\x8b" or (content_type and "gzip" in content_type.lower()):
        data = gzip.decompress(data)
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def decoded_candidates(value: str | None) -> list[str]:
    if not value:
        return []
    out = [value]
    current = value
    for _ in range(4):
        decoded = urllib.parse.unquote(current)
        if decoded == current:
            break
        out.append(decoded)
        current = decoded
    return out


def nested_values(value: str | None) -> list[str]:
    found: list[str] = []
    for candidate in decoded_candidates(value):
        parsed = urllib.parse.urlparse(candidate)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        for key in ("ulp", "url", "target_url", "dl_target_url", "redirect", "u"):
            for v in params.get(key, []):
                if v:
                    found.append(v)
    return found


def classify_url(value: str | None) -> str:
    if not value:
        return "empty"
    parsed = urllib.parse.urlparse(value)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "rzekl.com" in host or "rztekl.com" in host or "ad.admitad.com" in host:
        return "admitad_tracking"
    if "aliexpress." in host and "/item/" in path:
        return "aliexpress_item"
    if "alitems.com" in host:
        return "alitems"
    if "alibaba.com" in host and "/product-detail/" in path:
        return "alibaba_product_detail"
    if "offer.alibaba.com" in host and "/cps/" in path and "productId" in query:
        return "offer_alibaba_cps_productid"
    if "alibaba.com" in host and "/trade/search" in path:
        return "alibaba_search"
    if "alibaba.com" in host:
        return "alibaba_other"
    return f"other:{host or 'no-host'}"


def old_extract_aliexpress_item_only(value: str | None) -> str | None:
    if not value:
        return None
    for candidate in decoded_candidates(value) + nested_values(value):
        parsed = urllib.parse.urlparse(candidate)
        if "aliexpress." in parsed.netloc.lower() and "/item/" in parsed.path.lower():
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
    return None


def proposed_extract_from_zip(value: str | None) -> str | None:
    if not value:
        return None
    # Mirrors the uploaded idea: aliexpress item, alitems, alibaba product-detail, nested params.
    to_check = decoded_candidates(value)
    checked = 0
    while to_check and checked < 30:
        checked += 1
        candidate = to_check.pop(0)
        parsed = urllib.parse.urlparse(candidate)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        if "aliexpress." in host and "/item/" in path:
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        if "alitems.com" in host:
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        if "alibaba.com" in host and "/product-detail/" in path:
            return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        for n in nested_values(candidate):
            to_check.extend(decoded_candidates(n))
    return None


def offer_alibaba_product_id(value: str | None) -> str | None:
    for candidate in decoded_candidates(value) + nested_values(value):
        parsed = urllib.parse.urlparse(candidate)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if "offer.alibaba.com" in host and "/cps/" in path and params.get("productId"):
            return params["productId"][0]
    return None


def analyze_provider(conn: sqlite3.Connection, provider_id: str, max_rows: int, timeout: int) -> int:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    provider = cur.execute("SELECT * FROM feed_providers WHERE id = ?", (provider_id,)).fetchone()
    print("\n" + "=" * 100)
    print(f"Provider: {provider_id}")
    if not provider:
        print("ERROR: provider not found")
        return 2
    for key in ("id", "name", "adapter", "enabled", "last_status", "last_imported_count", "updated_at"):
        if key in provider.keys():
            print(f"  {key}: {provider[key]}")
    urls = candidate_urls_from_provider(provider)
    if not urls:
        print("ERROR: no feed URL found in provider row")
        return 3
    feed_url = urls[0]
    print(f"Feed URL: {mask_url(feed_url)}")
    data, content_type = fetch_bytes(feed_url, timeout)
    text = decode_feed(data, feed_url, content_type)
    print(f"Downloaded bytes: {len(data)}")
    print(f"Content-Type: {content_type}")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    print(f"Headers ({len(headers)}): {', '.join(headers[:30])}" + (" ..." if len(headers) > 30 else ""))

    stats: dict[str, int] = {
        "scanned": 0,
        "old_extract_ok": 0,
        "proposed_extract_ok": 0,
        "offer_alibaba_productid": 0,
        "sale_price_discount_10": 0,
    }
    raw_classes: dict[str, int] = {}
    nested_classes: dict[str, int] = {}
    samples = {"old": [], "proposed": [], "offer": [], "raw": [], "sale": []}

    for row in reader:
        if stats["scanned"] >= max_rows:
            break
        stats["scanned"] += 1
        title = get_any(row, TITLE_KEYS) or ""
        raw = get_any(row, LINK_KEYS) or ""
        raw_class = classify_url(raw)
        raw_classes[raw_class] = raw_classes.get(raw_class, 0) + 1
        for n in nested_values(raw):
            cls = classify_url(n)
            nested_classes[cls] = nested_classes.get(cls, 0) + 1
        old = old_extract_aliexpress_item_only(raw)
        proposed = proposed_extract_from_zip(raw)
        pid = offer_alibaba_product_id(raw)
        if old:
            stats["old_extract_ok"] += 1
            if len(samples["old"]) < 5:
                samples["old"].append({"title": title[:90], "extracted": mask_url(old)})
        if proposed:
            stats["proposed_extract_ok"] += 1
            if len(samples["proposed"]) < 5:
                samples["proposed"].append({"title": title[:90], "extracted": mask_url(proposed), "class": classify_url(proposed)})
        if pid:
            stats["offer_alibaba_productid"] += 1
            if len(samples["offer"]) < 8:
                samples["offer"].append({"title": title[:90], "productId": pid, "raw_class": raw_class, "raw": mask_url(raw)})
        price = parse_decimal(row.get("price"))
        sale = parse_decimal(row.get("sale_price"))
        if price and sale and sale < price:
            pct = ((price - sale) / price) * Decimal("100")
            if pct >= 10:
                stats["sale_price_discount_10"] += 1
                if len(samples["sale"]) < 5:
                    samples["sale"].append({"title": title[:90], "price": str(price), "sale_price": str(sale), "discount_percent": f"{pct:.2f}", "raw": mask_url(raw)})
        if len(samples["raw"]) < 5:
            samples["raw"].append({"title": title[:90], "raw_class": raw_class, "raw": mask_url(raw), "nested": [classify_url(n) for n in nested_values(raw)[:3]]})

    print("\nStats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nRaw link classes:")
    for k, v in sorted(raw_classes.items(), key=lambda kv: (-kv[1], kv[0]))[:25]:
        print(f"  {k}: {v}")
    print("\nNested URL classes:")
    for k, v in sorted(nested_classes.items(), key=lambda kv: (-kv[1], kv[0]))[:25]:
        print(f"  {k}: {v}")
    for name, items in samples.items():
        print(f"\nSample {name}:")
        if not items:
            print("  none")
        for item in items:
            print("  - " + json.dumps(item, ensure_ascii=False))

    print("\nInterpretation:")
    if stats["proposed_extract_ok"] == 0 and stats["offer_alibaba_productid"]:
        print("  Uploaded extractor idea will NOT fix this provider alone: feed links contain offer.alibaba.com/cps productId, not alibaba.com/product-detail URLs.")
    elif stats["proposed_extract_ok"] > stats["old_extract_ok"]:
        print("  Uploaded extractor idea improves target extraction for this provider. Next step is live link validation before production import.")
    else:
        print("  Uploaded extractor idea does not materially improve extraction for this provider in this scan.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/discounthub.sqlite3")
    p.add_argument("--provider-ids", default="admitad_20881_alibaba_ww_v1,admitad_6115_aliexpress_ww_v1")
    p.add_argument("--max-rows", type=int, default=500)
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()
    print("== Stage 82 Admitad URL extractor theory diagnostics ==")
    print(f"DB: {args.db}")
    print(f"Max rows/provider: {args.max_rows}")
    print("Mode: dry-run only; no import, no delete")
    conn = sqlite3.connect(args.db)
    code = 0
    for provider_id in [x.strip() for x in args.provider_ids.split(",") if x.strip()]:
        try:
            code = max(code, analyze_provider(conn, provider_id, args.max_rows, args.timeout))
        except Exception as e:
            print("\n" + "=" * 100)
            print(f"Provider: {provider_id}")
            print(f"ERROR: {type(e).__name__}: {e}")
            code = max(code, 10)
    conn.close()
    return code

if __name__ == "__main__":
    raise SystemExit(main())
