"""Collect public Bybit announcement search results; never call trading APIs.

The endpoint and request schema come from the saved public announcement frontend.
All queries concern instrument parameters; no authentication or cookies are sent.
"""

from __future__ import annotations

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/original_v1_1_metadata_recovery_v2/provenance"
URL = "https://announcements.bybit.com/x-api/announcements/api/search/v2/index/announcement-posts_en"
QUERIES = [
    "tick size",
    "minimum order quantity",
    "trading parameters",
    "quantity step",
    "minimum order size",
    "order quantity perpetual",
]


def collect():
    receipt_path = DEST / "ANNOUNCEMENT_RECOVERY_RECEIPT.json"
    if receipt_path.exists() or (DEST.parent / "recovery_manifest.json").exists():
        raise ValueError("Existing evidence preserved; use audit --resume-existing")
    queries = []
    hits = {}
    for number, query in enumerate(QUERIES, 1):
        page = 0
        received = 0
        reported = None
        while reported is None or received < reported:
            base = f"announcement_query_{number}_page_{page}"
            request = DEST / (base + ".request.json")
            response = DEST / (base + ".response.json")
            request.write_text(
                json.dumps({"query": query, "page": page, "hitsPerPage": 50}) + "\n"
            )
            cached = response.exists()
            proc = (
                None
                if cached
                else subprocess.run(
                    [
                        "curl",
                        "--silent",
                        "--show-error",
                        "--connect-timeout",
                        "10",
                        "--max-time",
                        "20",
                        "--header",
                        "Content-Type: application/json",
                        "--data-binary",
                        "@" + str(request),
                        "--output",
                        str(response),
                        "--write-out",
                        "%{http_code}",
                        URL,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            )
            trace = {
                "query": query,
                "page": page,
                "url": URL,
                "method": "POST_PUBLIC_SEARCH_READ_ONLY",
                "exit_code": proc.returncode if proc else None,
                "http_code": proc.stdout if proc else None,
                "error": proc.stderr.strip() if proc else None,
                "transport": "NEW_HTTP" if proc else "PRESERVED_PREVIOUS_SUCCESS_JSON",
                "request_file": str(request.relative_to(ROOT)),
                "response_file": str(response.relative_to(ROOT)),
                "credentials_sent": False,
                "private_API": False,
            }
            queries.append(trace)
            if proc and (proc.returncode or proc.stdout != "200"):
                trace["complete"] = False
                break
            obj = json.loads(response.read_text())
            if obj.get("ret_code") != 0:
                trace["complete"] = False
                break
            result = obj["result"]
            rows = result["hits"]
            reported = result["nbHits"]
            trace.update(reported_total=reported, rows=len(rows), complete=True)
            for row in rows:
                hits[row["objectID"]] = {
                    k: row.get(k)
                    for k in (
                        "objectID",
                        "title",
                        "url",
                        "date_timestamp",
                        "publish_time",
                        "topics",
                    )
                }
            received += len(rows)
            if not rows or received >= reported:
                break
            page += 1
    # Read all derivative-related parameter notices within/preceding the target era.
    # This is retrieval triage, never SOURCE setup selection or validity inference.
    selected = [
        r
        for r in hits.values()
        if r["date_timestamp"] < 1764977401
        and (
            "Derivatives" in r["topics"]
            or "Perpetual" in r["title"]
            or "Unified Trading Account" in r["title"]
        )
    ]
    articles = []

    def fetch(row):
        stem = re.sub("[^a-zA-Z0-9_-]", "_", row["objectID"])
        path = DEST / ("announcement_article_" + stem + ".html")
        url = "https://announcements.bybit.com/en" + row["url"]
        proc = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--connect-timeout",
                "10",
                "--max-time",
                "20",
                "--output",
                str(path),
                "--write-out",
                "%{http_code}",
                url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        trace = {
            **row,
            "url_requested": url,
            "exit_code": proc.returncode,
            "http_code": proc.stdout,
            "error": proc.stderr.strip(),
            "file": str(path.relative_to(ROOT)),
            "file_sha256": sha256(path.read_bytes()).hexdigest()
            if path.exists()
            else None,
            "credentials_sent": False,
            "private_API": False,
        }
        if proc.returncode == 0 and proc.stdout == "200":
            text = path.read_text()
            match = re.search(
                r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL
            )
            if match:
                detail = json.loads(match[1])["props"]["pageProps"].get(
                    "articleDetail", {}
                )
                pieces = []

                def gather(value):
                    if isinstance(value, dict):
                        if isinstance(value.get("text"), str):
                            pieces.append(value["text"])
                        for key, child in value.items():
                            if key != "text":
                                gather(child)
                    elif isinstance(value, list):
                        for child in value:
                            gather(child)

                gather(detail.get("content", {}))
                body = "\n".join(pieces)
                body_path = path.with_suffix(".text.txt")
                body_path.write_text(body + "\n")
                trace.update(
                    article_title=detail.get("title"),
                    article_date=detail.get("date"),
                    text_file=str(body_path.relative_to(ROOT)),
                    text_sha256=sha256(body_path.read_bytes()).hexdigest(),
                    mentions_BTCUSDT=bool(
                        re.search(r"(?<![A-Z0-9])BTCUSDT(?![A-Z0-9])", body)
                    ),
                    mentions_ETHUSDT=bool(
                        re.search(r"(?<![A-Z0-9])ETHUSDT(?![A-Z0-9])", body)
                    ),
                )
                if trace["mentions_BTCUSDT"] or trace["mentions_ETHUSDT"]:
                    trace["body_for_parameter_review"] = body
        return trace

    with ThreadPoolExecutor(max_workers=4) as executor:
        articles = list(
            executor.map(
                fetch,
                sorted(selected, key=lambda r: (r["date_timestamp"], r["objectID"])),
            )
        )
    receipt = {
        "collection_date_UTC": datetime.now(UTC).isoformat(),
        "endpoint_source": "docs/original_v1_1_metadata_recovery_v2/provenance/official_announcement_index.js",
        "queries": queries,
        "unique_search_hits": len(hits),
        "retrieval_triage": "All search hits before requested end with Derivatives topic, Perpetual title, or Unified Trading Account title; no lower date bound.",
        "selected_historical_derivative_notices": len(selected),
        "articles": articles,
        "historical_interval_proof_automatically_inferred": False,
        "trade_entry_allowed": False,
        "limitations": "Search index may omit deleted/unindexed notices; absence of other changes cannot prove unchanged-period applicability.",
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    (DEST / "ANNOUNCEMENT_SEARCH_HIT_INDEX.json").write_text(
        json.dumps(
            sorted(hits.values(), key=lambda r: (r["date_timestamp"], r["objectID"])),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "unique_hits": len(hits),
                "selected_articles": len(selected),
                "target_symbol_mentions": [
                    {
                        k: r.get(k)
                        for k in (
                            "article_title",
                            "article_date",
                            "mentions_BTCUSDT",
                            "mentions_ETHUSDT",
                        )
                    }
                    for r in articles
                    if r.get("mentions_BTCUSDT") or r.get("mentions_ETHUSDT")
                ],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    collect()
