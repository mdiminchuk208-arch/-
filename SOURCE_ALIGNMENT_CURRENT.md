# Current primary-PDF source reconstruction

The actual SW5, SW9, SW11, SW12 and SW22 PDFs are now preserved and fully read (54 pages, text and diagrams). The current additive source policy is `source-primary-pdf-native-2`; see [SOURCE_PDF_NATIVE_PROTOCOL.md](SOURCE_PDF_NATIVE_PROTOCOL.md) and [SOURCE_PDF_PROTOCOL.md](SOURCE_PDF_PROTOCOL.md) for page-cited SOURCE_RULE and explicit machine choices, and [SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md](SOURCE_ALIGNED_BYBIT_50_TRADE_REPORT.md) for results and QA. Canonical remains frozen; the retained table below describes the historical canonical/summary-based implementation, not the new primary-PDF branch. Prior source reports and policies are preserved.

## Historical retained-source table

# Source alignment: retained materials

Original PDF/DOCX files are absent. This table compares the retained primary descriptions and cited pages in `config/source_rules.json`; it does not claim independent rereading of those files. Numeric/backtest choices remain separately labelled. Real LONG/SHORT evidence uses the source chapter entry TFs 5m/15m; 60m entry is a separate requested research configuration.

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

Full extracted requirements, names/pages and code references are preserved in the matching `source_alignment.json` report artifact. Strict IMB, gap POIs, body thresholds and three targets remain declared conservative parameters; qualifying that subset does not certify every discretionary setup or establish profitability. No claim that historical zero READY is correct is made: the real pipeline now produces READY and fills.
