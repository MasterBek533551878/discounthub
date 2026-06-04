#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, gzip, io, json, re, sqlite3, urllib.request
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
TITLE_KEYS = ("title","name","product_name","productname","product title","product_title","item_title","item name","model","product")
LINK_KEYS = ("aw_deep_link","deeplink","deep_link","tracking_url","affiliate_url","gotolink","go_to_link","url","link","product_url","producturl","merchant_deep_link","merchant_url","product link","product_link")
IMAGE_KEYS = ("image","image_url","imageurl","picture","picture_url","thumbnail","aw_image_url","merchant_image_url","main_image","product_image","image link","image_link")
CURRENT_PRICE_KEYS = ("price","sale_price","saleprice","current_price","currentprice","now_price","discount_price","final_price","special_price","amount","search_price","price_amount","base_price_amount","product_price")
OLD_PRICE_KEYS = ("old_price","oldprice","original_price","originalprice","was_price","list_price","rrp","msrp","retail_price","strike_price","regular_price","base_price","compare_at_price")
AVAILABILITY_KEYS = ("availability","stock","stock_status","in_stock","is_in_stock","inventory")

def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def get_any(row: dict[str, str], keys: Iterable[str]) -> str | None:
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
    if not value: return None
    s = str(value).strip().replace("\u00a0", " ")
    s = re.sub(r"[A-Za-z$€£¥₽₩₺₹₴₸]+", "", s)
    s = re.sub(r"[^0-9,.\-]", "", s)
    if not s or s in {"-", ".", ","}: return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = ("".join(parts[:-1]) + "." + parts[-1]) if len(parts[-1]) in (1,2) and len(parts) > 1 else s.replace(",", "")
    try:
        d = Decimal(s)
        return d if d > 0 else None
    except InvalidOperation:
        return None

def is_out_of_stock(value: str | None) -> bool:
    if not value: return False
    s = value.strip().lower()
    return any(t in s for t in ("out of stock","out_of_stock","outofstock","unavailable","not available","sold out","sold_out","no stock","false","0"))

def find_urls_in_obj(obj: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values(): urls.extend(find_urls_in_obj(v))
    elif isinstance(obj, list):
        for v in obj: urls.extend(find_urls_in_obj(v))
    elif isinstance(obj, str):
        urls.extend(URL_RE.findall(obj))
    return urls

def candidate_urls_from_provider(row: sqlite3.Row) -> list[str]:
    urls: list[str] = []
    for key in row.keys():
        value = row[key]
        if value is None: continue
        text = str(value).strip()
        if not text: continue
        urls.extend(URL_RE.findall(text))
        if text.startswith("{") or text.startswith("["):
            try: urls.extend(find_urls_in_obj(json.loads(text)))
            except Exception: pass
    def score(url: str) -> tuple[int,int]:
        u = url.lower(); s = 0
        if any(x in u for x in ("product","feed",".csv",".gz")): s += 100
        if "rzekl.com/g/" in u or "ad.admitad.com/g/" in u: s -= 50
        if "alibaba" in u: s += 10
        return (-s, len(url))
    out, seen = [], set()
    for url in urls:
        clean = url.rstrip(",);]")
        if clean not in seen:
            seen.add(clean); out.append(clean)
    return sorted(out, key=score)

def fetch_bytes(url: str, timeout: int):
    req = urllib.request.Request(url, headers={"User-Agent":"DiscountHub-Stage81-Diagnostics/1.0","Accept":"text/csv,application/csv,application/gzip,application/octet-stream,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type")

def decode_feed(data: bytes, url: str, content_type: str | None) -> str:
    if url.lower().endswith(".gz") or data[:2] == b"\x1f\x8b" or (content_type and "gzip" in content_type.lower()):
        data = gzip.decompress(data)
    for enc in ("utf-8-sig","utf-8","latin-1","cp1252"):
        try: return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode("utf-8", errors="replace")

def discount_percent(old: Decimal, current: Decimal) -> Decimal:
    return ((old - current) / old) * Decimal("100")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/discounthub.sqlite3")
    p.add_argument("--provider-id", default="admitad_20881_alibaba_ww_v1")
    p.add_argument("--max-rows", type=int, default=25000)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--sample-limit", type=int, default=5)
    args = p.parse_args()

    print("== Stage 81 Admitad provider discount diagnostics ==")
    print(f"Provider: {args.provider_id}")
    print(f"DB: {args.db}")
    print(f"Max rows: {args.max_rows}")
    print("Mode: dry-run only; no import, no delete\n")

    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    provider = cur.execute("SELECT * FROM feed_providers WHERE id = ?", (args.provider_id,)).fetchone()
    if not provider:
        print(f"ERROR: provider not found: {args.provider_id}"); return 2
    print("Provider row:")
    for key in ("id","name","adapter","enabled","last_status","last_imported_count","updated_at"):
        if key in provider.keys(): print(f"  {key}: {provider[key]}")
    print()
    urls = candidate_urls_from_provider(provider)
    if not urls:
        print("ERROR: No URL found in provider row. Columns:")
        for key in provider.keys(): print(f"  {key}: {str(provider[key])[:180] if provider[key] is not None else ''}")
        return 3
    print("Candidate URLs:")
    for i, url in enumerate(urls[:10], 1):
        print(f"  [{i}] " + re.sub(r"/([A-Za-z0-9_\-]{20,})/", "/***TOKEN***/", url))
    print()
    feed_url = urls[0]
    print("Fetching selected feed URL...")
    data, content_type = fetch_bytes(feed_url, args.timeout)
    text = decode_feed(data, feed_url, content_type)
    print(f"Downloaded bytes: {len(data)}")
    print(f"Content-Type: {content_type}\n")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    print(f"Headers ({len(headers)}): {', '.join(headers[:40])}" + (" ..." if len(headers) > 40 else ""))
    print()

    stats = {k:0 for k in ["scanned","missing_title","missing_link","missing_image","missing_price","out_of_stock","no_discount_pair","below_1","below_5","below_10","passed_1","passed_5","passed_10"]}
    samples10=[]; samples5=[]; samples1=[]; samples_no=[]; price_seen={}; old_seen={}; avail_seen={}
    for row in reader:
        if stats["scanned"] >= args.max_rows: break
        stats["scanned"] += 1
        title=get_any(row,TITLE_KEYS); link=get_any(row,LINK_KEYS); image=get_any(row,IMAGE_KEYS); availability=get_any(row,AVAILABILITY_KEYS)
        if availability: avail_seen[availability[:80]]=avail_seen.get(availability[:80],0)+1
        if not title: stats["missing_title"]+=1; continue
        if not link: stats["missing_link"]+=1; continue
        if not image: stats["missing_image"]+=1; continue
        if is_out_of_stock(availability): stats["out_of_stock"]+=1; continue
        current_raw=get_any(row,CURRENT_PRICE_KEYS); old_raw=get_any(row,OLD_PRICE_KEYS)
        for key, value in row.items():
            nk=norm_key(key)
            if value and any(t in nk for t in ("price","amount","rrp","msrp")): price_seen[key]=price_seen.get(key,0)+1
            if value and any(t in nk for t in ("old","original","was","list","rrp","msrp","retail","regular","base")): old_seen[key]=old_seen.get(key,0)+1
        current=parse_decimal(current_raw); old=parse_decimal(old_raw)
        if current is None: stats["missing_price"]+=1; continue
        if old is None or old <= current:
            stats["no_discount_pair"]+=1
            if len(samples_no)<args.sample_limit: samples_no.append({"title":title[:120],"current_raw":current_raw,"old_raw":old_raw,"link":link[:160]})
            continue
        pct=discount_percent(old,current)
        item={"title":title[:120],"discount":f"{pct:.2f}%","current":str(current),"old":str(old),"link":link[:160]}
        if pct>=1: stats["passed_1"]+=1; samples1.append(item) if len(samples1)<args.sample_limit else None
        else: stats["below_1"]+=1
        if pct>=5: stats["passed_5"]+=1; samples5.append(item) if len(samples5)<args.sample_limit else None
        else: stats["below_5"]+=1
        if pct>=10: stats["passed_10"]+=1; samples10.append(item) if len(samples10)<args.sample_limit else None
        else: stats["below_10"]+=1

    print("Summary:")
    for k in ["scanned","missing_title","missing_link","missing_image","missing_price","out_of_stock","no_discount_pair"]: print(f"  {k}: {stats[k]}")
    print("\nDiscount thresholds:")
    print(f"  passed >= 1%:  {stats['passed_1']}")
    print(f"  passed >= 5%:  {stats['passed_5']}")
    print(f"  passed >= 10%: {stats['passed_10']}")
    print(f"  below 10%:     {stats['below_10']}\n")
    print("Price-like fields seen:")
    for k,c in sorted(price_seen.items(), key=lambda kv:(-kv[1],kv[0]))[:30]: print(f"  {k}: {c}")
    print("\nOld-price-like fields seen:")
    for k,c in sorted(old_seen.items(), key=lambda kv:(-kv[1],kv[0]))[:30]: print(f"  {k}: {c}")
    print("\nAvailability values:")
    for k,c in sorted(avail_seen.items(), key=lambda kv:(-kv[1],kv[0]))[:20]: print(f"  {k}: {c}")
    def ps(title, samples):
        print("\n"+title)
        if not samples: print("  none")
        for s in samples: print("  - "+json.dumps(s, ensure_ascii=False))
    ps("Sample passed >= 10%:", samples10); ps("Sample passed >= 5%:", samples5); ps("Sample passed >= 1%:", samples1); ps("Sample rows with no valid discount pair:", samples_no)
    print("\nConclusion:")
    if stats['passed_10']>0:
        print("  This provider has rows that can pass DiscountHub production discount rules. Next step: sync and test /click.")
    elif stats['passed_1']>0:
        print("  This provider has discounted rows, but none reached the current 10% threshold in this scan.")
    else:
        print("  No rows with a valid old/current discount pair were found in this scan. Keep it out of app for now.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
