"""Rebuild source and search inventories from retained public response receipts."""

import hashlib
import json
import re
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt(name: str) -> dict:
    data = json.loads((ROOT / f"{name}.receipt.json").read_text())
    body = (ROOT / data["body_file"]).read_bytes()
    assert sha256(body) == data["body_sha256"], name
    assert len(body) == data["body_bytes"], name
    return data


def candidate(name: str, **details: object) -> dict:
    data = receipt(name)
    return {
        "id": name,
        "original_or_requested_url": data["requested_url"],
        "final_url": data.get("final_url"),
        "raw_body_path": data["body_file"],
        "raw_sha256": data["body_sha256"],
        "raw_bytes": data["body_bytes"],
        "receipt_path": f"{name}.receipt.json",
        "retrieved_at_utc": data["retrieved_at_utc"],
        "http_status": data["http_status"],
        **details,
        "verification_status": "UNVERIFIED_FOR_EXECUTABLE_EPOCH",
    }


def article_text_hash(name: str) -> str:
    doc = html.fromstring((ROOT / f"{name}.body").read_bytes())
    next_data = json.loads(doc.xpath('string(//script[@id="__NEXT_DATA__"])'))
    article = next_data["props"]["pageProps"]["articleDetail"]["content"]["json"]
    tokens = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                tokens.append(node["text"])
            for key, value in node.items():
                if key != "text":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(article)
    normalized = re.sub(r"\s+", " ", " ".join(tokens)).strip()
    return sha256(normalized.encode())


def market_fields_hash(name: str, symbols: list[str]) -> str:
    markets = json.loads((ROOT / f"{name}.body").read_text())
    fields = {}
    for symbol in symbols:
        market = markets[symbol.replace("USDT", "/USDT:USDT")]
        info = market["info"]
        assert info["symbol"] == symbol
        assert info["contractType"] == "LinearPerpetual"
        assert info["settleCoin"] == "USDT"
        fields[symbol] = {
            "symbol": info["symbol"],
            "contractType": info["contractType"],
            "settleCoin": info["settleCoin"],
            "tickSize": info["priceFilter"]["tickSize"],
        }
    return sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode())


def main() -> None:
    search = []
    for path in sorted(ROOT.glob("*.receipt.json")):
        name = path.name.removesuffix(".receipt.json")
        data = receipt(name)
        search.append(
            {
                "id": name,
                "requested_url": data["requested_url"],
                "http_status": data["http_status"],
                "retrieved_at_utc": data["retrieved_at_utc"],
                "body_path": data["body_file"],
                "body_sha256": data["body_sha256"],
                "body_bytes": data["body_bytes"],
                "receipt_path": path.name,
                "network_error": data.get("network_error"),
            }
        )
    (ROOT / "SEARCH_INVENTORY.json").write_text(json.dumps(search, indent=2) + "\n")

    contract = "Bybit USDT-settled linear perpetual; BTCUSDT or ETHUSDT as stated"
    shared_notice_limits = [
        "The page's Open Graph publication timestamp is an issuer assertion, not an independent capture at that time.",
        "The stated effective time is a plan/claim, not independently verified application.",
        "No source establishes uninterrupted tick-size continuity before and after the event or through 2025-12-05T23:30Z.",
    ]
    sources = [
        candidate(
            "archived_eth_20230205",
            symbols=["ETHUSDT"],
            contract_identity=contract,
            source_class="official_notice_independent_archive",
            original_url="https://announcements.bybit.com/article/changes-to-tick-size-for-ethusdt-perpetual-contract-2023-01-06--bltb4b6d3ffa3c5206c/",
            archive_identifier="Arquivo.pt Memento 20230205041038id_",
            title_date="2023-01-06",
            advertised_publication_at_utc="2023-01-06T07:03:06Z",
            advertised_publication_basis="archived Open Graph article:published_time",
            independently_proven_publication_at_utc=None,
            advertised_effective_at_utc="2023-01-17T08:00:00Z",
            archive_capture_at_utc="2023-02-05T04:10:38Z",
            exchange_capture_at_utc=None,
            before_tick={"ETHUSDT": "0.05"},
            after_tick={"ETHUSDT": "0.01"},
            normalized_relevant_text_sha256=article_text_hash("archived_eth_20230205"),
            prior_frozen_literal_text_sha256="7c7499498f767e5c58178a017987518979e588d9f98c7c4a398d21842ca74bcf",
            proves=[
                "The exact ETHUSDT change claim existed in official page bytes by the independent 2023-02-05 archive capture."
            ],
            does_not_prove=shared_notice_limits
            + ["Archive capture followed the claimed effective time."],
        ),
        candidate(
            "official_eth_en",
            symbols=["ETHUSDT"],
            contract_identity=contract,
            source_class="official_notice_current_retrieval",
            original_url="https://announcements.bybit.com/en/article/changes-to-tick-size-for-ethusdt-eth-perp-perpetual-contracts-2023-01-06--bltb4b6d3ffa3c5206c/",
            archive_identifier=None,
            title_date="2023-01-06",
            advertised_publication_at_utc="2023-01-06T07:03:06Z",
            advertised_publication_basis="current Open Graph article:published_time",
            independently_proven_publication_at_utc=None,
            advertised_effective_at_utc="2023-01-17T08:00:00Z",
            archive_capture_at_utc=None,
            exchange_capture_at_utc=None,
            before_tick={"ETHUSDT": "0.05"},
            after_tick={"ETHUSDT": "0.01"},
            normalized_relevant_text_sha256=article_text_hash("official_eth_en"),
            proves=[
                "The currently served official page explicitly names ETHUSDT and a planned tick change."
            ],
            does_not_prove=shared_notice_limits,
        ),
        candidate(
            "official_20230207",
            symbols=["BTCUSDT"],
            contract_identity=contract,
            source_class="official_notice_current_retrieval",
            original_url="https://announcements.bybit.com/en/article/changes-to-tick-size-for-usdt-perpetual-contract-2023-02-07--blt80c14139bdd327bc/",
            archive_identifier=None,
            title_date="2023-02-08",
            advertised_publication_at_utc="2023-02-07T11:02:47Z",
            advertised_publication_basis="current Open Graph article:published_time; title is dated 2023-02-08",
            independently_proven_publication_at_utc=None,
            advertised_effective_at_utc="2023-02-10T08:00:00Z",
            archive_capture_at_utc=None,
            exchange_capture_at_utc=None,
            before_tick={"BTCUSDT": "0.5"},
            after_tick={"BTCUSDT": "0.1"},
            normalized_relevant_text_sha256=article_text_hash("official_20230207"),
            proves=[
                "The currently served official page explicitly names BTCUSDT USDT Perpetual and a planned tick change."
            ],
            does_not_prove=shared_notice_limits
            + ["No contemporary independently archived BTC notice was retained."],
        ),
    ]

    commit_times = {
        "ccxt_bybit_460503bd48fa": (
            "460503bd48fa3dd8338348d8146fd4ae80d4acb7",
            "2023-10-28T11:44:02Z",
            {"BTCUSDT": "0.10"},
        ),
        "ccxt_bybit_fbec4993ce01": (
            "fbec4993ce0171b08691611281b9410397059333",
            "2023-10-31T16:59:26Z",
            {"BTCUSDT": "0.10", "ETHUSDT": "0.01"},
        ),
        "ccxt_bybit_bfa6cfbaaa59": (
            "bfa6cfbaaa598a80a9834c43862a430a8433c509",
            "2024-03-26T14:37:54Z",
            {"BTCUSDT": "0.10", "ETHUSDT": "0.01"},
        ),
        "ccxt_bybit_3c7fb16f4fa9": (
            "3c7fb16f4fa9c29f3272d0f530dc98dfdafbb393",
            "2025-05-19T09:26:28Z",
            {"BTCUSDT": "0.10", "ETHUSDT": "0.01"},
        ),
    }
    for name, (sha, commit_time, ticks) in commit_times.items():
        sources.append(
            candidate(
                name,
                symbols=list(ticks),
                contract_identity=contract,
                source_class="third_party_repository_market_fixture_immutable_commit",
                original_url=f"https://raw.githubusercontent.com/ccxt/ccxt/{sha}/ts/src/test/static/markets/bybit.json",
                archive_identifier=f"Git commit {sha}",
                title_date=None,
                advertised_publication_at_utc=None,
                independently_proven_publication_at_utc=None,
                git_author_at_utc=commit_time,
                git_committer_at_utc=commit_time,
                exchange_capture_at_utc=None,
                archive_capture_at_utc=None,
                advertised_effective_at_utc=None,
                before_tick=None,
                after_tick=None,
                observed_price_filter_tick=ticks,
                observed_fields="info.symbol, info.contractType=LinearPerpetual, info.settleCoin=USDT, info.priceFilter.tickSize",
                normalized_relevant_text_sha256=market_fields_hash(name, list(ticks)),
                proves=[
                    "A third-party repository contains an exact-symbol Bybit-style instrument fixture with explicit priceFilter.tickSize at this immutable commit."
                ],
                does_not_prove=[
                    "The exchange response collection time is absent; Git author/committer time is not exchange capture or rule-effective time.",
                    "A test fixture may be copied forward without refreshing instrument data; later commits do not prove contemporaneous exchange state.",
                    "No fixture proves continuous intervening settings or the 2022 baseline.",
                ],
            )
        )

    sources.append(
        candidate(
            "tardis_metadata_api_markdown",
            symbols=["BTCUSDT", "ETHUSDT"],
            contract_identity=contract,
            source_class="third_party_instrument_metadata_service_documentation",
            original_url="https://docs.tardis.dev/api/instruments-metadata-api.md",
            archive_identifier=None,
            title_date=None,
            advertised_publication_at_utc=None,
            independently_proven_publication_at_utc=None,
            advertised_effective_at_utc=None,
            archive_capture_at_utc=None,
            exchange_capture_at_utc=None,
            before_tick=None,
            after_tick=None,
            normalized_relevant_text_sha256=sha256(
                "\n".join(
                    line.strip()
                    for line in (ROOT / "tardis_metadata_api_markdown.body")
                    .read_text()
                    .splitlines()
                    if line.startswith(
                        ("`changes` is complete", "* Only `contractMultiplier` changes")
                    )
                ).encode()
            ),
            proves=[
                "Tardis schema explicitly includes priceIncrement and historical changes[].priceIncrement fields.",
                "Documentation explicitly states only contractMultiplier changes are guaranteed complete; priceIncrement changes are best-effort.",
            ],
            does_not_prove=[
                "No BTCUSDT or ETHUSDT values were retrieved.",
                "Even authorized API data would not establish complete priceIncrement change history solely from this service.",
            ],
            access_result={
                "BTCUSDT": "tardis_api_btc.receipt.json: HTTP 401",
                "ETHUSDT": "tardis_api_eth.receipt.json: HTTP 401",
            },
        )
    )
    (ROOT / "SOURCE_CANDIDATES.json").write_text(json.dumps(sources, indent=2) + "\n")
    print(len(search), "responses and", len(sources), "source candidates verified")


if __name__ == "__main__":
    main()
