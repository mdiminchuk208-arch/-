# Phase 1.4.2 v0.4.2 recheck

- Source rule rechecked: completed SFP -> lower timeframe -> BOS -> only then search entry.
- Source rule added: SFP becomes irrelevant after a candle body close beyond pattern min/max (`[SW.BAND]12. Индикаторы.pdf`, p.13).
- No wick-based invalidation was invented: invalidation is body-close based.
- SFP extreme uses completed sweep-candle high/low as a declared TECHNICAL_NORMALIZATION.
- Finite BOS wait window remains BACKTEST_PARAMETER; no source duration is claimed.
- Right-censoring remains separate from expiry.
- BOS after invalidation cannot confirm a candidate; same-timestamp tie is conservatively invalidated.
- Shared same-BOS links are clustered into one opportunity and preserved as multiple contexts for audit.
- Actual trade entry remains intentionally blocked.
- Real-market OB autovalidation remains `BLOCKED_PENDING_CONTEXT`.
