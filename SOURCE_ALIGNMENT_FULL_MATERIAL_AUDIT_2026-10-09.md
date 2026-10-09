# Full trading-material audit vs current Strategy Engine — 2026-10-09

## Scope

This audit replaces the earlier assumption that the available rule registry was a sufficient representation of the user's trading methodology.

The supplied archive and the previously retained matching SW.BAND PDFs were re-read as the source basis. DOCX XML text, including text stored in Word drawing/text-box parts rather than ordinary paragraphs, was included. The only primary module not physically present is `[SW.BAND]7. Работа с уровнями Фибоначчи.pdf`: the uploaded ZIP contains only its Windows shortcut. OTE/Fibonacci rules used here are therefore sourced from the supplied `Методичка.docx` and other available supplied material, not claimed as a direct read of module 7.

Authoritative rule summary: [SOURCE_OF_TRUTH_TRADING_RULES.md](SOURCE_OF_TRUTH_TRADING_RULES.md).

---

# 1. Executive result

The previous historical result **must not be interpreted as a backtest of the complete supplied methodology**.

What the old stage4 result really proved:

- historical OHLC was causal;
- selected proxy signals were not manually inserted;
- limit touches occurred on actual retained OHLC;
- virtual accounting was internally reconciled;
- BACKTEST/SHADOW execution of that saved software policy was deterministic.

What it did **not** prove:

- source-complete POI qualification;
- active Order Flow alignment;
- absence of meaningful liquidity against the setup;
- EQH/EQL / BSL/SSL context;
- Demand/Supply qualification and Premium/Discount rules;
- the conservative HTF→LTF entry sequence for every mapping;
- source-valid FTA/target selection;
- source-specific exit management.

Therefore `40 READY → 7 entries → 7 closed` was a backtest of an explicitly normalized proxy policy, not a certification of the original methodology.

The canonical engine has now been changed to fail closed: automatic gap/POI research evidence cannot promote a setup to `READY_FOR_VIRTUAL_ENTRY`. Only explicit source-qualified levels can do that. `trade_entry_allowed=false` remains unchanged.

---

# 2. Source-to-engine matrix

| AREA | SUPPLIED METHODOLOGY | CURRENT IMPLEMENTATION BEFORE THIS AUDIT | RESULT |
| --- | --- | --- | --- |
| Swing / HH-HL / LH-LL | Three-candle structural swing; bullish HH+HL, bearish LL+LH | Confirmed swing/structure state machine | STRONG MATCH |
| BOS | Body close through protected structural level | Body-close protected-level BOS | STRONG MATCH |
| Post-BOS structure | New opposite structure must form; conservative path waits for CONF | Opposite structure transition exists; CONF separate | STRONG/PARTIAL MATCH |
| SFP | External liquidity wick raid, close back inside, next candle opens valid side, then LTF structure | Sweep episodes + immediate next-candle SFP + later invalidation | STRONG MATCH |
| Range boundaries | Impulse end → correction end; 0.5 reaction; unclear ranges should be skipped | Causal range engine with midpoint/clarity logic | PARTIAL/STRONG MATCH |
| OB core | Sweep + engulf/displacement + BOS + HTF POI + structural impulse + trend + IMB context | OB evidence contains these categories | PARTIAL MATCH |
| OB first test | First test strongly preferred; repeat only with LTF confirmation | First-test freshness tracking exists | MATCH WITH SOFTWARE NORMALIZATION |
| Smooth HTF→LTF approach | Conservative variant explicitly waits for smooth approach, reaction, LTF break and new LTF POI | No source-complete smooth-approach gate | MISSING |
| POI | Generic area: OB, Breaker, manipulation, Demand/Supply, etc. | HTF three-candle gap used as automatic POI subset | PROXY / NOT SOURCE-COMPLETE |
| Demand/Supply | Old-liquidity raid, untested zone, Supply in Premium / Demand in Discount | No complete canonical detector/gate | MISSING |
| Premium/Discount | Directional context required for source zones | OTE geometry exists; context not complete across POI classes | PARTIAL |
| OTE | 0.705–0.79; 0.5 equilibrium; confluence, not standalone permission | 0.705–0.79 geometry implemented | GEOMETRY MATCH, CONTEXT PARTIAL |
| EQH/EQL | Substructure liquidity pools; can postpone entry until swept | No complete canonical EQH/EQL gate | MISSING |
| BSL/SSL | Major liquidity/context and targets | No complete canonical BSL/SSL engine | MISSING |
| Liquidity against setup | Explicitly forbidden by supplied Smart Money Trader material | Not a canonical admission blocker | CRITICAL MISSING GATE |
| STB/BTS | Trend alignment + liquidity raid + absorption + BOS/CONF | Not a canonical complete entry path | MISSING/PARTIAL |
| Mitigation | Return toward origin/0.5 | Not represented as a complete source path | MISSING/PARTIAL |
| Order Flow | Trade with active flow; flow works with liquidity toward POI | No source-complete canonical Order Flow admission gate | CRITICAL MISSING GATE |
| FTA | First opposing problem POI; partial/full take allowed | Three distinct opposing gap POIs used by auto policy | PROXY / MISMATCH |
| Three targets | Not a source prerequisite | Exactly three proxy targets required for old automatic READY | PROJECT/BACKTEST OVERLAY |
| Aggression numeric threshold | Qualitative aggressive/strong impulse | 0.6 body fraction / 1.0 engulf ratio | RESEARCH_PARAMETER, NOT SOURCE NUMBER |
| Freshness universal wick touch | Zone-specific freshness concepts; Supply/Demand explicitly untested | Universal conservative wick-touch normalization for gap proxy | SOFTWARE NORMALIZATION |
| Risk | Primary SW.BAND recommends approx. 0.25–2%; examples centred on 1–2% | Default 2%; accepted project range 2–5%; total 6% | DEFAULT MATCH; RANGE IS PROJECT OVERLAY |
| Exit management | FTA partial/full; Range 80/20; dedicated risk chapter warns against moving SL | Global 40/30/30 + TP1 cost-adjusted BE | PROJECT OVERLAY / SOURCE-SPECIFIC CONFLICT |
| Indicators | Confirmation/context only | Not primary entry triggers | COMPATIBLE |

---

# 3. Why the old automatic READY was unsafe as a methodology claim

The old automatic route could become canonical `READY_FOR_VIRTUAL_ENTRY` after satisfying:

- a gap-only HTF POI proxy;
- numeric aggression parameters;
- a source-inspired OB/OTE intersection;
- a universal freshness normalization;
- three distinct opposing gap targets.

That was useful for research, but the supplied methodology additionally contains context that was not proven by that route: generic POI class, Demand/Supply, active Order Flow, meaningful opposing liquidity, EQH/EQL/BSL/SSL context, conservative HTF→LTF approach and source-specific targets/exits.

A proxy can therefore remain a research observation, but it cannot be used as evidence that the original methodology itself produced a trade.

---

# 4. Historical seven-trade reclassification

Old stage4 lifecycle evidence contained seven actual virtual entries across six mappings. Their OHLC touches and accounting remain valid facts; their **source compliance is reclassified** below.

| MAPPING | SIGNAL / TRADE | OLD RESULT | SOURCE CLASSIFICATION NOW | WHY |
| --- | --- | ---: | --- | --- |
| 15/5 | XRPUSDT SHORT `7f9ef0e73c09c10eac6a738f` | TP1 → stop, +9.8622 | `UNCERTAIN_SOURCE` | TF path is compatible, but old automatic READY did not prove source-complete POI class, active Order Flow, or absence of liquidity against setup. TP1→BE/stop lifecycle is a project overlay, not proof of source exit validity. |
| 60/5 | XRPUSDT SHORT `3f8338b57a87fd615bbc4882` | stop, -23.4000 | `UNCERTAIN_SOURCE` | Compatible TF mapping; entry was admitted through the research POI/target proxy and lacks retained proof of the missing source-context gates. Cannot call this a source-valid loss. |
| 60/15 | AVAXUSDT LONG `75d2c61990233a3077fe2349` | stop, -23.4000 | `UNCERTAIN_SOURCE` | Compatible conservative LTF range, but source-complete liquidity/Order-Flow/POI qualification was not proven. |
| 240/5 | BNBUSDT LONG `6368e0eee22ede75c86aa9da` | stop, -23.4000 | `UNCERTAIN_SOURCE` | 4H HTF with 5m LTF can fit the Advanced conservative TF description, but the actual auto qualification remained gap-proxy based and omitted required contextual proof. |
| 240/15 | BNBUSDT LONG `b15c3672f5c912a686373246` | stop, -23.4000 | `UNCERTAIN_SOURCE` | 4H→15m is within described conservative TF range, but source-complete context was not proven. |
| 240/60 | BTCUSDT SHORT `562f49bbf510d68fc4d4c67c` | TP1 → stop, +11.1659 | `FALSE_POSITIVE_IMPLEMENTATION` **as a source-conservative entry** | The prior report itself labelled 240/60 a research mapping outside the Advanced conservative lower-TF 1–15m path. It therefore cannot be counted as a canonical source-conservative trade. Other missing source gates also remain. |
| 240/60 | AVAXUSDT SHORT `d0220592f1743192e87311f9` | stop, -23.6233 | `FALSE_POSITIVE_IMPLEMENTATION` **as a source-conservative entry** | Same 240/60 mapping violation plus missing source-complete context. |

Numerically, those seven isolated trade results sum to approximately **-96.1953 USDT**: two positive outcomes and five negative outcomes. That number describes the old proxy executions only; it is **not** the P&L of a validated source-complete strategy.

## What can and cannot be concluded from the five stops

Cannot conclude:

- that the original methodology has a poor win rate;
- that SFP/BOS/OTE themselves are the cause;
- that widening stops or loosening filters will fix performance;
- that the five stops are `SOURCE_VALID_LOSS`.

Can conclude:

- the old implementation admitted trades without proving all source-required context;
- two 240/60 trades were not valid examples of the stated conservative LTF entry path;
- old automatic READY must not be used to optimize source rules from P&L.

---

# 5. False-negative risk in the old funnel

The old funnel also cannot be treated as a complete search of source setups.

The automatic detector used a three-candle gap as the HTF POI representation. The supplied methodology permits a broader POI family (OB, Breaker, manipulation, Demand/Supply, etc.). Therefore a setup rejected because no suitable gap proxy existed may still have contained another source-valid POI class.

Likewise, the old requirement for three distinct fresh opposing gap POIs could reject a source-valid setup whose valid first target/FTA existed but three proxy targets did not.

These are **potential false negatives**, not proven missed winners. They must be re-audited only after source-complete POI/FTA detection exists.

---

# 6. Canonical correction applied

Canonical automatic promotion is now fail-closed:

- auto detector can still produce research evidence;
- research evidence is labelled `AUTO_RESEARCH_PROXY_PENDING_SOURCE_QUALIFICATION`;
- a completed proxy is surfaced with `AUTO_RESEARCH_PROXY_READY_NOT_SOURCE_QUALIFIED`;
- canonical status remains `WAITING_FOR_SOURCE_LEVELS`;
- `AUTO_RESEARCH_PROXY_NOT_SOURCE_QUALIFIED` is recorded as the blocker;
- research proxy stop/three-target values are not attached as canonical levels;
- `StrategySignal` rejects any attempt to construct `READY_FOR_VIRTUAL_ENTRY` using a non-explicit research level policy;
- `trade_entry_allowed=false` remains invariant.

The old detector remains useful for diagnostics and ablation. Its output is no longer allowed to answer a different question: “did the supplied methodology authorize this trade?”

---

# 7. Next implementation order dictated by the sources

Canonical source automation should be completed in this order, without PnL-fitting:

1. source POI taxonomy: OB / Breaker / Demand-Supply / manipulation;
2. Demand/Supply freshness + liquidity-raid + Premium/Discount gates;
3. explicit liquidity map: structural external/internal, EQH/EQL, BSL/SSL, previous-period levels where objectively specified;
4. `LIQUIDITY_AGAINST_SETUP` blocker;
5. active Order Flow state and alignment blocker;
6. conservative HTF→LTF approach state (including reaction / structure / new LTF POI); ambiguous “smooth approach” must stay research-labelled until objectively specified;
7. FTA as the first source-valid opposing POI rather than “three gap targets”;
8. setup-specific exit policy separation: Range 80/20 vs other setups; keep 40/30/30 + BE as project overlay, never source claim;
9. rerun honest historical BACKTEST only after the above gates are causal, deterministic and tested;
10. classify each new trade as source-qualified with explicit evidence attached before evaluating profitability.

No source threshold should be invented merely to increase historical P&L.
