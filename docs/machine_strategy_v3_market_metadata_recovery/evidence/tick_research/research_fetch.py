"""Capture public metadata research responses with distinct retrieval timestamps."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def main() -> None:
    name, url = sys.argv[1:3]
    destination = urlparse(url)
    if destination.scheme != "https" or destination.hostname not in {
        "announcements.bybit.com",
        "announcements.bybit.global",
        "api.github.com",
        "api.tardis.dev",
        "arquivo.pt",
        "docs.tardis.dev",
        "index.commoncrawl.org",
        "lite.duckduckgo.com",
        "raw.githubusercontent.com",
        "search.brave.com",
        "web.archive.org",
        "www.amberdata.io",
    }:
        raise ValueError("Only recorded public metadata destinations permitted")
    root = Path(__file__).resolve().parent
    retrieved_at = datetime.now(UTC).isoformat()
    req = Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; metadata-research/1.0)"}
    )
    network_error = None
    try:
        with urlopen(req, timeout=35) as response:
            body = response.read()
            status = response.status
            final_url = response.url
            headers = dict(response.headers)
    except HTTPError as error:
        body = error.read()
        status = error.code
        final_url = error.url
        headers = dict(error.headers)
    except (URLError, TimeoutError) as error:
        body = b""
        status = None
        final_url = None
        headers = {}
        network_error = str(error)
    body_file = root / f"{name}.body"
    headers = {
        key: value
        for key, value in headers.items()
        if key.lower()
        in {
            "date",
            "content-type",
            "memento-datetime",
            "link",
            "content-length",
            "etag",
            "last-modified",
        }
    }
    body_file.write_bytes(body)
    receipt = {
        "requested_url": url,
        "final_url": final_url,
        "retrieved_at_utc": retrieved_at,
        "method": "GET_PUBLIC_UNAUTHENTICATED",
        "http_status": status,
        "response_headers": headers,
        "sensitive_or_unneeded_headers_retained": False,
        "body_file": body_file.name,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "network_error": network_error,
    }
    (root / f"{name}.receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(name, status, len(body), receipt["body_sha256"], network_error or "")


if __name__ == "__main__":
    main()
