#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib import error as urllib_error
from urllib import request as urllib_request


DEFAULT_URL = "https://statuspage.me/lifetime-deal/partner/discounthub"
DEFAULT_OFFER_ID = "statuspage-me"
DEFAULT_STATE_FILE = Path("/var/lib/discounthub/statuspage-me-offer-watch.json")
DEFAULT_DB = Path("data/discounthub.sqlite3")

SOLD_OUT_PATTERNS = (
    r"\bsold\s*out\b",
    r"\bdeal\s+is\s+closed\b",
    r"\bno\s+(?:lifetime\s+)?licenses?\s+(?:are\s+)?remaining\b",
    r"\b0\s+remaining\b",
    r"\bavailability\s+0\s*/\s*\d+\s+left\b",
    r"\b0\s+of\s+\d+\s+lifetime\s+licenses?\s+remain\b",
)

REMAINING_PATTERNS = (
    r"\bavailability\s+(\d+)\s*/\s*(\d+)\s+left\b",
    r"\b(\d+)\s+remaining\b",
    r"\b(\d+)\s+of\s+(\d+)\s+lifetime\s+licenses?\s+remain\b",
    r"\blicenses?\s+claimed\s+\d+\s+of\s+(\d+).*?\b(\d+)\s+left\b",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def normalize_html(raw_html: str) -> str:
    without_scripts = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        " ",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", unescape(without_tags)).strip().lower()


def fetch_page(url: str, timeout: int) -> str:
    request = urllib_request.Request(
        url,
        headers={
            "User-Agent": (
                "DiscountHubOfferWatch/1.0 "
                "(availability verification; contact: https://discounthub.uz/contact/)"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"Unexpected HTTP status: {status}")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def detect_availability(page_text: str) -> tuple[str, int | None, int | None]:
    for pattern in SOLD_OUT_PATTERNS:
        if re.search(pattern, page_text, flags=re.IGNORECASE):
            return "sold_out", 0, None

    for index, pattern in enumerate(REMAINING_PATTERNS):
        match = re.search(pattern, page_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue

        first = int(match.group(1))
        second = int(match.group(2)) if match.lastindex and match.lastindex >= 2 else None

        if index == 0:
            remaining, total = first, second
        elif index == 1:
            remaining, total = first, None
        elif index == 2:
            remaining, total = first, second
        else:
            total, remaining = first, second

        if remaining <= 0:
            return "sold_out", 0, total
        return "available", remaining, total

    # The page currently uses both of these stable phrases while the offer is live.
    if "exclusive discounthub offer" in page_text and "get lifetime access" in page_text:
        return "available_unknown_count", None, None

    return "ambiguous", None, None


def load_state(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def expire_offer(db_path: Path, offer_id: str, dry_run: bool) -> str:
    if dry_run:
        return "dry_run_no_database_change"

    if not db_path.exists():
        raise RuntimeError(f"Database not found: {db_path}")

    expired_at = iso_now()
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, valid_until FROM partner_offers WHERE id = ?",
            (offer_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Partner offer not found in database: {offer_id}")

        current_valid_until = str(row[1] or "").strip()
        if current_valid_until:
            try:
                parsed = datetime.fromisoformat(current_valid_until.replace("Z", "+00:00"))
                if parsed <= utc_now():
                    return "already_expired"
            except ValueError:
                pass

        connection.execute(
            """
            UPDATE partner_offers
            SET valid_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (expired_at, expired_at, offer_id),
        )
        connection.commit()

    return f"expired_at_{expired_at}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check the StatusPage.me DiscountHub lifetime deal and hide the "
            "partner offer after repeated explicit sold-out confirmations."
        )
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--offer-id", default=DEFAULT_OFFER_ID)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--min-confirmations", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    confirmations_required = max(2, args.min_confirmations)
    state = load_state(args.state_file)
    checked_at = iso_now()

    try:
        html = fetch_page(args.url, max(5, args.timeout))
        page_text = normalize_html(html)
        status, remaining, total = detect_availability(page_text)
    except (
        urllib_error.URLError,
        urllib_error.HTTPError,
        TimeoutError,
        RuntimeError,
        OSError,
    ) as exc:
        state.update(
            {
                "checked_at": checked_at,
                "last_status": "check_error",
                "last_error": f"{type(exc).__name__}: {exc}",
            }
        )
        save_state(args.state_file, state)
        print(
            json.dumps(
                {
                    "status": "check_error",
                    "action": "kept_active",
                    "reason": str(exc),
                    "checkedAt": checked_at,
                },
                ensure_ascii=False,
            )
        )
        return 0

    consecutive_sold_out = int(state.get("consecutive_sold_out", 0) or 0)
    action = "kept_active"

    if status == "sold_out":
        consecutive_sold_out += 1
        if consecutive_sold_out >= confirmations_required:
            action = expire_offer(args.db, args.offer_id, args.dry_run)
    elif status in {"available", "available_unknown_count"}:
        consecutive_sold_out = 0
    else:
        # Ambiguous HTML must never close the deal.
        consecutive_sold_out = 0
        action = "kept_active_ambiguous_page"

    state.update(
        {
            "checked_at": checked_at,
            "last_status": status,
            "last_remaining": remaining,
            "last_total": total,
            "consecutive_sold_out": consecutive_sold_out,
            "last_action": action,
            "last_error": None,
        }
    )
    save_state(args.state_file, state)

    print(
        json.dumps(
            {
                "status": status,
                "remaining": remaining,
                "total": total,
                "confirmations": consecutive_sold_out,
                "confirmationsRequired": confirmations_required,
                "action": action,
                "checkedAt": checked_at,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
