"""Bounded public venue probes in cloud/ordinary CI; no order/private client."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

PROBES: dict[str, list[tuple[Any, ...]]] = {
    "okx": [
        ("instruments", "https://www.okx.com/api/v5/public/instruments?instType=SWAP"),
        (
            "book_BTC",
            "https://www.okx.com/api/v5/market/books?instId=BTC-USDT-SWAP&sz=400",
        ),
        (
            "book_ETH",
            "https://www.okx.com/api/v5/market/books?instId=ETH-USDT-SWAP&sz=400",
        ),
    ],
    "binance_futures": [
        ("instruments", "https://fapi.binance.com/fapi/v1/exchangeInfo"),
        ("book_BTC", "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=100"),
        ("book_ETH", "https://fapi.binance.com/fapi/v1/depth?symbol=ETHUSDT&limit=100"),
    ],
    "hyperliquid": [
        ("instruments", "https://api.hyperliquid.xyz/info", {"type": "meta"}),
        (
            "book_BTC",
            "https://api.hyperliquid.xyz/info",
            {"type": "l2Book", "coin": "BTC"},
        ),
        (
            "book_ETH",
            "https://api.hyperliquid.xyz/info",
            {"type": "l2Book", "coin": "ETH"},
        ),
    ],
    "gate": [
        ("instruments", "https://api.gateio.ws/api/v4/futures/usdt/contracts"),
        (
            "book_BTC",
            "https://api.gateio.ws/api/v4/futures/usdt/order_book?contract=BTC_USDT&limit=100",
        ),
        (
            "book_ETH",
            "https://api.gateio.ws/api/v4/futures/usdt/order_book?contract=ETH_USDT&limit=100",
        ),
    ],
    "bitget": [
        (
            "instruments",
            "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES",
        ),
        (
            "book_BTC",
            "https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=BTCUSDT&productType=USDT-FUTURES&precision=scale0&limit=100",
        ),
        (
            "book_ETH",
            "https://api.bitget.com/api/v2/mix/market/merge-depth?symbol=ETHUSDT&productType=USDT-FUTURES&precision=scale0&limit=100",
        ),
    ],
    "bybit": [
        (
            "instruments",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT",
        ),
        (
            "book_BTC",
            "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=50",
        ),
        (
            "book_ETH",
            "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=ETHUSDT&limit=50",
        ),
    ],
    "kucoin_futures": [
        ("instruments", "https://api-futures.kucoin.com/api/v1/contracts/active"),
        (
            "book_BTC",
            "https://api-futures.kucoin.com/api/v1/level2/depth20?symbol=XBTUSDTM",
        ),
        (
            "book_ETH",
            "https://api-futures.kucoin.com/api/v1/level2/depth20?symbol=ETHUSDTM",
        ),
    ],
    "blofin": [
        ("instruments", "https://openapi.blofin.com/api/v1/market/instruments"),
        (
            "book_BTC",
            "https://openapi.blofin.com/api/v1/market/books?instId=BTC-USDT&size=100",
        ),
        (
            "book_ETH",
            "https://openapi.blofin.com/api/v1/market/books?instId=ETH-USDT&size=100",
        ),
    ],
    "mexc": [
        ("instruments", "https://contract.mexc.com/api/v1/contract/detail"),
        (
            "book_BTC",
            "https://contract.mexc.com/api/v1/contract/depth/BTC_USDT?limit=100",
        ),
        (
            "book_ETH",
            "https://contract.mexc.com/api/v1/contract/depth/ETH_USDT?limit=100",
        ),
    ],
    "kraken_futures": [
        ("instruments", "https://futures.kraken.com/derivatives/api/v3/instruments"),
        (
            "book_BTC",
            "https://futures.kraken.com/derivatives/api/v3/orderbook?symbol=PF_XBTUSD",
        ),
        (
            "book_ETH",
            "https://futures.kraken.com/derivatives/api/v3/orderbook?symbol=PF_ETHUSD",
        ),
    ],
    "coinbase_international": [
        ("instruments", "https://api.international.coinbase.com/api/v1/instruments"),
        (
            "book_BTC",
            "https://api.international.coinbase.com/api/v1/instruments/BTC-PERP/book?depth=100",
        ),
        (
            "book_ETH",
            "https://api.international.coinbase.com/api/v1/instruments/ETH-PERP/book?depth=100",
        ),
    ],
    "deribit": [
        (
            "instruments",
            "https://www.deribit.com/api/v2/public/get_instruments?currency=USDC&kind=future&expired=false",
        ),
        (
            "book_BTC",
            "https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC_USDC-PERPETUAL&depth=100",
        ),
        (
            "book_ETH",
            "https://www.deribit.com/api/v2/public/get_order_book?instrument_name=ETH_USDC-PERPETUAL&depth=100",
        ),
    ],
}
ALLOWED_URLS = {item[1] for probes in PROBES.values() for item in probes}
SAFE_HEADERS = {
    "content-type",
    "content-length",
    "date",
    "etag",
    "last-modified",
    "retry-after",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "x-mbx-used-weight-1m",
}
LIMIT = 4 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate(url, method="GET", payload=None):
    p = urlparse(url)
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.port
        or p.fragment
        or url not in ALLOWED_URLS
    ):
        raise ValueError("EXACT_PUBLIC_PROBE_URL_REQUIRED")
    params = parse_qs(p.query, keep_blank_values=True, strict_parsing=True)
    if any(
        k.lower() in {"api_key", "signature", "secret", "token", "password", "cookie"}
        for k in params
    ):
        raise ValueError("CREDENTIAL_QUERY_FORBIDDEN")
    if method == "POST":
        if url != "https://api.hyperliquid.xyz/info" or payload not in (
            {"type": "meta"},
            {"type": "l2Book", "coin": "BTC"},
            {"type": "l2Book", "coin": "ETH"},
        ):
            raise ValueError("PUBLIC_INFO_ONLY")
    elif method != "GET" or payload is not None:
        raise ValueError("PUBLIC_READ_ONLY")


def capture(
    url,
    dest,
    *,
    method="GET",
    payload=None,
    source_kind="PUBLIC_ENDPOINT",
    environment="CODEX_CLOUD",
):
    validate(url, method, payload)
    if environment not in {"CODEX_CLOUD", "GITHUB_HOSTED_CI"}:
        raise ValueError("APPROVED_ENVIRONMENT_REQUIRED")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    ident = sha256(
        (started + url + json.dumps(payload, sort_keys=True)).encode()
    ).hexdigest()[:24]
    headers = {
        "User-Agent": "CryptoBot-PublicVenueAudit/1",
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    begin = time.monotonic()
    status, filtered, raw, error = None, {}, b"", None
    try:
        response = build_opener(NoRedirect()).open(request, timeout=15)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError) as exc:
        response, error = None, type(exc).__name__
    if response is not None:
        with response:
            status = response.code
            filtered = {
                k.lower(): v
                for k, v in response.headers.items()
                if k.lower() in SAFE_HEADERS
            }
            raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raw, error = raw[:LIMIT], "TRUNCATED_UNVERIFIABLE"
    completed = datetime.now(UTC).isoformat()
    body = dest / (ident + ".body")
    receipt_path = dest / (ident + ".receipt.json")
    with body.open("xb") as stream:
        stream.write(raw)
    receipt = {
        "environment": environment,
        "url": url,
        "method": method,
        "payload": payload,
        "source_kind": source_kind,
        "request_started_at": started,
        "response_completed_at": completed,
        "latency_ms": format((time.monotonic() - begin) * 1000, ".3f"),
        "http_status": status,
        "headers": filtered,
        "raw_file": body.name,
        "raw_sha256": sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
        "error_class": error,
        "private_api": False,
        "truncated": error == "TRUNCATED_UNVERIFIABLE",
    }
    with receipt_path.open("x") as stream:
        stream.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return {**receipt, "receipt_file": str(receipt_path)}


def probe_all(dest, environment):
    def run(job):
        venue, name, url, payload = job
        r = capture(
            url,
            Path(dest) / venue,
            method="POST" if payload is not None else "GET",
            payload=payload,
            source_kind=name,
            environment=environment,
        )
        return {"venue": venue, **r}

    jobs = [
        (venue, item[0], item[1], item[2] if len(item) > 2 else None)
        for venue, items in PROBES.items()
        for item in items
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(run, jobs))
    # Repeat book samples on the same approved route after all first probes finish;
    # never repeat a blocked route. No favorable-snapshot selection.
    repeats = [
        (r["venue"], r["source_kind"] + "_second", r["url"], r["payload"])
        for r in records
        if r["source_kind"].startswith("book_")
        and r["http_status"] == 200
        and not r["truncated"]
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        records.extend(pool.map(run, repeats))
    summary = {
        "environment": environment,
        "probes": records,
        "strategy_or_orders_run": False,
    }
    with (Path(dest) / "PROBE_SUMMARY.json").open("x") as stream:
        stream.write(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--environment", choices=("CODEX_CLOUD", "GITHUB_HOSTED_CI"), required=True
    )
    args = p.parse_args()
    summary = probe_all(args.output, args.environment)
    print(
        json.dumps(
            {
                "environment": args.environment,
                "probe_count": len(summary["probes"]),
                "orders_run": False,
            }
        )
    )


if __name__ == "__main__":
    main()
