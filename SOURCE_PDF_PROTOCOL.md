# Primary PDF reconstruction and preregistered replay

Registered before new full-history detector output or trade outcomes. Parent:
`74a6f8de22511653943a78399fb52638a1dc9215`. All previous code, tests and artifacts
are retained. Canonical 40/30/30, original SL and cost-adjusted BE after TP1 are
unchanged. This additive source experiment has its own execution contract.
BACKTEST/SHADOW only, trade_entry_allowed=false, no network/private API.

## Primary sources, fully read

Original PDFs, full page-separated text and SHA256 are in
`data/source_materials/primary_pdf_2026_10_09`. Actual page counts: SW5=9,
SW9=16, SW11=8, SW12=15, SW22=6 (54 total). All pages rendered and visually
reviewed, including diagrams. `file`'s initial page estimate was incorrect for
SW5/SW9/SW12; pdfinfo, text form feeds and rendered pages agree.
Links in the course documents are references, not instructions to execute code.

| SOURCE_RULE and citation | Deterministic realization / change from 74a6f8d |
|---|---|
| SW5 p2: three candles, central wick strictly beyond both neighbours | Existing causal SOURCE_CONSERVATIVE native-TF swings; right candle must close. |
| SW5 p3–5: key HH/HL or LL/LH; BOS body close through protected point | Existing key structural detector retained; minor swing sequence must not substitute for key structure. |
| SW5 p6–7: conservative entry after CONF updating the new structure | Retain LTF raid → BOS → distinct new structure → later CONF. This is a selected conservative branch, not every permitted entry. |
| SW9 p2–3: OB candle takes liquidity, aggressive engulfing follows; whole wick zone, within HTF POI and structural impulse | Direct next-candle body engulf plus close beyond original full wick; origin candle itself raids. Local OB origin must overlap active HTF POI. IMB confluence recorded, not a universal gate: p2 calls it the most accurate signal. Body/wick numerical dominance is not imposed by this primary PDF. |
| SW9 p3: first test normally; repeat entry possible after LTF reaction | Each separate OB visit creates a new reaction context. Any repeat must establish a new raid/BOS/structure/CONF after that visit; consecutive overlapping bars do not count as visits. Old pending context cancels on a new visit. D/S remains first-test-only per retained DOC18. |
| SW9 p3: OB edge or inside limit, SL beyond OB or engulfing wick | Select proximal full-wick OB edge, SL immediately outside its distal wick. No post-outcome variant selection. |
| SW9 p7–10: breaker impulsively pierces OB without trading in it; conservative SL beyond liquidity-taking impulse | Retain gap-backed continuous piercing and structural proof; require the gap's middle candle actually pierces the OB body boundary, not an unrelated nearby gap. Proximal edge quote; conservative extreme outside breaking/sweep wick. |
| SW9 p4–6: HTF 15m–1D POI, LTF 1–15m reaction, new POI limit | Primary five mappings 15/5,60/5,60/15,240/5,240/15. 240/60 remains separate ANY_TF interpretation. |
| SW9 p11–16: FTA is first opposing POI; conclusion specifies higher TF | First fresh opposing **HTF** POI, never an incidental LTF FVG; full FTA exit selected. p11 allows partial/full exits; no literal fixed 5R/three TP requirement. |
| SW22 p1–4: STB/BTS takes liquidity and entire manipulation is absorbed; BOS or CONF, trend alignment; edge or .5 entry | Entire move from the last causally confirmed opposing swing to the sweep extreme, including all intervening candles; full body-close absorption beyond that move. Freeze boundaries at formation. Select .5 quote, original technical SL outside whole manipulation. Single-candle sweep-only proxy superseded. |
| SW22 p5 diagram: actual liquidity work plus key confirmations, not merely a zigzag trend | Key structure pairs from confirmed structural events, not the last two arbitrary internal swings. Require reclaimed structural raid and later body break of an already-known key; flow may establish on continuing STRUCTURE_CONFIRMED as well as post-BOS CONF. |
| SW22 p6: flow stays valid while delivering to global POI; its test ends flow | Freeze destination for each generation; later same-direction confirmations do not retarget it to an untested nearer zone. Invalidation observed on closed native lower-TF bars. No automatic opposite entry on a target touch; opposite structure/liquidity proof still required. |
| SW11 p2–4,8: planned quote/SL/TP, .25–2% risk, last traded price, no SL widening; do not put stop at liquidity | Reference account 1170, 2% including assumed friction, real Bybit last-price OHLC; original SL stays fixed. Technical stop placed one representable price outside wick (software quote, not exchange tick-size claim). Gaps can exceed planned risk and are reported. |
| SW12 p2–15: structure indicator must be checked; RSI/volume/PDH-PDL/ATR auxiliary, no standalone buy/sell | Native structure independently reconstructed. PDH/PDL completed UTC day pools retained. No mandatory RSI, volume, ATR threshold or fitted indicator depth. ATR-based SFP stop/manual body invalidation is an optional alternative; primary uses the explicitly permitted technical POI stop. |
| Retained SW6 DOC14: meaningful opposing liquidity must be handled even below SL | Adverse native structural pools throughout the active structural leg block; unrelated distant historical equal pools are not universal blockers. Numeric meaningfulness beyond this contextual normalization is unspecified. |
| Retained SW10 DOC06: deviation must interact with external POI, reclaim/retest, 80% inside range | Existing external-POI conservative branch and 80/20 original-SL exit retained. SW5/9/11/12/22 do not supply a replacement Range algorithm. Two separate HTF reclaim/retest observations and .08 midpoint tolerance are declared machine normalizations. |
| Retained DOC18: D/S last opposite move, takes old liquidity, fresh, P/D | Independent existing D/S detector retained, no OB fallback or mandatory FVG. Midpoint quote is declared choice. |

## Choices frozen before outcomes

New additive files: source_pdf.py, source_pdf_cases.py, run_source_pdf_bybit.py,
config/source_pdf_policy.json. No new data-dependent optimization. Use all 40
native saved series / 993575 candles, verify original input hashes and identity,
no interpolation. Whole-history detection and execution, not a favorable period.
Already-inspected 2026 remains DEVELOPMENT, not OOS.

Independent SOURCE_TRADE_CASE_VALIDATION removes shared BUSY/budget admissions;
each unique physical reaction has its own fixed reference account. Separate
visits to the same OB are different opportunities; overlapping multi-TF reports
of one reaction deduplicate before fills/outcomes. Earliest READY retained, then
larger HTF/smaller LTF/fixed symbol priority/ID; never replace canceled first quote
with a later one after inspecting outcomes. Execute real native 5m bars whose
OPEN is at/after READY. Costs .0006 each side, slippage .0002 each fill, pessimistic
stop-first ambiguity, no invented favorable gap improvement, no endpoint closure.
Primary first50 CLOSED cases sorted by filled-entry interval, READY then fixed
ties. Retain all later CLOSED, OPEN, pending, canceled and duplicate evidence.
All execution and source snapshots are causal; future outcome only labels CLOSED
after pre-registered opportunity selection. Undefined ratios remain null.

Separate one-position portfolio and ANY_TF diagnostics cannot substitute for
primary cases. Source interpretation has finite scope: full replay proves the
maximum for this registered implementation, not a mathematical maximum of every
discretionary/optional source variant. Any remaining ambiguities stay explicit.
Do not change locked implementation/source/config during replay. Existing segments
require exact code/input/artifact --resume-existing checks; changed hashes demand
a new retained output root. Prefix-only reconstruction, future mutation, actual
fill/cost ledger, preservation and full tests must pass before delivery.
