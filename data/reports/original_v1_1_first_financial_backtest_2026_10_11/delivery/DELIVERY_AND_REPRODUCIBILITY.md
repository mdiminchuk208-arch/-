# Immutable first result delivery

The PRE-OUTCOME producer/protocol/configuration remain byte-identical to commit
`008b80d97cf008e14af94d4271c12188257a926f`. This delivery utility only restores
CSV bytes; it imports no strategy, prices, financial simulator or exchange client.
No second financial variant or admission change is introduced.

Both `result/all_candidates.csv` and `result/all_WAIT.csv` are117,710,997bytes,
above GitHub's100MiB per-file limit. Their original local files are preserved.
Git publishes deterministic gzip copies in the same result directory. Both the
original and compressed SHA256 values are included in `result_manifest.json`.
`csv_archives_receipt.json` records verified decompressed equality. The local
`.git/info/exclude` applies only to these two materialized CSV copies; no other
original artifact is excluded.

After a fresh checkout, restore the two exact CSV files before immutable resume:

```sh
python data/reports/original_v1_1_first_financial_backtest_2026_10_11/delivery/restore_csv_archives.py
python scripts/run_original_v1_1_first_financial_backtest.py --resume-existing
```

Existing matching exports are retained; a different existing file or bad archive
fails verification. Missing files are restored via a temporary file and verified
against the sealed SHA256 before replacement. `--verify-only` verifies archives
without materializing missing exports. Restoration is not a financial calculation.

Resume is a read-only replay of the exact registered decisions/metrics, comparing
all frozen result hashes and raw/evidence records. It does not run another variant
or rewrite results. Original `--run`, `--prepare`, `--qa`, and `--seal` refuse
replacement of existing artifacts. Keep first-result producer and protocol frozen.

STOP after delivery. Evidence-blocked zero exposure is not zero strategy edge;
historical fills/exit paths/shared sizing were not exercised. No new labels,
overlays, optimization, LIVE/private API or trading authorization.
