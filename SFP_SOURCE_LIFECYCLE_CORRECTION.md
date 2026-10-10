# Causal SFP validity / cancellation correction — 2026-10-10

This correction is registered before inspecting new trade outcomes. The full40
`c8263dd` detector is retained as the complete native candidate corpus. Qualification
and lifecycle are evaluated on ALL its candidates and ALL corresponding stored
native bars, independently of execution/Win/Loss. No quotes, stops, targets,
READY timestamps, source formation rules or risk/costs are fitted to results.

Two definite type/lifecycle errors were found in the candidate engine:

1. A BOS proof's `protected` is the broken level of the OLD opposite structure.
   It is not a new protected HL/LH in the incoming direction. Without a genuinely
   confirmed new structure, freezing that broken price as a new SFP thesis adds
   an uncited LTF cancellation gate. No new CONF gate is added: SFP has its real
   native pattern and entry POI; BOS stays confirmation evidence, not a fabricated
   new protected key. SOURCE_RULE SW5 structure types / SW9 p13 / DOC16 P0075–87.
2. Synthetic SFP waiting contexts were not retired on native pattern body failure
   BEFORE their later READY. A reclaimed price weeks later cannot resurrect an
   already invalidated SFP. SW12 p13 explicitly invalidates the pattern when a
   body closes beyond its wick; it is also the stated source ATR manual exit.

Final pipeline: verified full40 native candidates → causal SFP qualification at
READY → global physical IDs → fixed selection → independent execution. Preserve
all rejected candidates and the precise past invalidation proof. Read only closed
native candles. A future failure must never reject an earlier READY or prevent a
fill before its CLOSE. No arbitrary age limit and no generic later LTF state gate
in the primary cancellation cohort. Pending source SFP cancels at the earliest
entry-POI native body failure or native SFP pattern body failure. Filled cases
retain their original SL/FTA/ATR source exit; the cancellation cannot erase them.

The strict comparison retains the original conservative candidate-engine events,
including its former BOS-level interpretation, explicitly as a control. The
original d46646f nine orders and strict0fills/0closures remain byte-identical;
their separate fixed-quote cancellation audit is unaffected (none is this SFP
delivery exception). Every cohort keeps identical qualification and physical IDs.

The reuse receipt checks all detector/source/code/data/segment SHA hashes; final
source gates and lifecycles have their own locked implementation and native
timestamps. Engine root and its provisional context execution are untouched.
QA covers pre-READY invalidation, irreversible invalidity, future CLOSE causality,
wick-only versus body failure, former broken level, actual quote touch/entry,
unchanged source trade fields, full prefix/future mutation and accounting.
Only BACKTEST/SHADOW, `trade_entry_allowed=false`; no LIVE/private API.
