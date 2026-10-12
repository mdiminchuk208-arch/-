"""Append-only bounded public capture; no redirects, credentials or orders."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/machine_strategy_v3_prospective_readiness/evidence/public_captures"
HEADER_ALLOWLIST = {
    "content-type",
    "date",
    "content-length",
    "last-modified",
    "etag",
    "location",
}
LIMIT = 4 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.fragment
    ):
        raise ValueError("EXACT_PUBLIC_HTTPS_REQUIRED")
    if parsed.hostname == "api.bybit.com":
        params = parse_qs(parsed.query, strict_parsing=True, keep_blank_values=True)
        if params.get("category") != ["linear"] or params.get("symbol") not in (
            ["BTCUSDT"],
            ["ETHUSDT"],
        ):
            raise ValueError("EXACT_PUBLIC_INSTRUMENT_REQUIRED")
        if parsed.path == "/v5/market/instruments-info":
            allowed = {"category", "symbol"}
        elif parsed.path == "/v5/market/kline":
            allowed = {"category", "symbol", "interval", "start", "end", "limit"}
            if params.get("interval") != ["15"]:
                raise ValueError("NATIVE_M15_REQUIRED")
            for name in ("start", "end", "limit"):
                if len(params.get(name, [])) != 1 or not params[name][0].isdigit():
                    raise ValueError("BOUNDED_INTEGER_KLINE_REQUEST_REQUIRED")
            if not 0 < int(params["limit"][0]) <= 1000 or int(params["start"][0]) > int(
                params["end"][0]
            ):
                raise ValueError("INVALID_KLINE_BOUNDS")
        else:
            raise ValueError("PUBLIC_MARKET_ENDPOINT_REQUIRED")
        if set(params) != allowed or any(len(v) != 1 for v in params.values()):
            raise ValueError("UNEXPECTED_QUERY_PARAMETER")
    elif parsed.hostname == "announcements.bybit.com":
        if parsed.query or not (
            parsed.path == "/en/" or parsed.path.startswith("/en/article/")
        ):
            raise ValueError("OFFICIAL_NOTICE_PATH_REQUIRED")
    else:
        raise ValueError("OFFICIAL_HOST_REQUIRED")


def capture(url, dest=DEST):
    validate_url(url)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    ident = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex
    request = Request(
        url,
        headers={
            "User-Agent": "CryptoBot-IntegrityCapture/1",
            "Accept": "application/json,text/html",
        },
    )
    opener = build_opener(NoRedirect())
    error, status, headers, raw = None, None, {}, b""
    try:
        response = opener.open(request, timeout=20)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError) as exc:
        response, error = None, type(exc).__name__
    if response is not None:
        with response:
            status = response.code
            headers = {
                k.lower(): v
                for k, v in response.headers.items()
                if k.lower() in HEADER_ALLOWLIST
            }
            raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raw, error = raw[:LIMIT], "BOUNDED_RESPONSE_TRUNCATED_UNVERIFIABLE"
    finished = datetime.now(UTC).isoformat()
    body_path = dest / (ident + ".body")
    receipt_path = dest / (ident + ".receipt.json")
    with body_path.open("xb") as stream:
        stream.write(raw)
    receipt = {
        "id": ident,
        "requested_url": url,
        "request_started_at_utc": started,
        "retrieved_at_utc": finished,
        "http_status": status,
        "error_class": error,
        "headers": headers,
        "body_file": body_path.name,
        "body_sha256": sha256(raw).hexdigest(),
        "body_bytes": len(raw),
        "response_truncated": error == "BOUNDED_RESPONSE_TRUNCATED_UNVERIFIABLE",
        "private_api": False,
        "continuous_epoch_proof": False,
    }
    with receipt_path.open("x") as stream:
        stream.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, choices=("BTCUSDT", "ETHUSDT"))
    parser.add_argument(
        "--kind", choices=("instruments", "kline"), default="instruments"
    )
    parser.add_argument("--start-ms", type=int)
    parser.add_argument("--end-ms", type=int)
    args = parser.parse_args()
    params = {"category": "linear", "symbol": args.symbol}
    endpoint = "instruments-info"
    if args.kind == "kline":
        endpoint = "kline"
        params.update(
            interval="15", start=str(args.start_ms), end=str(args.end_ms), limit="1000"
        )
    receipt = capture(
        "https://api.bybit.com/v5/market/" + endpoint + "?" + urlencode(params)
    )
    print(
        json.dumps(
            {
                "id": receipt["id"],
                "http_status": receipt["http_status"],
                "body_sha256": receipt["body_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
