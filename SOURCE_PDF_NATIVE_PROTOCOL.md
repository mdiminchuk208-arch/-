# Native observation timing correction — primary PDF policy v2

Registered after the initial PDF replay (9 READY /0FILLED/0CLOSED), before new
native-timing replay outcomes. It is not represented as blinded to that earlier
result. Original PDF source rules, entry/SL/exit choices, liquidity normalization,
symbol priority, data and all costs remain as in SOURCE_PDF_PROTOCOL.md.
The earlier complete replay and all its 93 hashed artifacts are retained under
`data/reports/source_pdf_bybit_2026_10_09`; exact report/source snapshots are under
`data/reports/source_pdf_closed_htf_intermediate`.

## Objective source discrepancy

SW9 p4–6 says to switch to LTF after price approaches/enters the already known
HTF POI and then observe its reaction. The existing replay waited for that HTF
candle to close before starting the LTF reaction clock. This can discard an
already causally observed 5m raid/BOS occurring between actual touch and HTF close.
No source rule requires waiting for a second observation of an already known zone.
SW9 p11–16 calls FTA the first trouble area ahead of the entry. A zone already
crossed at READY cannot be a fresh ahead-of-price destination.

## Fixed correction before new outcomes

Observe all available HTF POI visits using CLOSED native 5m bars, only when the
zone was already known at that bar's OPEN. Never consume the forming HTF bar.
First/last visit times and contiguous visits use this same 5m clock; HTF close
must not count the same observation as a second visit. Repeat OB still requires
a wholly new LTF raid/BOS/structure/CONF after the new visit. D/S remains fresh-only.
Range deviation/reclaim/retest retains its separately registered HTF confirmation
clock. Structural BOS and body invalidation remain native to their own TF.
Observe first FTA/global destination touches on the same closed native 5m clock;
do not reuse a tested target. Before READY require current LTF close strictly
between resting entry and first target. Cancellations known at a close affect the
next bar, never retrospectively prevent an earlier valid fill.

No numerical threshold, entry/SL variant or exit allocation is changed to improve
outcomes. SourceEngine timing is fixed in an additive source_pdf_native module;
the previous source_pdf engine and tests remain byte-exact. New runner/policy use
a fresh output root; exact verified --resume-existing remains mandatory for any
completed native-policy segments. Compare old and new signals and complete all
40series/993575candles, independent cases, prefix/future-mutation and full QA.
Canonical TP40/30/30/SL/cost-adjusted TP1 BE unchanged; trade_entry_allowed=false,
only BACKTEST/SHADOW, no LIVE/private API.
