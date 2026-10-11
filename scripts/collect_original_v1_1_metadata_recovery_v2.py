"""Recover public metadata provenance only; preserves every existing collection."""

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "docs/original_v1_1_metadata_recovery_v2"
P = D / "provenance"
DOCS = Path("/tmp/bybit_metadata_recovery_docs")
SDK = Path("/tmp/bybit_metadata_recovery_pybit")


def run(args, cwd=R):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    return {
        "command": args,
        "cwd_role": "project" if cwd == R else cwd.name,
        "exit_code": r.returncode,
        "stdout": r.stdout,
        "stderr": r.stderr,
    }


def git(args, cwd):
    r = run(["git", *args], cwd)
    assert r["exit_code"] == 0, r
    return r["stdout"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, obj):
    (P / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def collect():
    if (D / "recovery_manifest.json").exists() or (
        P / "HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json"
    ).exists():
        raise ValueError("Existing evidence preserved; use audit --resume-existing")
    receipt = {
        "stage": "A",
        "collection_date_UTC": datetime.now(UTC).isoformat(),
        "sources": [],
        "network_attempts": [],
        "searches": [],
        "historical_periods_proved": 0,
        "trade_entry_allowed": False,
    }
    pattern = r"tickSize|qtyStep|minOrderQty|effective_from|effective_to|tick_size|quantity_precision"
    search = run(
        [
            "rg",
            "-l",
            "--hidden",
            "-g",
            "!.git/**",
            "-g",
            "!*.csv*",
            "-g",
            "!*.jsonl*",
            "-g",
            "!*.pdf",
            "-g",
            "!*.txt",
            "-g",
            "!*.log",
            pattern,
            "src",
            "scripts",
            "tests",
            "config",
            "docs",
            "data",
        ]
    )
    assert search["exit_code"] == 0
    paths = search.pop("stdout").splitlines()
    search["matched_files"] = [
        {"path": p, "sha256": sha((R / p).read_bytes())} for p in paths
    ]
    search["interpretation"] = (
        "File-name-only search; code/models/synthetic examples and v2 UNKNOWN registry. No authoritative effective-dated production instrument snapshot."
    )
    receipt["searches"].append(search)
    tracked = git(["ls-files"], R).splitlines()
    metadata_paths = [
        p
        for p in tracked
        if re.search(r"(instrument|metadata|snapshot|manifest)", p, re.IGNORECASE)
    ]
    save(
        "REPOSITORY_METADATA_PATH_INDEX.json",
        {
            "tracked_files": len(tracked),
            "metadata_name_candidates": metadata_paths,
            "scope": "Filenames only; no monetary history/labels read; matches are not instrument-period proof.",
        },
    )
    for args in [
        [
            "log",
            "--all",
            "--format=%H %cI %s",
            "--",
            "src/crypto_bot/data/bybit.py",
            "src/crypto_bot/data/models.py",
        ],
        ["log", "--all", "--format=%H %cI %s", "--", "*instrument*", "*metadata*"],
    ]:
        res = run(["git", *args])
        receipt["searches"].append(res)
    for role, cwd, remote in [
        ("official_docs", DOCS, "https://github.com/bybit-exchange/docs.git"),
        ("official_sdk", SDK, "https://github.com/bybit-exchange/pybit.git"),
    ]:
        head = git(["rev-parse", "HEAD"], cwd).strip()
        receipt["sources"].append(
            {
                "role": role,
                "url": remote,
                "pinned_commit": head,
                "commit_time": git(["show", "-s", "--format=%cI", head], cwd).strip(),
                "reachable_commit_count": int(
                    git(["rev-list", "--count", "--all"], cwd)
                ),
                "complete_clone_no_shallow": git(
                    ["rev-parse", "--is-shallow-repository"], cwd
                ).strip()
                == "false",
            }
        )
    logs = [
        (
            "OFFICIAL_INSTRUMENT_HISTORY.log",
            [
                "log",
                "--all",
                "--no-merges",
                "--format=%H %cI %s",
                "--",
                "docs/v5/market/instrument.mdx",
            ],
        ),
        (
            "OFFICIAL_FILTER_CHANGE_SEARCH.log",
            [
                "log",
                "--all",
                "-G",
                r"tickSize|qtyStep|minOrderQty|precision",
                "--format=%H %cI %s",
                "--",
                "docs/changelog/v5.mdx",
            ],
        ),
        (
            "OFFICIAL_FILTER_DIFFS.log",
            [
                "log",
                "--all",
                "--no-merges",
                "-p",
                "-G",
                r"tickSize|qtyStep|minOrderQty|priceScale",
                "--format=%H %cI %s",
                "--",
                "docs/v5/market/instrument.mdx",
            ],
        ),
    ]
    for name, args in logs:
        content = git(args, DOCS)
        (P / name).write_text(content)
        receipt["searches"].append(
            {
                "command": ["git", *args],
                "pinned_repository_head": receipt["sources"][0]["pinned_commit"],
                "output": str((P / name).relative_to(R)),
                "sha256": sha(content.encode()),
            }
        )
    changelog = git(["show", "HEAD:docs/changelog/v5.mdx"], DOCS)
    (P / "OFFICIAL_CHANGELOG_v5.mdx").write_text(changelog)
    sdklog = run(
        [
            "git",
            "log",
            "--all",
            "-G",
            r"tickSize|qtyStep|minOrderQty|effective_from|effective_to",
            "--format=%H %cI %s",
            "--",
            "tests",
            "pybit",
        ],
        SDK,
    )
    receipt["searches"].append(
        {
            **sdklog,
            "interpretation": "No instrument filter/effective-period fixture found in reachable SDK history; SDK not executed.",
        }
    )
    # Full immutable versions of public instrument documentation, not API production snapshots.
    versions = [
        ("pre_2023", "2023-01-01T00:00:00Z"),
        ("end_2023", "2024-01-01T00:00:00Z"),
        ("end_2024", "2025-01-01T00:00:00Z"),
        ("requested_end", "2025-12-05T23:30:01Z"),
        ("current", None),
    ]
    projected = []
    for label, cutoff in versions:
        commit = git(
            ["rev-list", "-1", *([f"--before={cutoff}"] if cutoff else []), "HEAD"],
            DOCS,
        ).strip()
        text = git(["show", commit + ":docs/v5/market/instrument.mdx"], DOCS)
        name = "OFFICIAL_INSTRUMENT_" + label + ".mdx"
        (P / name).write_text(text)
        row = {
            "version": label,
            "commit": commit,
            "commit_time": git(["show", "-s", "--format=%cI", commit], DOCS).strip(),
            "document_sha256": sha(text.encode()),
            "file": str((P / name).relative_to(R)),
            "snapshot_type": "DOCUMENTATION_EXAMPLE_NOT_PRODUCTION_API_ARCHIVE",
            "response_projection": [],
            "effective_from": None,
            "effective_to": None,
            "period_proof": False,
            "testnet_host_present": "Host: api-testnet.bybit.com" in text,
        }
        for block in re.findall(r"```json[^\n]*\n(.*?)\n```", text, re.DOTALL):
            # Documentation has // comments before examples; retain original file, project only JSON fields.
            clean = "\n".join(
                line
                for line in block.splitlines()
                if not line.lstrip().startswith("//")
            ).strip()
            while clean:
                try:
                    obj, end = json.JSONDecoder().raw_decode(clean)
                except json.JSONDecodeError:
                    break
                clean = clean[end:].strip()
                result = obj.get("result", {}) if isinstance(obj, dict) else {}
                for item in result.get("list", []) if isinstance(result, dict) else []:
                    if item.get("symbol") not in ("BTCUSDT", "ETHUSDT"):
                        continue
                    price = item.get("priceFilter", {})
                    lot = item.get("lotSizeFilter", {})
                    row["response_projection"].append(
                        {
                            "category": result.get("category"),
                            "symbol": item.get("symbol"),
                            "contract_type": item.get("contractType"),
                            "base_asset": item.get("baseCoin"),
                            "quote_asset": item.get("quoteCoin"),
                            "settle_asset": item.get("settleCoin"),
                            "priceScale": item.get("priceScale"),
                            "tickSize": price.get("tickSize"),
                            "qtyStep": lot.get("qtyStep"),
                            "minOrderQty": lot.get("minOrderQty"),
                            "example_server_time": obj.get("time"),
                            "sample_launchTime": item.get("launchTime"),
                            "admissible_as_historical_interval": False,
                        }
                    )
        projected.append(row)
    save("OFFICIAL_DOCUMENT_EXAMPLE_ASSESSMENT.json", projected)
    receipt["searches"].append(
        {
            "scope": "Full official instrument document history/filter diffs; current V5 changelog; five immutable full-document snapshots (before2023/end2023/end2024/requested-end/current).",
            "finding": "Dated source samples exist, but no full production effective interval proof. No gap-free historical filter change schedule for BTCUSDT/ETHUSDT identified. Documentation continuity is not filter continuity.",
        }
    )
    # Retry public GETs through the configured proxy. No credentials, endpoint aliases or policy bypass.
    urls = [
        (
            "BTCUSDT_current_api",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT",
        ),
        (
            "ETHUSDT_current_api",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=ETHUSDT",
        ),
        (
            "official_public_announcements",
            "https://api.bybit.com/v5/announcements/index?locale=en-US&type=new_crypto&limit=50",
        ),
        (
            "official_derivatives_change_2025",
            "https://announcements.bybit.com/article/adjustments-to-bybit-s-derivative-trading-limit-order-mechanism-blt469228de1902fff6/",
        ),
        (
            "public_archive_index",
            "https://web.archive.org/cdx/search/cdx?url=api.bybit.com%2Fv5%2Fmarket%2Finstruments-info%2A&output=json&filter=statuscode%3A200&collapse=timestamp%3A6",
        ),
    ]
    for label, url in urls:
        headers = P / (label + ".headers")
        body = P / (label + ".response")
        res = run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "10",
                "--max-time",
                "20",
                "--dump-header",
                str(headers),
                "--output",
                str(body),
                "--write-out",
                "%{http_code}",
                url,
            ]
        )
        header_sha = sha(headers.read_bytes()) if headers.exists() else None
        if headers.exists():
            headers.write_text(
                re.sub(
                    r"^set-cookie:.*$",
                    "set-cookie: [REDACTED_PUBLIC_RESPONSE_COOKIE]",
                    headers.read_text(),
                    flags=re.MULTILINE | re.IGNORECASE,
                )
            )
        receipt["network_attempts"].append(
            {
                "raw_header_sha256": header_sha,
                "label": label,
                "method": "GET",
                "url": url,
                "exit_code": res["exit_code"],
                "http_code": res["stdout"],
                "error": res["stderr"].strip(),
                "headers_file": str(headers.relative_to(R))
                if headers.exists()
                else None,
                "body_file": str(body.relative_to(R)) if body.exists() else None,
                "private_API": False,
                "credentials_sent": False,
                "proxy_policy_bypassed": False,
            }
        )
    missing = run(
        [
            "git",
            "ls-remote",
            "https://github.com/bybit-exchange/bybit-official-api-docs.git",
            "HEAD",
        ]
    )
    receipt["searches"].append(
        {
            **missing,
            "interpretation": "Guessed legacy official repository URL not found; no historical data obtained.",
        }
    )
    receipt["limits"] = (
        "Search is scoped to project repository/reachable official Git histories and attempted public references. Bybit API access returns upstream geographic 403 in this collection; public web archive is proxy-blocked; announcement frontend is separately assessed; no claim that metadata never existed elsewhere. Current API, documentation sample, sample server time and sample launchTime are insufficient effective-date proof."
    )
    save("HISTORICAL_METADATA_SEARCH_RECEIPT_v2.json", receipt)
    print(
        json.dumps(
            {
                "document_versions": len(projected),
                "docs_commits": receipt["sources"][0]["reachable_commit_count"],
                "instrument_history_commits": len(
                    (P / "OFFICIAL_INSTRUMENT_HISTORY.log").read_text().splitlines()
                ),
                "project_field_matches": len(paths),
                "network_attempts": [
                    (x["label"], x["exit_code"], x["http_code"])
                    for x in receipt["network_attempts"]
                ],
                "verified_periods": 0,
            }
        )
    )


if __name__ == "__main__":
    collect()
