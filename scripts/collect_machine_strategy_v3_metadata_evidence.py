"""Bounded public metadata searches; retain raw bytes and separate retrieval times."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v3_market_metadata_recovery/evidence/root_search"
ALLOWED = {
    "web.archive.org",
    "arquivo.pt",
    "index.commoncrawl.org",
    "api.github.com",
    "raw.githubusercontent.com",
    "api.bybit.com",
    "bybit-exchange.github.io",
    "api.tardis.dev",
    "docs.tardis.dev",
}


def query(host, endpoint, **params):
    return "https://" + host + endpoint + "?" + urlencode(params)


def searches():
    result = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        result.append(
            (
                "current_api_" + symbol,
                "CURRENT_CONTEXT_ONLY",
                query(
                    "api.bybit.com",
                    "/v5/market/instruments-info",
                    category="linear",
                    symbol=symbol,
                ),
            )
        )
        for endpoint in ("v5/market/instruments-info*", "v2/public/symbols*"):
            label = symbol + "_" + endpoint.split("/")[0]
            result.append(
                (
                    "wayback_api_" + label,
                    "ARCHIVE_INDEX",
                    query(
                        "web.archive.org",
                        "/cdx/search/cdx",
                        url="api.bybit.com/" + endpoint,
                        output="json",
                        **{
                            "from": "20210101",
                            "to": "20251205",
                            "filter": "statuscode:200",
                            "collapse": "digest",
                            "limit": 200,
                        },
                    ),
                )
            )
            result.append(
                (
                    "arquivo_api_" + label,
                    "ARCHIVE_INDEX",
                    query(
                        "arquivo.pt",
                        "/wayback/cdx",
                        url="api.bybit.com/" + endpoint,
                        output="json",
                        **{
                            "from": "20210101",
                            "to": "20251205",
                            "filter": "status:200",
                            "collapse": "digest",
                            "limit": 200,
                        },
                    ),
                )
            )
        result.append(
            (
                "tardis_instrument_" + symbol,
                "THIRD_PARTY_INSTRUMENT_METADATA",
                "https://api.tardis.dev/v1/instruments/bybit/" + symbol,
            )
        )
        for wording in (
            symbol + " tick",
            symbol + " priceFilter",
            symbol + " tickSize",
        ):
            result.append(
                (
                    "arquivo_text_" + wording.replace(" ", "_"),
                    "ARCHIVE_TEXT_INDEX",
                    query(
                        "arquivo.pt",
                        "/textsearch",
                        q=wording,
                        siteSearch="announcements.bybit.com",
                        **{"from": "20210101000000"},
                        to="20251205233000",
                        maxItems=50,
                    ),
                )
            )
    for year in (2022, 2023, 2024, 2025):
        result.append(
            (
                "official_doc_history_" + str(year),
                "OFFICIAL_DOC_GIT_CONTEXT_ONLY",
                query(
                    "api.github.com",
                    "/repos/bybit-exchange/docs/commits",
                    path="docs/v5/market/instrument.mdx",
                    until=f"{year}-12-05T23:30:00Z",
                    per_page=1,
                ),
            )
        )
    result.append(
        (
            "tardis_exchange_catalog",
            "THIRD_PARTY_INSTRUMENT_METADATA",
            "https://api.tardis.dev/v1/exchanges/bybit",
        )
    )
    result.append(
        (
            "official_instrument_docs",
            "CURRENT_DOC_SEMANTICS_ONLY",
            "https://bybit-exchange.github.io/docs/v5/market/instrument",
        )
    )
    result.append(
        (
            "tardis_instrument_doc",
            "THIRD_PARTY_DOC_SEMANTICS_ONLY",
            "https://docs.tardis.dev/api/instruments-metadata-api",
        )
    )
    for collection in (
        "CC-MAIN-2022-49",
        "CC-MAIN-2023-06",
        "CC-MAIN-2024-51",
        "CC-MAIN-2025-47",
    ):
        result.append(
            (
                "commoncrawl_api_" + collection,
                "ARCHIVE_INDEX",
                query(
                    "index.commoncrawl.org",
                    "/" + collection + "-index",
                    url="api.bybit.com/*",
                    output="json",
                    filter="status:200",
                    collapse="urlkey",
                    pageSize=100,
                ),
            )
        )
    # API archive queries are deliberately broad over category/symbol variants.
    # Duplicate symbol-labelled index responses are not independent evidence.
    return result


def fetch(item):
    label, source_class, url = item
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED:
        raise ValueError("Unapproved public metadata destination")
    if (
        parsed.hostname == "api.bybit.com"
        and parsed.path != "/v5/market/instruments-info"
    ):
        raise ValueError("Only public instrument metadata endpoint permitted")
    started = datetime.now(UTC).isoformat()
    request = Request(
        url,
        headers={
            "User-Agent": "CryptoBot-metadata-research/1.0",
            "Accept": "application/json,text/html",
        },
    )
    body, headers, status, error = b"", {}, None, None
    try:
        response = urlopen(request, timeout=20)
    except HTTPError as exc:
        response = exc
    except (URLError, OSError) as exc:
        error = type(exc).__name__
        response = None
    if response is not None:
        with response:
            status = response.status
            headers = {
                k: response.headers.get(k)
                for k in ("Date", "Content-Type", "Memento-Datetime")
                if response.headers.get(k)
            }
            body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                error = "RESPONSE_TOO_LARGE_INCOMPLETE"
    DEST.mkdir(parents=True, exist_ok=True)
    raw = DEST / (label + ".body")
    raw.write_bytes(body)
    receipt = {
        "id": label,
        "url": url,
        "source_class": source_class,
        "method": "GET_PUBLIC_UNAUTHENTICATED",
        "private_API": False,
        "request_started_at": started,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "headers": headers,
        "error_class": error,
        "body_path": str(raw.relative_to(ROOT)),
        "body_sha256": sha256(body).hexdigest(),
        "bytes": len(body),
        "result_is_historical_epoch_proof": False,
        "search_limits": "Bounded index result; miss/error is not absence/continuity proof; no automatic epoch promotion",
    }
    (DEST / (label + ".receipt.json")).write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    )
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true", required=True)
    args = parser.parse_args()
    if args.collect:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(fetch, searches()))
        (DEST / "SEARCH_RECEIPTS.json").write_text(
            json.dumps(results, sort_keys=True, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "searches": len(results),
                    "HTTP_200": sum(r["http_status"] == 200 for r in results),
                    "historical_epoch_promotion": False,
                }
            )
        )


if __name__ == "__main__":
    main()
