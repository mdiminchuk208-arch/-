# Next Task — EXCHANGE_SELECTION_AUDIT_v1 Freeze

The previous prospective-readiness gate is frozen at `fdf5b95e34c724ab73e8f3e64d36aed562ad965b` with `V3_PROSPECTIVE_READINESS_FROZEN_STOP`. The previously opened Bybit-only `Prospective Capture Activation + Control Plane v2` task was NOT executed and is superseded before implementation by this exchange-selection gate at the user's explicit direction.

Preserve every prior freeze. Do NOT change strategy rules, do NOT run historical v3 financial outcomes, do NOT generate OOS signals/trades, and do NOT enable PAPER/LIVE.

## Objective
Select the strongest venue architecture for Crypto Bot before starting a 365-day prospective evidence clock.

The audit must determine, using current official evidence and reproducible public endpoint probes, whether the project should:
1. keep Bybit as primary validation/execution venue;
2. switch to another venue;
3. use one venue for research/validation and a different venue for later execution;
4. retain multiple secondary/fallback venues.

The user explicitly authorizes considering exchanges outside the current Bitget/MEXC/BloFin/Bybit set.

The decision must prioritize **true bot execution cost**, **public data/metadata quality**, **API accessibility/reliability**, **liquidity/slippage**, and **validation integrity**. Do not rank by marketing claims or app-promotional fees.

## Candidate universe
Audit at minimum these venues when the required perpetual product/API exists:
- OKX
- Binance Futures
- Hyperliquid
- Gate
- Bitget
- Bybit
- KuCoin Futures
- BloFin
- MEXC
- Kraken derivatives/futures
- Coinbase International / perpetual venue if technically applicable
- Deribit if product fit is technically applicable

Additional credible venues may be included if discovered. If a venue lacks the required product or cannot satisfy the project's BTC/ETH perpetual workflow, mark `PRODUCT_MISMATCH` with exact evidence instead of forcing it into the ranking.

## Product baseline for apples-to-apples comparison
Primary symbols:
- BTC perpetual
- ETH perpetual

Preferred contract model:
- linear stablecoin-margined perpetual when available.

If a venue uses materially different settlement/margin conventions, document them and normalize costs carefully. Do not silently compare inverse, coin-margined, DEX and stablecoin-linear products as if identical.

## Frozen scoring model — define before collecting outcomes
Produce two independent rankings:

### A. Research / Validation Venue Score
Weights:
- public historical market-data depth + continuity: **25%**
- instrument/tick metadata provenance and change-history recoverability: **20%**
- public API accessibility/reliability/rate limits: **20%**
- funding/OI/trades/orderbook historical availability: **15%**
- reproducibility / timestamp semantics / documentation quality: **10%**
- execution-cost realism available for later simulation: **10%**

### B. Execution Venue Score
Weights:
- all-in execution cost: **35%**
- liquidity / spread / depth / modeled slippage: **25%**
- API reliability / order types / exchange-side SL-TP / reduce-only / isolated margin: **15%**
- funding and basis characteristics: **10%**
- operational/API permissions and safety fit: **10%**
- public-data/metadata quality: **5%**

Do not change weights after seeing which venue wins. If a criterion cannot be measured, mark it missing and apply the preregistered missing-data rule rather than subjectively redistributing weights.

## A. True fee audit
For every venue, collect current official fee evidence with retrieval time and immutable hash/receipt where technically possible.

Use the **ordinary API user / base tier** as the default comparison unless the venue has no such tier. Separately report VIP/token/referral/promotional reductions but do not use them in the primary ranking unless they are guaranteed and applicable to automated API trading.

Critically distinguish:
- web/app fee vs API-specific fee;
- maker vs taker;
- standard perpetual vs special/innovation/pre-listing product;
- exchange fee vs funding transfer;
- rebates/negative maker fees;
- fee-token discounts;
- region/account-specific schedules.

Required normalized scenarios for BTC and ETH:
1. taker entry + taker exit;
2. maker entry + taker exit;
3. maker entry + maker exit where technically realistic;
4. 50/50 maker-taker blended turnover.

Calculate round-trip fee in:
- percent of notional;
- basis points;
- USD at $1k, $5k, $10k, $25k and $50k notional.

Where API trading has a distinct schedule (for example MEXC), the API schedule controls the bot comparison.

## B. Funding audit
Funding is not automatically an exchange fee. Preserve sign/direction semantics.

For each venue, document:
- funding interval rules;
- current formula/limits if public;
- historical funding endpoint availability and depth;
- whether funding histories can be acquired reproducibly for BTC/ETH;
- any platform surcharge separate from trader-to-trader funding.

Do NOT select a venue based on one current funding print. This gate is architecture selection, not strategy P&L optimization.

## C. Public historical data audit
Probe official public APIs/documented archives without credentials where possible.

For BTC/ETH perpetuals determine:
- native M15 candle availability;
- maximum historical depth;
- pagination and row limits;
- missing-bar semantics;
- start/end timestamp semantics;
- completed-bar marker if any;
- trades history availability/depth;
- orderbook/public depth access;
- mark/index/premium series;
- funding history;
- OI history;
- instrument metadata including exact tick size/price filters;
- API changelog / announcements / metadata-change evidence;
- delisted/archived contract metadata where relevant.

Specifically assess whether the venue can support the project's required **2–3 year backtest evidence path** and future **365-day pristine OOS** without inventing tick epochs.

## D. Live public endpoint accessibility audit
Run bounded, non-trading probes from:
1. the current Codex/cloud research environment;
2. an ordinary GitHub-hosted CI runner if available through repository workflows.

No VPN, proxy, residential routing, geolocation spoofing, private API keys, cookies or account sessions.

For each public endpoint record:
- URL family (redact only secrets; there should be none);
- HTTP status;
- latency sample;
- rate-limit headers if exposed;
- response content hash;
- symbol/product identity;
- timestamp.

Repeated 403/451/geo blocking is a major reliability penalty for the research venue. Do not evade it.

## E. Liquidity, spread and slippage audit
Use contemporaneous public order-book snapshots only; no strategy signals.

For BTC and ETH perpetuals, sample multiple UTC times when technically practical and calculate exact executable VWAP/impact for both BUY and SELL at:
- $1,000
- $5,000
- $10,000
- $25,000
- $50,000

Report:
- best bid/ask spread in bps;
- depth within 1/2/5/10 bps where meaningful;
- modeled market-order slippage by notional and side;
- snapshot time/source;
- caveat that snapshots are not future execution guarantees.

Do not use a single unusually favorable snapshot as the venue score. Use deterministic aggregation (median, and worst observed sample where sample count permits).

## F. Bot execution capability audit
For each venue verify from current official docs/API schemas:
- REST + WebSocket availability;
- isolated margin;
- leverage controls;
- reduce-only;
- exchange-side stop-loss / take-profit or equivalent conditional orders;
- client order IDs / idempotency;
- order query / fills / position state;
- API key permission granularity (Read + Trade without Withdraw where applicable);
- IP allowlisting where applicable;
- rate limits;
- maintenance/status endpoints or operational status feed;
- testnet/demo availability where applicable.

Do not create private API keys or place orders in this gate.

## G. Venue-model compatibility
Hyperliquid and any non-CEX/orderbook venue must be assessed on its actual architecture, not forced into CEX assumptions.

Document differences in:
- custody / wallet signing model;
- API authentication;
- fee/rebate mechanics;
- liquidation/margin engine;
- data provenance;
- orderbook/fill semantics;
- operational dependencies.

A low fee alone does not win if implementation/security/data risks dominate.

## H. Hard exclusion / STOP criteria
A venue cannot be the primary Research/Validation venue if any of these remain unresolved:
- no reproducible BTC/ETH perpetual historical candles at required granularity/depth;
- no defensible current tick/price-filter metadata;
- public API persistently inaccessible from both approved research environments;
- ambiguous product identity preventing deterministic normalization;
- evidence cannot support causally known prospective metadata capture.

A venue cannot be the primary future Execution venue if any of these remain unresolved:
- bot trading API unavailable or materially incompatible;
- cannot enforce safe position/order controls required by the project;
- withdrawal permission cannot be separated from trade permissions where an API-key model is used;
- fees are not deterministically knowable for the account/API trading class;
- severe endpoint/access restrictions make reliable operation unreasonable.

## I. Decision format
Freeze the following outputs separately:

1. `PRIMARY_RESEARCH_VALIDATION_VENUE`
2. `PRIMARY_EXECUTION_VENUE`
3. `SECONDARY_EXECUTION_VENUE`
4. `REFERENCE_BENCHMARK_VENUE`
5. `REJECTED_OR_DEFERRED_VENUES` with exact reasons

It is valid for the first four roles to name different venues. Do not force one venue to win every category.

Before promotion, perform an independent red-team review asking whether the winner changes under reasonable non-tuned sensitivity tests, for example:
- fee-cost weight ±5 percentage points with proportional preregistered redistribution;
- removing one liquidity snapshot;
- treating unknown historical depth conservatively;
- excluding promotional fee discounts.

Sensitivity is for robustness of the architecture choice, not for cherry-picking a desired winner.

## Required specialist workflow
Required functions:
1. `cost_funding_auditor` — fee/funding normalization lead.
2. `historical_data_engineer` — historical/public data capability and real endpoint probes.
3. `market_microstructure_auditor` — spread/depth/slippage and venue execution semantics.
4. `execution_auditor` — order API, margin, SL/TP, permissions and safety requirements.
5. `tick_metadata_researcher` — tick/filter metadata and historical/prospective provenance.
6. `statistics_robustness_analyst` — frozen scoring implementation and sensitivity checks.
7. `overfit_red_team` — independent challenge to ranking/weights/evidence gaps.
8. `final_independent_reviewer` — final PASS/STOP seal.

Use other configured roles only if materially necessary. Record actual launched identities and role functions.

## Required namespace
Create immutable namespace:
`docs/exchange_selection_audit_v1/`

Required artifacts:
- `EXCHANGE_SELECTION_REPORT.md`
- `CANDIDATE_UNIVERSE.json`
- `OFFICIAL_FEE_EVIDENCE.json`
- `NORMALIZED_FEE_MATRIX.json`
- `FUNDING_CAPABILITY_MATRIX.json`
- `PUBLIC_DATA_CAPABILITY_MATRIX.json`
- `PUBLIC_ENDPOINT_PROBES.json`
- `LIQUIDITY_SPREAD_SLIPPAGE.json`
- `EXECUTION_CAPABILITY_MATRIX.json`
- `METADATA_PROVENANCE_MATRIX.json`
- `RESEARCH_VENUE_SCORES.json`
- `EXECUTION_VENUE_SCORES.json`
- `SENSITIVITY_ANALYSIS.json`
- `REJECTED_VENUES.json`
- `INDEPENDENT_REVIEW.md`
- `QA_REPORT.md`
- `freeze_manifest.json`

Retain official URLs, retrieval timestamps and content hashes/receipts. No secrets/private credentials.

## Mandatory QA
At minimum:
- deterministic fee normalization tests;
- bps/USD round-trip calculation tests;
- API-specific-vs-app-fee precedence tests;
- maker/taker sign/rebate handling;
- funding vs trading-fee separation;
- exact-decimal arithmetic;
- public endpoint identity checks;
- orderbook VWAP/slippage unit tests;
- scoring weights sum to 100% and remain frozen;
- missing-data penalty deterministic;
- ranking replay byte-identical;
- sensitivity analysis deterministic;
- source/hash verification;
- frozen v3 namespaces invariant;
- no strategy signal/outcome/P&L surfaces read;
- Ruff/format, mypy, compile for new code;
- final independent reviewer PASS required for venue promotion.

## Decision gate
Publish exactly one primary state:

### `EXCHANGE_SELECTION_AUDIT_FROZEN_PASS`
Only if evidence is sufficient to select a defensible primary research/validation architecture and future execution architecture.

### `EXCHANGE_SELECTION_AUDIT_FROZEN_STOP`
If no venue or venue combination meets minimum evidence/access/safety requirements. List exact unresolved blockers.

On PASS, update `agent_control/STATUS.md` and `CURRENT_STATE.md` with the selected venue roles and exact freeze/manifest hashes. The next gate should adapt **data/metadata capture infrastructure first**, without silently changing frozen v3 strategy rules. Any strategy port to a materially different market/product requires an explicit pre-outcome compatibility/version gate before financial evaluation.

Historical v3 financial backtest remains unauthorized in this audit.
Do NOT start the 365-day OOS clock on any venue before selection is frozen and its prospective capture protocol is independently registered.
Do NOT enable PAPER or LIVE.
`trade_entry_allowed=false` remains invariant.
