# OKX frozen-v3 qualification — Stage A

Decision: **MACHINE_STRATEGY_V3_QUALIFICATION_STOP**, pre-outcome readiness only. V3 has not been financially evaluated, qualified or failed. No trade cases, strategy signals or financial performance were computed. This STOP is an evidence barrier, not a Win Rate verdict. Stage B remains unauthorized.

## Completed work

The preregistration was committed at `aa10ed0d65e97ab7f3b58a06ed8d3151f7f72371` before new financial outcomes. Its SHA-256 is `74d161d04dc5634859b1e6e1b8fa07d60281c86fde7b4a02d0bced15f3c93988`. It binds exact OKX BTC-USDT-SWAP and ETH-USDT-SWAP, development `[2024-10-13T00:00Z, 2026-10-13T00:00Z)`, and 365-day warmup starting 2023-10-14. The two complete UTC development years were chosen by calendar, not observed performance. All acquired historical prices are development-exposed and never pristine OOS.

| Input | BTC | ETH | Verification |
| --- | ---: | ---: | --- |
| Native M15, including warmup | 105,120 | 105,120 | Official public history endpoint, confirm=1, 900-second UTC grid, no gap/duplicate/interpolation |
| Derived H1 | 26,280 | 26,280 | Complete contiguous groups only |
| Derived H4 | 6,570 | 6,570 | Complete contiguous groups only |
| Derived D1 | 1,095 | 1,095 | Complete UTC days only |
| Development funding settlements | 2,190 | 2,190 | Signed actual rates, exact contract/timestamp match to retained raw sources |

The acquisition script is public-only and imports no strategy/outcome code. 702 native-candle pages preserve URLs, UTC request/response clocks, hashes, lengths and filtered headers. Native outputs use deterministic gzip (empty filename, mtime=0) and exact decimals. Replaying retained pages reproduces both normalized content hashes. The new input bridge supplies honest OKX product/source labels instead of the inherited Bar description that says Bybit; it derives only data, never discovers setups or drives orders.

Funding recovery solved the previously documented three-month API limit: the official historical-data page offers a public archive from March 2022. Forty-eight monthly ZIPs cover October 2024–September 2026, and the recent public API supplies the partial October 2026 tail. Sixty overlapping realized-rate rows per contract match exactly. Every scoped normalized row is independently matched back to its archive CSV or public API `realizedRate`. Rows at/after 2026-10-13T00:00Z are excluded from the bound development input. The observed eight-hour grid is verified for this series, not backdated from a current funding interval or assumed for the future. The archive-link POST is an explicitly public, unauthenticated metadata operation, not a private account/order endpoint. No credentials, cookies or exchange account session were used.

## Preregistered qualification rules

WR >=70% remains the user's non-negotiable requirement for historical, later OOS/forward, and Paper samples. The historical preregistration additionally requires >=200 CLOSED trades, positive net expectancy and net cash-risk-unit result after costs/funding, PF >=1.20, closed-case-ledger drawdown <=20R, max consecutive net losses <=10, Wilson 95% WR lower bound >=60%, no unresolved filled exits, adequate coin/direction samples and positive coin/direction results, fixed concentration limits, doubled fee/slippage stress survival, and no critical causal/integrity defects. Definitions and exact thresholds are in STAGE_A_PREREGISTRATION.json. These are project policy selected before outcomes, not SOURCE_RULE or fitted parameters. The case-risk ledger is not a leveraged portfolio-equity simulation. Thresholds may not be relaxed after observing results; failure evidence must be frozen before a new version.

## Evidence blockers

1. **Historical tick/lot/filter epochs are not verified for the declared period.** Current `tickSz`, `lotSz`, `ctVal`, `minSz` are current observations only. The two bounded official announcement API probes returned HTTP403/Cloudflare1010; no routing/browser evasion or broad repeated retries were used. Candle decimal precision, price GCD, snapshot interpolation, or an arbitrary coarse grid cannot establish effective historical filters. The independent tick resolver explains why a coarse grid is not a guaranteed adverse bound: it can alter fillability, nearest-target collisions and the admitted trade universe. No fake `verified=true` epoch or retroactive current metadata is injected into the frozen contracts. A hypothetical alternative grid model would be a separate version and would still not prove exact frozen-v3 execution or exchange realism.
2. **Ordinary account-applicable API SWAP fees remain unknown.** The old 2/5 bps FAQ is an example, and targeted public frontend fee configuration returns Spot tables. The private account fee endpoint was not called. Frozen v3's 6 bps fee plus 2 bps slippage per leg is a modeled convention, not historical OKX fee evidence or a proven account-specific upper bound. Doubling a hypothetical model does not manufacture that missing proof.
3. **The frozen financial runner remains Bybit-bound and excludes funding.** The new nonfinancial bridge resolves acquisition/source labeling, not financial authorization. A separate reviewed OKX outcome wrapper, lot/size treatment, funding position-at-settlement/mark-value conventions and cost ledger would be needed after the evidence barriers are solved. This is deferred technical implementation, not the hard external source barrier itself. Frozen core geometry, costs, metadata guard, originals and v2.x are not patched.

Completed-bar release at bar close in the bridge is explicitly a historical model assumption; actual historical API publication latency is not proven. No unfinished/future bar is released to a decision prefix. The root verifies protected v3 hashes and the inherited exchange freeze; predecessor financial artifacts are hash-checked only, not parsed. No strategy outcome is inferred from raw prices.

## Next action and resume boundary

Keep this completed acquisition and funding series; do not recollect them. Resume this frozen namespace only with its externally supplied manifest hash. To reopen fair Stage A, obtain defensible dated historical tick/lot/filter coverage and ordinary API fee evidence, or establish a genuinely conservative separately versioned compatibility policy that independent execution review accepts without financial tuning. New evidence/corrections must go into a new readiness-repair namespace, never mutate this freeze. If source accessibility changes, retry only the affected bounded public evidence path; do not evade its restriction. Account/legal or credentials choices inherently require the user and are not inferred from public documentation.

The autonomous campaign remains the governing objective. It cannot skip the evidence barrier by redesigning strategy rules, run a favorable hypothetical result as qualification, start OOS early, or fast-forward Paper calendar requirements. No platform work, private trading API, OOS clock, PAPER or LIVE. `trade_entry_allowed=false`.

Actual specialist identities in this Stage A: `okx_stage_a_cost_funding` (cost/funding audit and official archive recovery) and `okx_stage_a_tick_audit` (independent historical-filter/compatibility analysis), run sequentially. The final independent Stage-A reviewer is recorded separately in INDEPENDENT_REVIEW.md. Root is the sole implementation writer. No strategy_designer or parameter-search worker was launched.
