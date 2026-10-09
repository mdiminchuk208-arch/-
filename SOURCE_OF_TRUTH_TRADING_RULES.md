# Strategy Engine — source-of-truth trading rules

Status: authoritative methodology baseline for source-alignment work.

This file is derived from the trading materials supplied by the user. It intentionally separates source rules from later software/backtest normalizations. A rule marked `PROJECT_OVERLAY` or `RESEARCH_PARAMETER` may remain available for experiments, but must never be presented as if it came from the methodology.

## Material set reviewed

Primary / dedicated sources:

1. `[SW.BAND]4. Рыночная структура (Base)` — DOCX/PDF.
2. `[SW.BAND]5. Рыночная структура (Advanced)` — PDF.
3. `[SW.BAND]6. Ликвидность` — DOCX/PDF.
4. `[SW.BAND]8. Торговые инструменты (Base)` — DOCX/PDF.
5. `SW_BAND9_Торговые_инструменты_Advanced.pdf`.
6. `[SW.BAND]10. Боковое движение` — DOCX/PDF.
7. `[SW.BAND]11. Риск-менеджмент.pdf`.
8. `[SW.BAND]12. Индикаторы.pdf`.
9. `[SW.BAND]22. Торговые инструменты (Pro).pdf`.
10. `Smart Money Trader 2.docx`.
11. `Зоны_спроса_и_предложения_Demand_and_Supply.docx`.
12. `Методичка.docx`.
13. `обучалка.docx` — supplementary mixed material; dedicated SW.BAND modules have priority on conflicts.

The uploaded ZIP contains only a Windows shortcut for `[SW.BAND]7. Работа с уровнями Фибоначчи.pdf`, not the PDF itself. OTE/Fibonacci rules below are therefore grounded in `Методичка.docx` and the other available supplied material, not claimed as a direct read of module 7.

---

## 1. Market structure

- Swing is a structural turning point, not an arbitrary visual peak.
- Advanced defines swing high/low as a three-candle structural formation.
- Bullish structure = HH + HL.
- Bearish structure = LL + LH.
- Market structure is fractal: HTF provides global context, LTF local/execution context.
- BOS requires a body/close through the protected structural level; wick-only excursion is insufficient.
- After bullish BOS, expected new bearish structure is LL + LH; SHORT is sought after the new bearish structure/LH forms.
- After bearish BOS, expected new bullish structure is HL + HH; LONG is sought after the new bullish structure/HL forms.
- CONF is a later update/confirmation of the new structure after BOS.
- The dedicated Advanced material explicitly describes waiting for CONF as the conservative approach.

## 2. Liquidity

- Price is analysed as moving from liquidity to liquidity.
- Internal liquidity exists inside an impulse/range; external liquidity exists beyond range boundaries and structural extrema.
- EQH/EQL are liquidity pools between substructure swings, not merely two arbitrary candle highs/lows.
- BSL/SSL, structural liquidity, EQH/EQL, previous-period liquidity and range liquidity are distinct context objects.
- Basic methodology uses liquidity primarily as target/context rather than a standalone entry trigger.
- EQH/EQL can identify both a target and a reason to postpone an entry until the liquidity is swept.
- `Smart Money Trader 2.docx` gives a direct prohibition: a trade must not be opened when meaningful liquidity is positioned against the setup. The engine therefore needs an explicit causal `LIQUIDITY_AGAINST_SETUP` assessment; modelling liquidity only as a target is insufficient.

## 3. SFP

- SFP is a false break / liquidity raid of a structural swing or range boundary.
- Wick takes external liquidity while the candle body fails to close beyond the swept level.
- The next candle must open back on the valid side of the swept liquidity level.
- SFP is confirmed only after these conditions are known; it is not predicted in advance.
- After SFP, execution moves to an LTF and waits for structure break/confirmation before entry search.
- SFP is valid on all timeframes; H1+ is described as the preferred search area in the dedicated module.
- A later body close beyond the SFP pattern extreme invalidates the pattern.

## 4. Order Block

Source formation/context requirements represented by the supplied Advanced material:

- liquidity sweep/raid;
- aggressive displacement / engulfing move;
- BOS / structural change confirmation;
- HTF POI context;
- location inside the structural impulse;
- alignment with active trend/flow;
- IMB is an important validation/quality component and must not be ignored.

The full engulfed candle including wicks is the OB zone in the dedicated Advanced source.

`Методичка.docx` additionally describes OB as the last candle before IMB/strong impulse and says it must sweep a high/low/wick and have a strong body relative to its wicks. No exact source number such as body fraction `0.6` is supplied.

### First test

- Normal work is overwhelmingly on the first OB test (~90% in the source wording).
- Repeat entry requires an additional LTF reaction/confirmation.

### Direct OB variant

- Limit may be placed at the relevant OB boundary or inside the zone.
- SL may be behind the OB extreme or behind the engulfing candle wick depending on the source-valid stop model.

### Conservative HTF → LTF variant

For OB approximately 15m–1D:

1. identify HTF OB/POI;
2. switch to lower timeframe (1–15m in the source chapter);
3. wait for a smooth structural approach into the HTF OB;
4. observe reaction;
5. wait for LTF structure break/confirmation;
6. require a newly formed LTF POI;
7. place the limit on that new LTF POI.

This path is explicitly described as safer/more conservative and capable of very high RR.

## 5. POI, Demand/Supply, Premium/Discount

### POI is not only FVG/gap

Advanced defines POI generically as an area of interest. It can be represented by manipulation zones, Order Blocks, Breakers, Demand/Supply zones and other qualified trading elements.

Therefore `HTF_THREE_CANDLE_GAP_POI_BACKTEST_PARAMETER` is a research subset, not source-complete POI detection.

### Demand/Supply

From `Зоны_спроса_и_предложения_Demand_and_Supply.docx`:

- forming movement must raid old liquidity;
- Supply/Demand zone must be untested/fresh;
- Supply is valid for sells in Premium;
- Demand is valid for buys in Discount.

## 6. OTE / Premium / Discount

- 0.5 = equilibrium/fair value.
- OTE = 0.705–0.79 in the supplied methodology.
- Premium/Discount context matters.
- OTE is strongest with a valid OB/POI.
- OTE is a confluence component, not independent entry permission.

## 7. Breaker / STB / BTS / Mitigation / Order Flow

### Breaker

- Breaker is an OB/base broken by a meaningful impulsive structural move.
- Conservative stop behind the liquidity-sweeping impulse is explicitly described as safer than the aggressive stop.

### STB/BTS

Source-valid STB/BTS entry context requires:

1. intended direction agrees with the main trend;
2. the move raids a liquidity pool and fully absorbs the manipulation on reversal;
3. BOS or CONF occurs.

Return/mitigation toward origin / 0.5 is part of the concept.

### Order Flow

- Order Flow is the sequence delivering price to a global POI.
- It requires active work with liquidity.
- Trades should be taken in the direction of active Order Flow.
- Once the destination/global POI is tested and flow breaks, the previous flow is no longer valid context.

A Strategy Engine that ignores active Order Flow as an entry-context filter is not source-complete.

## 8. Range / deviation

- Range forms after a strong directional impulse.
- First boundary = end of impulse; second boundary = end of subsequent correction.
- Correct range construction requires meaningful reaction at 0.5/midpoint.
- Unclear/smudged range geometry should be skipped rather than force-fitted.
- Deviation = raid of external liquidity beyond a range boundary.

### Aggressive range trade

- Requires deviation and relevant POI context.
- Source-specific exit rule: 80% of position is fixed inside the range near the opposite boundary; 20% may remain for a true breakout.

### Conservative range trade

- If an external POI is acting as a magnet, do not enter inside the range before that POI interaction.
- Wait for reaction, return/acceptance back inside the range and boundary retest before entry.

## 9. Targets / FTA

- FTA = First Trouble Area, the first relevant opposing POI after the structure/character change.
- Partial or full profit may be taken at FTA.
- Source does not require exactly three distinct fresh gap POIs for trade validity.
- TP1/TP2/TP3 is a product/project model and must be derived from source-valid targets without turning `three targets exist` into a false source prerequisite.

## 10. Stops

Source-valid stop concepts include:

- technical stop behind OB extreme;
- stop behind engulfing/liquidity-sweeping impulse wick in the applicable model;
- conservative Breaker stop behind the impulse/liquidity-sweep extreme;
- ATR may support stop-distance context.

The dedicated risk module says entry, stop and target must be determined before entry and warns against moving the stop after the fact. Therefore `TP1 -> cost-adjusted breakeven` is a `PROJECT_OVERLAY`, not a source rule from that risk module.

## 11. Risk

Primary SW.BAND risk module:

- professional risk is generally no more than 2% per trade depending on the system;
- recommended percentage-risk approach is roughly 0.25–2% per trade;
- position size is derived from risk amount / distance to SL;
- consistency and planned exits matter more than chasing extreme RR.

Supplementary `обучалка.docx` describes 1–2% as low/conservative and 2–5% as medium risk. Therefore current project-level 2–5% support is a `PROJECT_OVERLAY`, not the strict primary-module default. Current default 2% remains compatible with the primary module.

Leverage itself does not determine PnL; position size does.

## 12. Indicators

- RSI, Volume, PDH/PDL, ATR and structure indicators are supporting/context tools.
- Indicators are not standalone buy/sell signals.
- PDH/PDL are important previous-day liquidity/context levels.
- Volume can confirm strength/weakness.
- ATR can support volatility/stop selection.

---

## 13. Existing software policies that are NOT source rules

The following must remain explicitly separated from canonical source compliance:

1. `HTF_THREE_CANDLE_GAP_POI_BACKTEST_PARAMETER` — incomplete POI subset.
2. `THREE_DISTINCT_OPPOSING_POI_NEAR_EDGES_BACKTEST_PARAMETER` — not a source requirement for trade validity.
3. `BODY_FRACTION_AND_ENGULF_RATIO_BACKTEST_PARAMETER` with `0.6 / 1.0` — numeric thresholds are not supplied by the methodology.
4. Inclusive wick-touch as one universal POI-freshness definition — software normalization, not universal source wording.
5. Global `40/30/30` TP allocation — `PROJECT_OVERLAY`; Range has an explicit source 80/20 exit rule.
6. `TP1 -> breakeven` — `PROJECT_OVERLAY`, not the dedicated risk-module default.
7. 2–5% allowed risk range — `PROJECT_OVERLAY`; primary SW.BAND module is materially more conservative.
8. Any path with BOS but without the required new structure / selected conservative CONF context must be labelled non-conservative research.
9. Any trade that ignores meaningful opposing liquidity or active Order Flow is not source-complete.

## 14. Mandatory gates before canonical READY

A canonical source-aligned engine must causally answer:

1. What is the HTF trend / active Order Flow?
2. What exact structural context exists on the execution TF?
3. What liquidity was raided, and what meaningful liquidity remains against the setup?
4. Was the SFP/deviation/manipulation fully confirmed?
5. Did the required LTF BOS/new structure/CONF occur for the selected source path?
6. Is the candidate POI source-valid (OB, Breaker, Demand/Supply, manipulation, etc.), not merely a gap proxy?
7. Is the zone fresh/untested according to that zone type's source semantics?
8. Is LONG in Discount / SHORT in Premium where the selected source zone requires it?
9. Is the OB/POI inside structural impulse and aligned with trend/Order Flow?
10. Is meaningful liquidity positioned against the setup? If yes, reject/postpone unless the source path explicitly requires its sweep first.
11. Is entry/SL source-valid?
12. What is FTA / first opposing source-valid target?
13. Does this setup type have its own exit rule (e.g. Range 80/20) rather than blindly inheriting global 40/30/30?

No setup may reach canonical `READY` while a required source question is silently represented by an unrelated proxy.

## 15. Audit classification

Every historical virtual trade is to be classified as one of:

- `SOURCE_VALID_LOSS` — legitimate loss allowed by the methodology;
- `FALSE_POSITIVE_IMPLEMENTATION` — software admitted a trade the source would reject/postpone;
- `UNCERTAIN_SOURCE` — retained evidence is insufficient to prove source compliance.

False negatives must also be audited: source-valid opportunities may have been rejected by gap-only POI, three-target prerequisite or another software proxy.

Canonical strategy changes are driven by source alignment first, not retrospective PnL fitting.
