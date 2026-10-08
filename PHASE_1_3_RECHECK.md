# Phase 1.3 v0.3.1 — recheck report

This build supersedes v0.3.0.

## Fixed during recheck

1. Post-BOS CONF cannot use pre-BOS swings. New structure must form causally after BOS.
2. OB without IMB is marked `IMB_UNRESOLVED` and is not trade-eligible until the source ambiguity is explicitly resolved/tested.
3. Bybit kline/instrument response identity is validated; `symbolType` and `marketRegion` are parsed conservatively.
4. Non-finite OHLC/risk values and invalid volume/turnover are rejected.
5. Data QA blocks mixed exchange/symbol/interval series.
6. Strategy candle timestamps must be timezone-aware.
7. Added causal-prefix regression coverage against look-ahead.
8. Package, project and HTTP User-Agent versions are synchronized to 0.3.1.

## Verification

- Unit tests: 64/64 PASS
- `compileall`: PASS
- `config/source_rules.json`: valid JSON
- Real-market OB auto-validation remains intentionally blocked pending HTF POI, structural impulse/trend context, and numeric aggressive-impulse normalization.
