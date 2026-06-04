#!/usr/bin/env python3
import argparse
import csv
import gzip
import io
import json
import re
import sqlite3
import sys
import urllib.request
from typing import Any

URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def collect_urls(value: Any, out: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return
        # Try JSON first.
        if (text.startswith('{') and text.endswith('}')) or (text.startswith('[') and text.endswith(']')):
            try:
                collect_urls(json.loads(text), out)
                return
            except Exception:
                pass
        for match in URL_RE.findall(text):
            out.append(match)
        return
    if isinstance(value, dict):
        for v in value.values():
            collect_urls(v, out)
        return
    if isinstance(value, (list, tuple)):
        for v in value:
            collect_urls(v, out)
        return


def pick_feed_url(row: sqlite3.Row) -> str | None:
    urls: list[str] = []
    for key in row.keys():
        collect_urls(row[key], urls)
    # Prefer Admitad product export URLs.
    for url in urls:
        if 'export.admitad.com' in url and 'products' in url:
            return url
    for url in urls:
        if 'export.admitad.com' in url:
            return url
    return urls[0] if urls else None


def fetch_bytes(url: str, timeout: int) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "DiscountHub-Stage81b/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get('Content-Type', '')


def decode_bytes(data: bytes, content_type: str) -> str:
    if data[:2] == b'\x1f\x8b' or 'gzip' in content_type.lower():
        data = gzip.decompress(data)
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def parse_price(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # Remove currency codes/symbols, keep first numeric token.
    text = text.replace(',', '')
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='/opt/discounthub/backend/data/discounthub.sqlite3')
    ap.add_argument('--provider-id', required=True)
    ap.add_argument('--max-rows', type=int, default=25000)
    ap.add_argument('--timeout', type=int, default=30)
    args = ap.parse_args()

    print('== Stage 81b Admitad sale_price probe ==')
    print(f'Provider: {args.provider_id}')
    print(f'DB: {args.db}')
    print(f'Max rows: {args.max_rows}')
    print('Mode: dry-run only; no import, no delete')
    print()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute('SELECT * FROM feed_providers WHERE id = ?', (args.provider_id,)).fetchone()
    if not row:
        print('Provider not found')
        return 2

    print('Provider row:')
    for k in ('id', 'name', 'adapter', 'enabled', 'last_status', 'last_imported_count', 'updated_at'):
        if k in row.keys():
            print(f'  {k}: {row[k]}')
    print()

    url = pick_feed_url(row)
    if not url:
        print('No feed URL found in provider row.')
        print('Available columns:', ', '.join(row.keys()))
        return 3

    print('Feed URL found: yes (not printed to avoid leaking tokens)')
    print('Fetching feed...')
    data, content_type = fetch_bytes(url, args.timeout)
    print(f'Downloaded bytes: {len(data)}')
    print(f'Content-Type: {content_type}')

    text = decode_bytes(data, content_type)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
    except csv.Error:
        # Admitad/Alibaba exports are normal comma-separated CSV files, but
        # csv.Sniffer can fail on wide quoted rows. Fall back to comma CSV.
        print('CSV sniffer could not determine delimiter; falling back to comma delimiter.')
        dialect = csv.excel
        dialect.delimiter = ','
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    print(f'Headers ({len(headers)}): {", ".join(headers[:40])}')
    print()

    scanned = 0
    missing_price = 0
    sale_price_present = 0
    sale_price_numeric = 0
    price_numeric = 0
    sale_lt_price = 0
    sale_eq_price = 0
    sale_gt_price = 0
    pass_1 = pass_5 = pass_10 = 0
    samples_discount: list[dict[str, Any]] = []
    samples_sale_present: list[dict[str, Any]] = []

    for r in reader:
        scanned += 1
        if scanned > args.max_rows:
            break
        price_raw = r.get('price') or r.get('Price')
        sale_raw = r.get('sale_price') or r.get('sale price') or r.get('salePrice') or r.get('Sale Price')
        price = parse_price(price_raw)
        sale = parse_price(sale_raw)
        if price is None:
            missing_price += 1
        else:
            price_numeric += 1
        if sale_raw not in (None, ''):
            sale_price_present += 1
            if len(samples_sale_present) < 5:
                samples_sale_present.append({
                    'title': (r.get('title') or r.get('name') or '')[:140],
                    'price': price_raw,
                    'sale_price': sale_raw,
                    'availability': r.get('availability'),
                    'link': (r.get('link') or '')[:220],
                })
        if sale is not None:
            sale_price_numeric += 1
        if price is None or sale is None or price <= 0:
            continue
        if sale < price:
            sale_lt_price += 1
            discount = ((price - sale) / price) * 100.0
            if discount >= 1:
                pass_1 += 1
            if discount >= 5:
                pass_5 += 1
            if discount >= 10:
                pass_10 += 1
            if discount >= 1 and len(samples_discount) < 10:
                samples_discount.append({
                    'title': (r.get('title') or r.get('name') or '')[:140],
                    'price': price_raw,
                    'sale_price': sale_raw,
                    'discount_percent': round(discount, 2),
                    'availability': r.get('availability'),
                    'link': (r.get('link') or '')[:220],
                })
        elif sale == price:
            sale_eq_price += 1
        else:
            sale_gt_price += 1

    print('Summary:')
    print(f'  scanned: {min(scanned, args.max_rows)}')
    print(f'  price numeric: {price_numeric}')
    print(f'  missing price: {missing_price}')
    print(f'  sale_price present: {sale_price_present}')
    print(f'  sale_price numeric: {sale_price_numeric}')
    print(f'  sale_price < price: {sale_lt_price}')
    print(f'  sale_price = price: {sale_eq_price}')
    print(f'  sale_price > price: {sale_gt_price}')
    print()
    print('Discount thresholds using price as old price and sale_price as current price:')
    print(f'  passed >= 1%:  {pass_1}')
    print(f'  passed >= 5%:  {pass_5}')
    print(f'  passed >= 10%: {pass_10}')
    print()

    print('Sample rows with sale_price:')
    if samples_sale_present:
        for s in samples_sale_present:
            print('  - ' + json.dumps(s, ensure_ascii=False))
    else:
        print('  none')
    print()

    print('Sample rows where sale_price gives a discount >= 1%:')
    if samples_discount:
        for s in samples_discount:
            print('  - ' + json.dumps(s, ensure_ascii=False))
    else:
        print('  none')
    print()

    if pass_10 > 0:
        print('Conclusion: sale_price may be usable as discounted price. Adapter should be reviewed before importing.')
    elif sale_price_present > 0:
        print('Conclusion: sale_price exists, but no row in this scan produced a valid discount >= 10%. Keep it out of app for now.')
    else:
        print('Conclusion: no sale_price data found. Keep it out of app for now.')

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
