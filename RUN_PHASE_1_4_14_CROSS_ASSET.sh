#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
export PYTHONPATH=src

echo "============================================================"
echo "Crypto Bot Phase 1.4.14 - Cross-Asset Validation"
echo "============================================================"

echo "[1/4] Running unit tests..."
python -m unittest discover -s tests -q || exit 1

echo "[2/4] Compile check..."
python -B -m compileall -q src scripts tests || exit 1

echo "[3/4] Fetching 240 days of Bybit public data for the 10-symbol basket..."
python scripts/fetch_bybit_mtf_history.py \
  --symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT DOGEUSDT ADAUSDT LINKUSDT AVAXUSDT LTCUSDT \
  --intervals 5 15 60 240 --days 240 || \
  echo "NOTE: fetch reported REVIEW REQUIRED. The analyzer will still perform strict input QA."

echo "[4/4] Running cross-asset robustness audit..."
python scripts/analyze_cross_asset_robustness.py \
  --symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT BNBUSDT DOGEUSDT ADAUSDT LINKUSDT AVAXUSDT LTCUSDT \
  --evaluation-days 240 --suffix-days 60 --stabilization-days 7 --analysis-warmup-days 0
code=$?

echo "Report: data/reports/phase1_4_14/cross_asset_240d/summary.json"
if [ "$code" -eq 0 ]; then
  echo "RESULT: CROSS-ASSET GATE CLOSED"
else
  echo "RESULT: CROSS-ASSET GATE REMAINS OPEN. Inspect summary.json for missing/failed symbols."
fi
exit "$code"
