# Validation and exposure protocol

```json
{
  "rule_id": "M3_VALIDATION",
  "development": {
    "symbols": [
      "BTCUSDT",
      "ETHUSDT"
    ],
    "exchange": "BYBIT",
    "warmup_start": "2022-01-01T00:00:00+00:00",
    "interval": [
      "2023-01-01T00:00:00+00:00",
      "2025-12-05T23:30:00+00:00"
    ],
    "status": "EXPOSED_NOT_OOS"
  },
  "robustness": {
    "calendar_partitions": [
      2023,
      2024,
      2025
    ],
    "cross_classifications": [
      "symbol",
      "direction",
      "family",
      "setup_tf",
      "causal_market_state"
    ],
    "cost_multipliers": [
      "0.5",
      "1",
      "2"
    ],
    "independence_claim": false,
    "threshold_selection": false,
    "partition_boundary": "Exclude decisions or observation intervals crossing partition boundaries; censored/unresolved shown separately, not assigned zero"
  },
  "available_untouched_OOS": null,
  "current_OOS_gate": "STOP_NO_PRISTINE_OOS",
  "prospective_OOS": {
    "symbols": [
      "BTCUSDT",
      "ETHUSDT"
    ],
    "exchange": "BYBIT",
    "contract": "USDT_LINEAR_PERPETUAL",
    "TFs": [
      15,
      60,
      240,
      1440
    ],
    "start_rule": "Provisional plan only: first UTC D1 OPEN strictly after MAX(complete implementation pre-outcome freeze commit committer timestamp, append-only OOS registration commit committer timestamp). This contract-core design freeze alone cannot start the OOS clock. Register complete code/spec/data/protocol hashes and resolved start/end before first observation; missed preregistration/embargo => STOP, no post-outcome window shift",
    "end_rule": "start plus365 UTC days, exclusive",
    "window_reason": "Fixed four-season calendar evaluation commitment before outcomes, not an entry parameter",
    "acquisition": "Public completed M15 bars; derive contiguous UTC H1/H4/D1; no privateAPI/orders; metadata epoch announcements archived with publication known_at",
    "embargo": "Before locked end, no candidate signals, positions, trade labels or equity read, including inference from raw prices. Raw access only logged integrity-only script/role with no strategy-state access: hash/continuity/metadata checks. No interim optimization, early stopping, extension or relabeling after outcome",
    "warmup": "Exactly365 days pre-start completed bars for state warmup; no pre-start orders/outcomes. Prefix-only state reset/reservation ledger at OOS start",
    "warmup_current_state": "UNAVAILABLE_CONTIGUOUS: local Bybit public ends2025-12-05, native starts2026-01-25 and ends2026-09-22. Public gap filling needs independent evidence before registration; no interpolation/pretended ready prefix",
    "training_leakage": "No overlapping underlying OOS candles in development; hashes/copies/content periods checked; no carried development order or position",
    "readiness": "UNESTABLISHED_FUTURE_PLAN_NOT_EXISTING_PRISTINE_DATA",
    "missing_data": "No interpolation; gaps/instrument/metadata ambiguity => WAIT and unqualified-OOS report; do not shift window post hoc"
  },
  "qualification": "After separate authorization: fixed-spec development financial run, robustness, then locked untouched OOS; positive net ex-funding/PF>1 across declared model and stress reported, dependence-aware uncertainty and concentration disclosed. No production on reused TEST or subgroup alone; funding/actual execution evidence required for exchange-realism claim.",
  "implementation_scope": "NONFINANCIAL_CONTRACT_CORE; historical family-event adapter/full case runner not implemented in this gate",
  "first_v3_financial_backtest_ready": false,
  "first_financial_STOP_reasons": [
    "HISTORICAL_EVENT_ADAPTER_NOT_IMPLEMENTED",
    "NO_VERIFIED_HISTORICAL_TICK_EPOCHS"
  ],
  "production_candidate": null,
  "PAPER_enabled": false,
  "LIVE_enabled": false,
  "trade_entry_allowed": false
}
```

All local native/public/derived histories and source aliases are inventoried by hashes, underlying series, timestamps and prior research use. Renaming TEST, recompressing or aggregating candles does not restore independence. The future registration resolves the frozen-commit UTC boundary before its first observation. A changed implementation gets a new freeze and new OOS window; it must not reuse this window as untouched after any result inspection.
