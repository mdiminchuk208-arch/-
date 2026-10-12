# Historical data engineer — metadata recovery review

Scope: read-only review of frozen v3 readiness metadata and the two pinned M15 source CSVs. I did not read financial case files or strategy outcomes, run the historical runner, or change source prices. This review supplies data-period and consistency evidence only; it cannot declare a historical tick epoch VERIFIED.

## Exact pinned inputs and intervals

The frozen primary sources are `data/history/public_research/bybit_mirror/BTCUSDT/15.csv.gz` (SHA-256 `5d3fe4a4eb1d147c5f5516944bdbc45a21fb483d0bc667b5a92ed206aa8a6fc9`) and `data/history/public_research/bybit_mirror/ETHUSDT/15.csv.gz` (SHA-256 `94c8f3f414ae3bbbe08bc5180f3da88d72c699f8ff88fd8093062078260449f8`). I recomputed both compressed-file hashes. In the selected interval every row says `exchange=BYBIT`, exact symbol, `interval=15`, and `is_closed=1`; there were zero row-identity violations. These labels and the frozen source provenance call the instrument a Bybit USDT linear perpetual, but they are not an independent exchange-captured instrument-filter record. The raw compressed files also contain earlier rows; the frozen primary representation uses only the declared 2022–2025 interval.

For each symbol the exact M15 selected series has 137,758 rows, first open `2022-01-01T00:00:00Z`, last open `2025-12-05T23:15:00Z`, and availability end **exclusive** `2025-12-05T23:30:00Z`. Consecutive opens differ by exactly 900 seconds: zero missing/duplicate grid positions. Warmup `[2022-01-01T00:00:00Z, 2023-01-01T00:00:00Z)` is 35,040 bars / 31,536,000 seconds. Development `[2023-01-01T00:00:00Z, 2025-12-05T23:30:00Z)` is 102,718 bars / 92,446,200 seconds. The frozen derived H1/H4/D1 groups exclude incomplete terminal groups; there is no synthetic final bar or interpolation. These claims match `DATA_CONTINUITY_REPORT.json` and `DATA_GRID_AUTHENTICITY.json`; the row/grid/hash checks above were independently repeated here.

The pinned M15 files are `BYBIT:PUBLIC_MIRROR:{symbol}:15` in the frozen alias inventory. Their `source_raw/bybit_btc_15.gz` and `source_raw/bybit_eth_15.gz` files are raw-source aliases of those same underlying series, not independent exchange observations. `data/history/bybit/{symbol}/15.csv` is a separate `BYBIT:NATIVE_2026:{symbol}:15` exposed development series and is not a fallback for the pinned primary. Public-mirror H1/H4 and native H1/H4/5 are different timeframes/representations and cannot supply missing instrument metadata. Binance mirrors are another exchange. None of these OHLC aliases can establish a historical executable price filter.

## Notice-candidate grid check, non-authoritative

I divided each *raw string* open/high/low/close by a `Decimal` tick and required an integral quotient. Candidate ticks came only from the frozen notice claims. The pre-notice tick applied to 2022 warmup is a **hypothetical consistency test**, not a claim of an epoch. A cell is counted once for each off-grid OHLC field; bars are counted once if any field fails.

| Symbol / candidate interval | Candidate tick | Bars checked | Off-grid bars | Off-grid OHLC cells |
| --- | ---: | ---: | ---: | ---: |
| BTC warmup 2022 | 0.5 | 35,040 | 0 | 0 |
| BTC development before `2023-02-10T08:00:00Z` | 0.5 | 3,872 | 1 | 1 |
| BTC development from `2023-02-10T08:00:00Z` to exclusive end | 0.1 | 98,846 | 0 | 0 |
| ETH warmup 2022 | 0.05 | 35,040 | 0 | 0 |
| ETH development before `2023-01-17T08:00:00Z` | 0.05 | 1,568 | 4 | 6 |
| ETH development from `2023-01-17T08:00:00Z` to exclusive end | 0.01 | 101,150 | 0 | 0 |

Exact contradictory cells under those candidate boundaries:

| Symbol | M15 open UTC | Fields off candidate pre-change grid |
| --- | --- | --- |
| BTCUSDT | `2023-02-10T07:45:00Z` | high `21931.3` off `0.5` |
| ETHUSDT | `2023-01-17T07:00:00Z` | high `1563.39`, close `1563.36` off `0.05` |
| ETHUSDT | `2023-01-17T07:15:00Z` | open `1563.36` off `0.05` |
| ETHUSDT | `2023-01-17T07:30:00Z` | low `1557.76`, close `1559.76` off `0.05` |
| ETHUSDT | `2023-01-17T07:45:00Z` | open `1559.76` off `0.05` |

The notices describe ETH `0.05` to `0.01` at a claimed `2023-01-17T08:00:00Z` and BTC `0.5` to `0.1` at a claimed `2023-02-10T08:00:00Z`. Off-grid rows just before those times are a source/notice chronology and authenticity question. They cannot be resolved by moving effective times to the first finer candle, silently rounding OHLC, or declaring the observed grid to be an exchange rule. Likewise, post-claim alignment does not prove implementation or unchanged continuity. Status: **UNVERIFIED_NOTICE_CLAIM; consistency check only**.

The same five rows have identical numeric OHLC values in the `source_raw` aliases (`bybit_btc_15.gz`, SHA-256 `5192544084f775ace822f3dd8bce974d87ddeae17fd978ccab52872017189168`; `bybit_eth_15.gz`, SHA-256 `54ffe8ee9d2d51e4536d4104e9d569a544759527d4b4c25ca164a41458886c69`). This local comparison rules out a change introduced by the pinned CSV representation for these rows; the alias shares the same underlying public mirror and is not independent exchange corroboration.

## Metadata availability and recovery paths

The frozen v3 `TICK_EPOCHS.json` has zero VERIFIED epochs for either symbol. Its exact unresolved intervals are `[2022-01-01T00:00:00Z, 2025-12-05T23:30:00Z)` for both. Verified warmup coverage and verified development coverage are separately **0%** for each symbol. There is no fully verified shorter interval established by candle alignment. The local `original_v1_1_metadata_recovery_v2` and `original_v1_1_execution_metadata_v3` registries also report UNKNOWN historical price-filter intervals, though their older endpoint convention used an inclusive `23:30` label; the v3 exclusive availability end controls this gate.

A repository filename inventory identified retained Bybit notice bodies and official documentation revisions under `docs/original_v1_1_metadata_recovery_v2/provenance/` and the v3 readiness `evidence/` directory. `OFFICIAL_DOCUMENT_EXAMPLE_ASSESSMENT.json` describes Git commit-dated `docs/v5/market/instrument.mdx` example responses before 2023, end 2023, end 2024 and requested end. They are **documentation examples, not archived production `instruments-info` responses or effective-period proof**. `PARTIAL_METADATA_SOURCE_ASSESSMENT.json` likewise classifies the ETH/BTC notices as announced changes only. I found no filename indicating an authoritative historical production instrument snapshot; this is a filename inventory finding, not proof that no snapshot exists.

Useful targeted recovery locations are the official Bybit announcements and their preserved v3 receipts; the official `bybit-exchange/docs` Git history of `docs/v5/market/instrument.mdx` for chronology/context only; the Internet Archive CDX index for archived `api.bybit.com/v5/market/instruments-info?category=linear&symbol=...` response bytes; Arquivo.pt CDX/mementos around both notice dates and parameter endpoints; and Common Crawl's public index/WARC records for official pages or API URLs if indexed. Search both exact symbol and `category=linear`/`LinearPerpetual` (not spot or inverse); archive capture, publication, effective, and retrieval times must remain separate. The retained ETH Arquivo memento has a 2023-02-05 capture after its claimed effective time, and the existing BTC Arquivo CDX receipt has an empty body. Neither establishes pre-effective known-at or complete continuity. Third-party market-data archives should be considered only if a dataset actually contains byte-preserved instrument `priceFilter.tickSize`, explicit exact-contract identity, capture timestamps, hashes, and a defensible continuity chain; trade/kline archives alone do not qualify. These paths are search leads, not recovered epoch evidence.

**Recommendation:** keep both full intervals UNVERIFIED and preserve `V3_FINANCIAL_STOP`. Resolve the pre-change off-grid cells against an independently dated Bybit price-filter record and source-candle provenance before any candidate epoch is promoted. No historical financial run or source-price modification is supported by this review.
