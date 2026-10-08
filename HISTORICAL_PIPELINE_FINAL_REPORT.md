# Real historical Strategy Engine: итог текущего этапа

Результат **A для текущей сохранённой автоматической BACKTEST/SHADOW политики**:
**27 974 emitted setups → 40 READY → 7 virtual entries → 7 CLOSED**.
Реальные LONG и SHORT прошли qualification, actual OHLC touch, управление,
закрытие и независимую денежную сверку. Исторические сигналы не создавались вручную.

Это проверка исполнения сохранённой политики `0.4.21-causal-limit.3`, с её явно
обозначенными параметрами и консервативными gap-POI proxies. Сопоставлены сохранённые
source requirements; независимая сертификация отсутствующих первичных PDF/DOCX
не заявляется. Результат B «исходная стратегия объективно не содержит входов»
не заявляется. Закрывать работу объяснением «стратегия слишком строгая» не пришлось:
найдены и исправлены конкретные implementation/wiring defects.

## CHECK | STATUS | EVIDENCE

| CHECK | STATUS | EVIDENCE |
| --- | --- | --- |
| Saved base and original ZIP | PASS | `b059844`; 765 paths/modes/Git blobs exactly equal; stage1 ZIP receipt |
| Real-history qualification and entries | PASS | 6 full mappings; 40 READY, 7 filled/closed; stage3 logical runs, stage4 independent audit |
| Real LONG and SHORT in source entry TFs | PASS | AVAX 60/15 LONG, XRP 60/5 SHORT; actual source candles and causal snapshots |
| All setup outcomes explained | PASS | 27 974 mutually exclusive rows; 80 752 emitted signal states exactly matched production |
| OB search and availability | FIXED | Full 4 659 original audits; causal origin/anchor window and max(C close,BOS close) clock |
| Original nine POI rejections | EXPLAINED | All nine reviewed; all 51 preexisting overlapping seed instances genuinely previously touched |
| Range zero / manual clarity | FIXED | Same 7 667 episodes; 3 393 SFP_FORMED; zero CLARITY_REVIEW_BLOCKED |
| Real price and monetary reconciliation | PASS | Every entry and 9 exit reference prices checked; quantity, costs, risk, balance/fees reconciled |
| No lookahead on actual filled signals | PASS | Real LONG/SHORT prefix, future mutation, independent snapshots; checkpoint before/after fill |
| Deterministic replay | PASS | Current 57 code/config hashes; all eight reports byte-identical, workers 2 vs 1 |
| BACKTEST/SHADOW parity | PASS | Actual LONG 60/15 and SHORT 240/60; economic reports identical, signal difference only mode |
| Full tests | PASS | 410 tests; stage4_full_tests.log |
| Lint / mypy | PASS | E9,F clean; 55 source files clean |
| HTF alignment | PASS | 302 362 complete aggregates; zero OHLC mismatch, zero misaligned bars |
| Source alignment | QUALIFIED | Retained descriptions/pages matched; numeric parameters/software proxies explicitly separated |
| Additional PUBLIC Bybit download | BLOCKED_BY_PROXY | Actual API and public archive attempts without keys: tunnel 403; retained retry evidence |
| Safety | PASS | trade_entry_allowed=false, no LIVE/private API/order execution |

All stage4 evidence is under
[`data/reports/historical_blocker_investigation/stage4`](data/reports/historical_blocker_investigation/stage4).
`EVIDENCE_MANIFEST.json` records stored and decompressed SHA256 for every evidence
file. Gzip preserves the full logical content. Existing user artifacts remain.

## SAVED BASE

* Current canonical repository: **mdiminchuk208-arch/-**; branch **main**.
  GitHub moved the previous `mdiminchuk208-arch/Zsfhjl-` address; old links redirect.
* Starting commit: **b0598444498906638559e22dd1e5770123bd8cd1**.
* Original delivered GitHub ZIP: **63 591 840 bytes**, SHA256
  `5fab890123a3e50a0c834693de70c534a9ec41952d7bef0115e6e12f9c4df50a`.
* Exactly **765** archive entries, file modes and Git blob contents match that base;
  archive comment contains the same hash. No tracked base path was deleted.
* Base archive remains locally preserved in `/workspace/deliverables/` and available
  through the immutable GitHub archive of `b0598444498906638559e22dd1e5770123bd8cd1`.
* The final main intentionally contains subsequent fixes and evidence. Its final ZIP
  is generated and compared with that final commit after publication; it is not
  presented as byte-identical to the old baseline ZIP.

## REAL HISTORY FUNNEL

| STAGE | INPUT | PASS | REJECT | PASS RATE |
| --- | --- | --- | --- | --- |
| SETUP | 27974 | 27974 | 0 | 100.00% |
| STRUCTURE | 27974 | 27974 | 0 | 100.00% |
| BOS | 27974 | 27974 | 0 | 100.00% |
| ENTRY GEOMETRY | 27974 | 25158 | 2816 | 89.93% |
| OB candidate | 25158 | 20613 | 4545 | 81.93% |
| valid OB | 20613 | 1311 | 19302 | 6.36% |
| HTF POI | 1311 | 1216 | 95 | 92.75% |
| preexisting POI | 1216 | 1214 | 2 | 99.84% |
| fresh POI | 1214 | 75 | 1139 | 6.18% |
| supporting POI | 75 | 75 | 0 | 100.00% |
| OB first test | 75 | 50 | 25 | 66.67% |
| SL | 50 | 47 | 3 | 94.00% |
| targets | 47 | 40 | 7 | 85.11% |
| R:R | 40 | 40 | 0 | 100.00% |
| Score | 40 | 40 | 0 | 100.00% |
| READY | 40 | 40 | 0 | 100.00% |
| virtual entry | 40 | 7 | 33 | 17.50% |

The universe is **emitted execution setups**, which already contain causal
structure/BOS links. Therefore STRUCTURE/BOS pass rates here are 100%; they do not
mean every raw sweep passed. Raw Range episodes have a separate complete partition.

Each setup receives one first unpassed gate after its greatest **sequential**
progress at a causal, still-alive observation, using **one candidate** at that
observation. Candidate A/B/C facts are never combined across different OBs or
timestamps. A temporary WAIT that later passes is not a permanent setup rejection.
For a READY without entry, the first pending-order withdrawal/admission rejection
is preserved; later context invalidation cannot replace it. Requalification times
and final execution status are retained separately. A real later fill takes precedence.

Every row has an explicit cause. `INPUT=PASS+REJECT`, next INPUT=previous PASS,
and total REJECT + seven entries = 27 974. The single right-censored READY at
data end is included in the no-entry column, with an explicit censorship reason.
Full candidate OHLC/availability traces and all setup rows are retained for each mapping.

## OB: NO_POST_BOS_OB_PATTERN

The exhaustive original 60/5 audit reproduced 6 357 setups, 5 842 automatic-level
attempts and all **4 659** no-pattern cases:

| Original no-pattern cause | COUNT |
| --- | --- |
| Empty BOS+2 .. anchor-1 window | 3 342 |
| No required opposite A/B colours | 845 |
| No full body engulfing | 472 |

`OB_CORE_001` describes sweep/engulfing displacement/BOS confirmation. The prior
window incorrectly required OB formation after BOS and excluded the anchor.
`OB_LTF_ENTRY_001` requires waiting for BOS before searching/placing a limit; it
does not discard the causal candles that produced the confirmed impulse.
Now the candidate window starts at the latest causal pre-BOS structural adverse
extreme matching the frozen impulse origin and includes engulfing at the selected
anchor. A missing exact causal origin fails explicitly. Qualification still waits
for closed BOS and C/IMB availability.

All original BOS directions/identities, protected levels, times, A/B/C candles,
counts and rejection causes are in stage1 `original_ob_poi_v2/`. LONG/SHORT
symmetry, body engulfing, strict wick sweep, anchor inclusivity, foreign impulse
exclusion and missing origin have regression tests. Timeframe aggregation has
an independent real-data comparison. Threshold .6 body fraction / 1.0 engulf
ratio, raw liquidity sweep, trend, IMB, OTE intersection, SL and targets were retained.

The first stable window-only full 60/5 run reduced no-pattern setups to **1 020**
while READY stayed zero. After Range/tail wiring changes, the final exact 60/5
first-rejection count at OB candidate is **1 022** in 6 367 setups. These have
different emitted universes; they are not falsely represented as identical IDs.

A second defect consumed an OB on its own forming BOS candle. First-test tracking
now starts strictly after **max(C close, BOS close)**; later wick overlap remains
consumption. This is an availability fix, not relaxed freshness.

## POI / TOUCH / FRESHNESS

All original **nine** FRESH_PREEXISTING_HTF_POI_NOT_FOUND cases include symbol,
direction, setup/BOS timestamps, TFs, candidate creation/availability, price ranges,
first touch and all prior touches. Across them **51** overlapping preexisting
gap seed instances were found; **all 51 were genuinely stale**. These original
rejections were not changed just to obtain entries.

Current explicit machine semantics:

* POI is available only after its third forming candle closes; formation and earlier
  price activity do not count as post-availability touches.
* Supporting POI must be same-direction, known by A OPEN, overlap A and align with
  the confirmed expected structural transition. A is the current reaction; earlier
  closed candles after availability determine prior freshness.
* Inclusive **wick** overlap consumes freshness; body/close overlap is unnecessary.
  Exact boundary equality touches. `nextafter` outside a boundary remains outside.
* A candle not yet closed by the query cutoff contributes no later HIGH/LOW.
* The interval index is checked against an independent linear scan. Partially
  covered future nodes never contribute aggregate prices to an earlier query.
* OB first-test clock differs from the HTF gap formation clock and waits for complete
  OB/BOS availability. Actual BOS/C formation candles are not later retests.

Regression evidence is in `tests/test_freshness_index.py`,
`tests/test_ob_impulse_window.py`, `tests/test_ob_entry_reference.py` and replay
prefix tests. Body-only/close-only alternative touch policies are audited, but
are not substituted for the declared conservative wick-touch policy.

PREEXISTING + FRESH is attainable: the current partition contains **75** setups
with fresh supporting POI and **40** with all READY gates. Gap-only recognition,
preexisting-at-A and three opposing targets remain explicitly declared backtest
choices; they are not invented quotations from the original PDF.

## RANGE / CLARITY

| Same original episodes | BEFORE | AFTER |
| --- | --- | --- |
| Total boundary sweep episodes | 7 667 | 7 667 |
| SFP_FORMED | 0 | 3 393 |
| CLARITY_REVIEW_BLOCKED | 3 393 | 0 |
| CONSUMED_NO_SFP | 4 260 | 4 260 |
| AMBIGUOUS_DUAL_SIDE_SWEEP | 14 | 14 |

Every CONSUMED_NO_SFP case failed **SWEEP_CLOSE_NOT_INSIDE**: the wick raid did
not reclaim inside on that close. The 14 dual-side raids cannot establish intrabar
ordering from OHLC; **DUAL_SIDE_ORDER_UNOBSERVABLE** remains an explained fail-closed
case. All 3 393 previously blocked cases already satisfied the SFP price sequence;
the mandatory manual UNREVIEWED placeholder was their sole formation blocker.

Automatic clarity now proves ordered confirmed directional swing boundaries,
midpoint reaction and clean internal structure at validation. It does not admit
dirty geometry or use later invalidation to revoke prior validation. Explicit
manual overrides and legacy review mode remain auditable. The historical index
now includes the same Range events as independent prefix snapshots.

All 7 667 before/after episodes and **214 stratified full traces** follow BREAKOUT
→ boundary interaction → reclaim → candidate → next-OPEN SFP confirmation. No
Range boundary liquidity is reactivated after consumption. Parent status at audit
end is separately recorded: 6 324 episode observations belong to retired ranges,
1 302 to internally invalidated ranges, 41 to still validated ranges. These are
episode-parent observations, not counts of unique ranges; later parent status
does not erase an earlier correctly formed SFP. Range SFP does not by itself imply READY.

## SOURCE ALIGNMENT

| RULE | SOURCE REQUIREMENT | CURRENT IMPLEMENTATION | STATUS |
| --- | --- | --- | --- |
| BOS | MS_BOS_CONTEXT_001; [4, 5] | Protected HL/LH body acceptance; frozen exact BOS identity | MATCH_RETAINED_SOURCE |
| SFP | SFP_FORMATION_001; 5 | Strict wick raid, close reclaim, immediate next OPEN inside, then LTF BOS | MATCH_RETAINED_SOURCE_BULLISH_MIRROR_LABELLED |
| OB | OB_CORE_001; 2 | Sweep, full opposite-body engulf, BOS, HTF POI, impulse/trend; IMB retained conservatively | MATCH_SOURCE_ELEMENTS_WITH_DECLARED_NORMALIZATIONS |
| OB window | OB_CORE_001; 2 | Former A-after-BOS empty window replaced by causally confirmed BOS impulse, anchor included | MISMATCH_FIXED |
| Entry | OB_LTF_ENTRY_001; [4, 5, 6] | Limit quote in OB/OTE intersection, actual future touch, no signal-bar fill | MISMATCH_FIXED |
| Entry TF | OB_LTF_ENTRY_001; [4, 5, 6] | 5m/15m source chapter range; 240m/60m is explicitly requested research mapping outside chapter 1-15m | SOURCE_TF_DISTINCTION_RETAINED |
| Aggression | OB_AGGRESSIVE_THRESHOLD_001; None | Body fraction .6 / engulf ratio 1.0 unchanged; no PnL fitting | BACKTEST_PARAMETER_NOT_SOURCE_NUMBER |
| HTF POI | OB_CORE_001; 2 | HTF three-candle gap is a declared subset/normalization, not exhaustive discretionary POI recognition | EXPLICIT_CONSERVATIVE_SUBSET |
| Preexisting/supporting | OB_CORE_001; 2 | Supporting same-direction HTF gap known by A OPEN; A overlaps; expected transition aligns | CAUSAL_MACHINE_INTERPRETATION_NOT_SEPARATE_SOURCE_QUOTE |
| Fresh POI | OB_FIRST_TEST_001; 3 | No prior closed wick overlap, equality included; seed formation excluded; 51 original candidates genuinely stale | EXPLICIT_CONSERVATIVE_TOUCH_NORMALIZATION |
| Fresh OB | OB_FIRST_TEST_001; 3 | First-test clock strictly after max(C close,BOS close); no premature BOS consumption | AVAILABILITY_BUG_FIXED_FIRST_TEST_SUBSET |
| OTE | retained trade_plan.py / project OTE description; no raw page verified | Frozen broken extreme, opposite structural anchor/correction; .705-.79 source zone | PRESERVED_GEOMETRY_NO_INDEPENDENT_RAW_SOURCE_VERIFICATION |
| Targets | OB_CORE_001; 2 | Three distinct opposing gap near edges; original FTA extended explicitly for requested TP1/2/3 | BACKTEST_PARAMETER_NOT_THREE_SOURCE_TARGETS |
| Range boundaries | RANGE_BOUNDARIES_001; 2 | Directional impulse-end then correction-end; midpoint reaction and clean structure | MATCH_RETAINED_DESCRIPTION_WITH_PROXY_AND_TOLERANCE |
| Range SFP | SFP_RANGE_BOUNDARY_001; 5 | Same SFP rule on causally validated boundaries; original liquidity never reactivates | WIRING_MISMATCH_FIXED |
| Clarity | RANGE_BOUNDARIES_MAY_BE_NONCRISP_001; RANGE section | Existing explicit price area proof replaces unconditional manual UNREVIEWED placeholder | UNFINISHED_INTERNAL_GUARD_COMPLETED |
| Score/RR | OB_AGGRESSIVE_THRESHOLD_001; None | Score completeness, positive directional RR; no new Score/RR threshold; risk reentry >=75 unchanged | REQUESTED_EXPERIMENT_UNCHANGED |


The full extracted names/descriptions/pages/code references are retained in
`source_alignment.json` and [SOURCE_ALIGNMENT_CURRENT.md](SOURCE_ALIGNMENT_CURRENT.md).
Raw original PDF/DOCX are absent from this environment. Source elements are
preserved; .6 aggression, gap seeds, conservative wick-touch and three targets
remain declared parameters/proxies. No Score/risk/POI/SFP/BOS gate was removed to
increase trades. No parameter was optimized against this dataset's PnL.

## REAL DATASET

Ten symbols: BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK, AVAX, LTC (USDT).
**40 original CSV series, 993 575 candles**, approximately 240 days. TF 5m:
691 199 candles; 15m: 230 396; 1H: 57 590; 4H: 14 390. Every original row is
labelled exchange BYBIT. Individual raw ranges can differ slightly; each run
uses the shared complete coverage after 576 LTF warmup bars. 1D is not used.
All market timestamps in this report are UTC.

Actual keys-free PUBLIC requests to Bybit API and public historical archive
failed at the configured Cloud proxy with **Tunnel connection failed: 403 Forbidden**.
`public_bybit_retry.json` preserves the attempts. Public GitHub access works;
the environment does not permit these Bybit destinations. No credential/private
API, proxy bypass or synthetic historical replacement was used. Expanded history
was therefore not obtained. No independent fresh exchange download is claimed.

The retained raw files were not edited. An independent reconstruction of **302 362**
complete 15m/60m/240m bars from original 5m data found **zero OHLC mismatch** and
**zero aggregation misalignment**. Full raw dataset identities:

| SYMBOL | TF | START UTC | END UTC | CANDLES | SHA256 |
| --- | --- | --- | --- | --- | --- |
| ADAUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `b8f17c32c2c4a523f17ac9e44513261745477282627e400a3b6169016dc24d59` |
| ADAUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `939333c98892c91ff92cbf7bf09419bf05e0cc887e0a1de8abfe65dfe6818c14` |
| ADAUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `1600da71e214406729f547b1feb78d9dade86f33158bbdd879ccdfa074da2535` |
| ADAUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `d27de20a0b7c39c4fde21a2f7b66861c1aee3e5aecaa9b026b8ffc1013899bf5` |
| AVAXUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `ee67aa28fe93495d5fcc2bd275014f793e3b9bc726f2f159f37b7b9a2207616d` |
| AVAXUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `f8237dd5549d4061556b38b69f279aca828134c63310018b2224b321bc84b162` |
| AVAXUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `2d2f5312a3688b17ef39b1b67e1c97d54c7afdba9a80a5c54588dd3ac84e216e` |
| AVAXUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `ecb3abbddbc2d644c5f33ebac80b141bae7d068e2efe96fab231805e27245d5e` |
| BNBUSDT | 15 | 2026-01-25T12:30:00+00:00 | 2026-09-22T12:15:00+00:00 | 23039 | `916374fc697cea7d4b567ae2356fd332c63153d1532120bd5939f82b9c985f48` |
| BNBUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `68ac140426f226c5a53e0c268dad9c8c5f518b3b80fd84f2212c2a5bc0f6c722` |
| BNBUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `c76a359d661f7cb02b84a246a637efe519c10e93405c29962d57757ad843ec58` |
| BNBUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `e58b16ecb30024a5d95adfefd238371f14e61837d7d0618a0e711118753d5246` |
| BTCUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:15:00+00:00 | 23039 | `c15a595e948ad4d329c8b6044a95665dfbe53b97a2ef2d62df0d5230b8274b21` |
| BTCUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `017a82769092847de9409bd71f8c0de2935f932661f1f202549b54453a501f7c` |
| BTCUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:15:00+00:00 | 69119 | `5035989c9d85cecb05980946931daed7bc3fcf1e7d4e8cc0cd36498e25550e16` |
| BTCUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `711bc9aebbb618f450ac186f1a0a9d06309941c64e3489a5060292cabb502d54` |
| DOGEUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `37e7e19c601e945e8b3305e3ffcafa72582ecf05d5c4257b11521ff8c1cbaa66` |
| DOGEUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `686d4d1655f4e98f591ba88f49698c356015d63940d700e84dbaa7b2ed47278c` |
| DOGEUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `ef2c8cd457f3645cbf214f472cb7bfac997bbcd3c51ee9fd08dbdfaa06bdf5f6` |
| DOGEUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `d3588b39bf4ba2870ba7d8171f42c9a78074414080f1dcfe4b011d41f1853b3e` |
| ETHUSDT | 15 | 2026-01-25T12:30:00+00:00 | 2026-09-22T12:15:00+00:00 | 23039 | `c42c68735311d4e7045ddec5c622b6a899d07bce71fec2f3cc21bf4c2f8cf9e0` |
| ETHUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `219ecec093e68589ca35ec90c5543fed8cee7a058266978c1d92898c6286d178` |
| ETHUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `c0bc583b2af2f1bb28511547e784a0a922e1d1917cdcd44537967276c32c60ac` |
| ETHUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `6a68584ba89b7b56c5e1cd09c423c2e48eeb4823ef8c673de10ab457b4e447dc` |
| LINKUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `a00d508ffecfa07ef0799d21b65f29d35fc151a060edcd90c7a09c37c361a0c3` |
| LINKUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `c1c9d5febf3bbb253f30cd6ce2f9ff570bb3f3c8902e13b9e28ccd391c9940c6` |
| LINKUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `1dd65bb46df23fa092e64f361f5fb9d374facbccd7ebbad61a8c42fac888ec77` |
| LINKUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `71e75f38b4622d5417f86bfa1511a6fd056fe53b647e4cfd4778b87a659c3868` |
| LTCUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `10ff91d16c538b014c21138e420260a9778e35cc0e7ef6aa8d639a85ebb314fc` |
| LTCUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `093b55606ced0dc4d7f427990473f970305217e5e4f727ce05aed96f7c44cd63` |
| LTCUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `39331424b5986abc46cc32dcc4b322bf934034c2215d0a9c915b8c847b3d14cd` |
| LTCUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `354ceaf165a19fad08ee2b2f94404841d31a7721dc556917c166487a9621ed31` |
| SOLUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:15:00+00:00 | 23039 | `eed5ce7e194c1bc78cf69e365993021d491f0c846b096070dd561ad677d29481` |
| SOLUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `522080db3e29661dc78648d90e304224b9a521ff17e2c191239e787b346d8b2c` |
| SOLUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `119edc89b702c8b658fd86a1827dd08f7e9ff65960582ac56bb9609644eeb046` |
| SOLUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `db51eaadcf3ad68a2aa64df138dd7b0b63f3d0f046b8addeb377c47236e08bb9` |
| XRPUSDT | 15 | 2026-01-25T11:30:00+00:00 | 2026-09-22T11:30:00+00:00 | 23040 | `e9007109253dd38273702460c002a14d5069615403e115238e0e1153938dd013` |
| XRPUSDT | 240 | 2026-01-25T12:00:00+00:00 | 2026-09-22T08:00:00+00:00 | 1439 | `e49b9039cb3fcec87c725b97a79a4055f5d4aeb496e32931d2f914d82bb34f75` |
| XRPUSDT | 5 | 2026-01-25T11:20:00+00:00 | 2026-09-22T11:20:00+00:00 | 69120 | `74f7c34ef46c0d112d24f86b66be89d50806e3a03f193b4cce0654129989c5c8` |
| XRPUSDT | 60 | 2026-01-25T12:00:00+00:00 | 2026-09-22T11:00:00+00:00 | 5759 | `fd086ca3baf8a2d1b6668d0fc1075e3b76393007411087d3a53b6fc4edf902bd` |

## BEFORE / AFTER

| HTF/LTF | BEFORE SETUPS | AFTER SETUPS | READY | ENTRIES | CLOSED | FINAL EQUITY |
| --- | --- | --- | --- | --- | --- | --- |
| 15/5 | 12641 | 12656 | 25 | 1 | 1 | $1179.862166 |
| 60/5 | 6357 | 6367 | 5 | 1 | 1 | $1146.600000 |
| 60/15 | 4090 | 4097 | 6 | 1 | 1 | $1146.600000 |
| 240/5 | 2182 | 2184 | 1 | 1 | 1 | $1146.600000 |
| 240/15 | 1665 | 1667 | 1 | 1 | 1 | $1146.600000 |
| 240/60 | 1001 | 1003 | 2 | 2 | 2 | $1157.542548 |

BEFORE had 27 936 setups, zero READY/entries. AFTER has 27 974 setups, 40 READY,
seven entries and seven closed positions. Added setup instances come from Range
wiring and retention of previously omitted closed LTF tail data; OHLC was unchanged.
Each row is an **independent configuration portfolio starting with $1 170**.
Their PnL is not combined. The XRP event appears under two mappings; seven fills
are not asserted to be seven independent market opportunities.

Current mutually exclusive first rejections/outcomes:

| FIRST REJECTION / OUTCOME | COUNT |
| --- | --- |
| AGGRESSIVE_IMPULSE_THRESHOLD_NOT_MET | 3610 |
| ALL_HTF_CONTEXTS_INVALIDATED_BEFORE_FURTHER_PROGRESS | 617 |
| ALL_PREEXISTING_HTF_POIS_PREVIOUSLY_TOUCHED | 1139 |
| DIRECTIONAL_IMBALANCE_NOT_CONFIRMED | 6432 |
| ENTRY_LEVEL_EVIDENCE_WITHDRAWN | 4 |
| GEOMETRY_NOT_RESOLVED_BEFORE_CONTEXT_OR_DATA_END | 2199 |
| HTF_POI_NOT_PREEXISTING_AT_OB_A_OPEN | 2 |
| ISOLATED_MARGIN_BUDGET | 11 |
| LIMIT_NOT_FILLED_BEFORE_OB_FIRST_TEST_CONSUMED | 17 |
| NO_OB_CANDIDATE | 4545 |
| NO_OVERLAPPING_DIRECTIONAL_HTF_POI | 95 |
| OB_FIRST_TEST_ALREADY_CONSUMED | 25 |
| OB_OUTSIDE_OTE_OR_STRUCTURAL_IMPULSE | 5448 |
| OB_STOP_DOES_NOT_PROTECT_ENTIRE_OTE | 3 |
| PRICE_NOT_FILLED_BEFORE_DATA_END | 1 |
| RAW_STRUCTURAL_LIQUIDITY_SWEEP_NOT_FOUND | 3812 |
| THREE_DISTINCT_FRESH_OPPOSING_POIS_NOT_FOUND | 7 |
| VIRTUAL_TRADE_CLOSED | 7 |

Of 40 READY, **17** never reached the quoted price before a broader OB first-test
touch consumed eligibility; **11** hit unchanged isolated-margin budget; **four**
lost a fresh opposing target before execution; **one** remained unfilled at dataset
end; **seven** filled and closed. For the four target withdrawals, eight exact
before/after production-matched candidate traces show the fresh target count
falling below three. Initial/last READY times and later requalification are both
retained, with no replacement by a later final invalidation.

## REAL EXECUTION / LIFECYCLE / PnL

| HTF/LTF | SYMBOL | SIDE | ENTRY KNOWLEDGE TIME UTC | EXIT FILLS | NET PnL |
| --- | --- | --- | --- | --- | --- |
| 15/5 | XRPUSDT | SHORT | 2026-09-19T05:30:00+00:00 | TP1 → STOP_FIRST_CONSERVATIVE | $9.862166 |
| 60/5 | XRPUSDT | SHORT | 2026-09-19T05:30:00+00:00 | STOP_FIRST_CONSERVATIVE | $-23.400000 |
| 60/15 | AVAXUSDT | LONG | 2026-05-12T14:30:00+00:00 | STOP_FIRST_CONSERVATIVE | $-23.400000 |
| 240/5 | BNBUSDT | LONG | 2026-03-31T10:00:00+00:00 | STOP_FIRST_CONSERVATIVE | $-23.400000 |
| 240/15 | BNBUSDT | LONG | 2026-09-10T12:45:00+00:00 | STOP_FIRST_CONSERVATIVE | $-23.400000 |
| 240/60 | BTCUSDT | SHORT | 2026-04-29T10:00:00+00:00 | TP1 → STOP_FIRST_CONSERVATIVE | $11.165866 |
| 240/60 | AVAXUSDT | SHORT | 2026-09-20T12:00:00+00:00 | STOP_FIRST_CONSERVATIVE | $-23.623317 |

The emitted quote/execution zone is the qualified **OB ∩ OTE**; unrelated OTE
midpoint no longer replaces the selected OB. A quote is available only after its
source facts. A READY queued at CLOSE can fill only on subsequent candles.
OPEN fills must be inside the zone and no worse than the quoted limit; otherwise
the properly sided OPEN followed by an actual wick crossing supplies a resting-limit
fill. Wrong-side gaps outside the zone do not fabricate fills.

An intrabar fill has a **bar interval** and knowledge timestamp CLOSE, not an
invented exact tick execution time. Entry-bar favorable HIGH/LOW can predate the
touch, so only a subsequent favorable CLOSE proves entry-bar profit; the adverse
envelope and stop take conservative priority. Admissions occur before same-bar
exit profits across symbols. Marking a new intrabar position cannot credit price
movement from its pre-entry OPEN. Original fee/slippage friction remains; this is
a virtual cost model, not a claim about exchange limit-order fill mechanics.

All seven entries and **nine exits** reference actual original CSV price envelopes.
Two SHORT trades have real **TP1 → cost-adjusted breakeven → later stop** sequences.
The actual LONG trades close at SL. Real TP2/TP3 were **not observed** and are
not claimed as historical evidence; their constructed LONG/SHORT regressions still
pass. Every closed quantity, partial allocation, fee, slippage, risk, margin,
gross/net PnL and final balance was independently reconciled. No force-close or
hardcoded history trade was used.

## TESTS / CAUSALITY / DETERMINISM

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m ruff check src scripts tests --select E9,F
python -m mypy src scripts
```

Results: **410 tests PASS**, lint PASS, mypy PASS on 55 source files. Stable
implementation stages previously passed full suites 378, 394, 409; the additional
test fixes audit metadata for requalification, giving 410. Original tests were
retained, with strategy-registry version expectations updated when its version changed.

Full actual replay command for each table mapping:

```bash
PYTHONPATH=src python scripts/run_historical_portfolio.py --days max --htf 240 --ltf 60 --workers 2 --mode BACKTEST --report-root RUN_DIRECTORY
PYTHONPATH=src python scripts/audit_current_history.py --run RUN_DIRECTORY --output NEW_AUDIT_DIRECTORY --workers 2
PYTHONPATH=src python scripts/audit_entry_deferrals.py --run RUN_DIRECTORY --funnel NEW_AUDIT_DIRECTORY --output NEW_ENTRY_AUDIT_DIRECTORY
PYTHONPATH=src python scripts/verify_historical_lifecycles.py --runs RUN_DIRECTORY --output RECONCILIATION.json
PYTHONPATH=src python scripts/verify_historical_causality.py --runs LONG_RUN_DIRECTORY SHORT_RUN_DIRECTORY --output CAUSALITY.json
```

The report records runs performed autonomously in Cloud, not tasks delegated to
the user's computer. Real AVAX LONG 60/15 and XRP SHORT 60/5 READY snapshots
matched indexed history, independently computed snapshots, truncated prefixes
and changed future suffixes. Pending and filled real checkpoint resumes matched
complete runs. Current 240/60 repeats with workers **2 and 1** have all eight
logical reports byte-identical, including fingerprint
`609871836b657ccf015e83b7cfc5fc48c9197037e46e33eff0cbb3b563d97cc7`.
All **57** code/config input SHA values match the current files. BACKTEST/SHADOW
economic reports match byte-for-byte for real LONG 60/15 and SHORT 240/60;
signals differ only in mode. Mode-specific overall fingerprints properly differ.

## SAFETY / GIT / DELIVERY

`trade_entry_allowed=false` in engine, signals, decisions, trades and evidence.
EngineMode permits only BACKTEST and SHADOW; LIVE/private API/real orders remain
disabled. No exchange secrets, API keys, passwords, credentials or secret `.env`
are committed. Existing explicit non-secret templates and evidence are preserved.

Excluded rebuildable directories: `.venv`, `venv`, `env`, `__pycache__`,
`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.pytype`, `.tox`, `.nox`, `.cache`,
`node_modules`, `build`, `dist`, `*.egg-info`, `.eggs`, `htmlcov`. Temporary
files/caches are ignored; source/tests/config/fixtures/docs/scripts/diagnostics,
history and saved reports remain. Existing evidence logs are intentionally retained.

Stable commits in the preserved linear history:

* `b0598444498906638559e22dd1e5770123bd8cd1` — original ZIP rollback point.
* `b4a0649b42913f473877df7f0a7d8d41cc46423e` — corrected structural impulse OB window; original full audits.
* `f717797159175dbed642cbae52885e6241067d2b` — automatic Range clarity/wiring, causal availability/freshness.
* `f84977dcd995921a716acedd96fde79f925a30fc` — actual source OB limit selection and real lifecycle proof.
* This report/evidence stage is a subsequent regular commit; its final hash and
  confirmed remote main hash are returned after push and ZIP verification.

The final delivery check compares GitHub's immutable archive for that final
commit to every tracked path, mode and Git blob. A local
`/workspace/deliverables/crypto_bot_phase1_4_18.zip` is retained from the same
commit; the previous base ZIP remains available. Download through the repository's
**Code → Download ZIP**, or its immutable GitHub commit archive. No force push,
history rewrite or ChatGPT artifact publication is used.
