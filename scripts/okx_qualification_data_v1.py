"""Public native-M15 acquisition and integrity only; no strategy/outcome imports."""

from __future__ import annotations

import argparse
import gzip
import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v3_okx_qualification_v1"
PRODUCTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP")
STEP = 900000
BODY_LIMIT = 2 * 1024 * 1024


class DataInvalid(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def millis(value):
    return int(datetime.fromisoformat(value).timestamp()) * 1000


def parse_page(body, cursor):
    data = json.loads(body, parse_float=Decimal)
    if data.get("code") != "0" or not isinstance(data.get("data"), list):
        raise DataInvalid("PUBLIC_API_FAILURE")
    rows, seen = [], set()
    for row in data["data"]:
        if not isinstance(row, list) or len(row) != 9 or row[8] != "1":
            raise DataInvalid("INVALID_OR_UNCOMPLETED_NATIVE_CANDLE")
        at = int(row[0])
        if at % STEP or at >= cursor or at in seen:
            raise DataInvalid("CANDLE_GRID_CURSOR_OR_DUPLICATE")
        values = [Decimal(str(x)) for x in row[1:8]]
        if any(not x.is_finite() for x in values):
            raise DataInvalid("NONFINITE_CANDLE")
        o, h, low, close = values[:4]
        if min(o, h, low, close) <= 0 or not low <= min(o, close) <= max(o, close) <= h:
            raise DataInvalid("INVALID_OHLC")
        if any(x < 0 for x in values[4:]):
            raise DataInvalid("NEGATIVE_VOLUME")
        rows.append([str(at), *[str(x) for x in values], "1"])
        seen.add(at)
    return sorted(rows, key=lambda r: int(r[0]))


def page_url(product, cursor):
    if product not in PRODUCTS or type(cursor) is not int or cursor <= 0:
        raise DataInvalid("PUBLIC_PRODUCT_OR_CURSOR_REQUIRED")
    return "https://www.okx.com/api/v5/market/history-candles?" + urlencode(
        {"instId": product, "bar": "15m", "after": cursor, "limit": 300}
    )


def fetch(product, cursor, folder):
    """Only one fixed official public GET family; TLS/proxy trust stays inherited."""
    url = page_url(product, cursor)
    name = str(cursor)
    raw, receipt = folder / (name + ".body"), folder / (name + ".receipt.json")
    if raw.exists() or receipt.exists():
        raise DataInvalid("EXISTING_CAPTURE_PRESERVED")
    started = datetime.now(UTC).isoformat()
    tick = time.monotonic()
    request = Request(
        url,
        headers={"User-Agent": "CryptoBot-Readiness/1", "Accept": "application/json"},
    )
    try:
        response = build_opener(NoRedirect()).open(request, timeout=20)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read(BODY_LIMIT + 1)
        status = response.code
        headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower()
            in {"date", "content-type", "retry-after", "x-ratelimit-remaining"}
        }
    folder.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(body)
    save(
        receipt,
        {
            "url": url,
            "method": "GET",
            "product": product,
            "after_ms": cursor,
            "request_started_at": started,
            "response_completed_at": datetime.now(UTC).isoformat(),
            "latency_ms": round((time.monotonic() - tick) * 1000, 3),
            "http_status": status,
            "headers": headers,
            "raw_path": str(raw.relative_to(ROOT)),
            "raw_sha256": sha256(body).hexdigest(),
            "body_bytes": len(body),
            "truncated": len(body) > BODY_LIMIT,
            "private_API": False,
        },
    )
    if status != 200 or len(body) > BODY_LIMIT:
        raise DataInvalid("HTTP_OR_BODY_LIMIT_STOP")
    return body


def retained_pages(folder, product, end):
    pages = []
    cursor = end
    for receipt in sorted(
        folder.glob("*.receipt.json"),
        key=lambda p: int(p.name.split(".")[0]),
        reverse=True,
    ):
        r = json.loads(receipt.read_text())
        raw = ROOT / r["raw_path"]
        if not raw.resolve().is_relative_to(folder.resolve()):
            raise DataInvalid("CAPTURE_PATH_OUTSIDE_ASSIGNED_PRODUCT")
        body = raw.read_bytes()
        if (
            r["product"] != product
            or r["after_ms"] != cursor
            or r["url"] != page_url(product, cursor)
            or sha256(body).hexdigest() != r["raw_sha256"]
            or len(body) != r["body_bytes"]
            or r["http_status"] != 200
            or r["truncated"]
        ):
            raise DataInvalid("RETAINED_PAGE_INTEGRITY_OR_CHAIN_STOP")
        rows = parse_page(body, cursor)
        if not rows:
            raise DataInvalid("EMPTY_HISTORY_BEFORE_REQUIRED_START")
        cursor = int(rows[0][0])
        pages.extend(rows)
    return pages, cursor


def validate_continuity(rows, start, end):
    indexed = {}
    for row in rows:
        at = int(row[0])
        if start <= at < end:
            if at in indexed:
                raise DataInvalid("CROSS_PAGE_DUPLICATE")
            indexed[at] = row
    missing = [t for t in range(start, end, STEP) if t not in indexed]
    if missing:
        raise DataInvalid(f"CONTINUITY_GAP:{len(missing)}:{missing[0]}")
    return [indexed[t] for t in range(start, end, STEP)]


def collect(product, max_pages=100):
    spec = json.loads((DEST / "STAGE_A_PREREGISTRATION.json").read_text())
    start, end = millis(spec["warmup_start"]), millis(spec["end_exclusive"])
    folder = DEST / "evidence/candles" / product
    pages, cursor = retained_pages(folder, product, end)
    for _ in range(max_pages):
        if cursor <= start:
            break
        body = fetch(product, cursor, folder)
        rows = parse_page(body, cursor)
        if not rows:
            raise DataInvalid("EMPTY_HISTORY_BEFORE_REQUIRED_START")
        cursor = int(rows[0][0])
        pages.extend(rows)
        save(
            DEST / f"checkpoints/{product}.json",
            {
                "product": product,
                "next_after_ms": cursor,
                "required_start_ms": start,
                "page_count": len(list(folder.glob("*.receipt.json"))),
                "complete": cursor <= start,
                "trade_entry_allowed": False,
            },
        )
        time.sleep(0.25)
    if cursor > start:
        return {
            "product": product,
            "state": "CHECKPOINTED_INCOMPLETE",
            "next_after_ms": cursor,
        }
    rows = validate_continuity(pages, start, end)
    content = "".join(compact(row) for row in rows).encode()
    target = DEST / "data" / (product + ".M15.jsonl.gz")
    target.parent.mkdir(parents=True, exist_ok=True)
    with (
        target.open("wb") as out,
        gzip.GzipFile(fileobj=out, filename="", mode="wb", mtime=0) as stream,
    ):
        stream.write(content)
    report = {
        "product": product,
        "state": "CONTINUOUS_NATIVE_M15_VERIFIED",
        "warmup_start": spec["warmup_start"],
        "development_start": spec["development_start"],
        "end_exclusive": spec["end_exclusive"],
        "bars": len(rows),
        "step_ms": STEP,
        "gaps": 0,
        "interpolation": False,
        "completed_bar_marker": "confirm=1",
        "data_path": str(target.relative_to(ROOT)),
        "stored_sha256": sha256(target.read_bytes()).hexdigest(),
        "content_sha256": sha256(content).hexdigest(),
        "historical_actual_publication_latency_verified": False,
        "historical_tick_epochs_verified": False,
        "financial_authorization": False,
        "trade_entry_allowed": False,
    }
    save(DEST / f"checkpoints/{product}.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", choices=PRODUCTS, required=True)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 1000:
        parser.error("max-pages must be 1..1000")
    print(compact(collect(args.product, args.max_pages)), end="")


if __name__ == "__main__":
    main()
