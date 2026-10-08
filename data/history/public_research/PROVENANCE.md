# Public external research data

The exact normalized CSV contents and stored gzip bytes are hashed in
`data/reports/robustness_research/*_dataset_manifest.json`. No missing candle is
interpolated. Only complete UTC-aligned lower-timeframe groups produce an HTF bar.
All timestamps refer to UTC; `end_exclusive` is the last candle's close.

Binance public mirror: https://github.com/Speirsy11/crypto-dataset at
`f1a95659f3cdd655b3ce7cbb1300e8fc944723bb`. Its publisher identifies Binance
public market data and dedicates the candle dataset to CC0 (license retained).
The endpoint and spot/linear-perpetual market type are not explicitly documented;
our instrument label remains `UNVERIFIED_BINANCE_MARKET_TYPE`. These data are
neither certified Bybit execution prices nor proof of perpetual-market edge.
The download manifest records every one of 628 real Parquet objects and matches
its byte count and SHA256 to the pinned public Git LFS pointer. A pointer itself
is never imported as candle data. `source_rows != 5` bars are excluded and audited.
All selected objects predate 2026. LINK, AVAX and LTC were unavailable in this
mirror; no alternative symbol was selected by results.

Bybit mirror: https://github.com/mestoness/btc-eth-candles-history at
`9ca04178df06ce649f00779a49e11094fe5b1c70`. Its README identifies Bybit USDT-M
perpetual candles. Original BTC/ETH 15m, 60m and 240m CSVs are preserved losslessly
under `bybit_mirror/source_raw/`. The normalized series use complete aggregates
of each real 15m CSV. The independent native-HTF comparison records 202 different
bars in `bybit_htf_independent_check.json`; original prices are not patched.
The mirror does not provide 5m data and does not include an explicit data license.

These public mirror histories have incomplete independent upstream verification.
They are labelled retrospective external research. The previously inspected 2026
Bybit corpus remains DEVELOPMENT and is excluded from external holdout dates.
Coverage-only common symbol periods were registered before performance runs.
Earlier single-symbol observations remain stored; the primary basket does not
trade before every fixed member exists. Disconnected coverage is evaluated as
independent portfolio segments, never spliced into an invented equity trajectory.

Reproduction: install `requirements-research.txt` for the optional Parquet importer;
use `scripts/fetch_public_research_dataset.py` and
`scripts/import_public_research_data.py`. The Strategy Engine remains stdlib-only.
Transient Git LFS download action URLs and their query tokens are not persisted.
