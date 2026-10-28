# OKX PURE SOURCE Live Diagnostic — Runbook

## Scope and safety boundary

This service is a public-market-data diagnostic runtime only.

It does **not** contain private OKX credentials, does **not** place orders and does **not** grant financial execution permission. PURE SOURCE remains fail-closed with `trade_entry_allowed=false`.

The runtime path is:

`verified OKX history -> durable MTF state -> public closed-candle catch-up -> PURE SOURCE Stage 14/15 diagnostic replay -> durable outbox -> health receipt`

## 1. Prepare verified historical datasets

From the repository root:

```bash
python scripts/fetch_okx_mtf_history.py \
  --symbols BTC-USDT-SWAP \
  --intervals 5 15 60 240 D \
  --days 30 \
  --output-root data/history
```

The command must finish with healthy coverage/QA for every timeframe. Each CSV must have a matching `.manifest.json` file.

Optional offline diagnostic verification before live startup:

```bash
python scripts/run_okx_pure_source_diagnostic.py \
  --symbol BTC-USDT-SWAP \
  --intervals 5 15 60 240 D \
  --data-root data/history
```

Expected safety facts:

- `baseline_identifiability=NOT_IDENTIFIABLE` while that remains the authoritative SOURCE verdict;
- `trade_entry_allowed=false`;
- `financial_run=false`.

## 2. Local one-cycle smoke test

```bash
python scripts/run_okx_live_diagnostic_service.py \
  --symbol BTC-USDT-SWAP \
  --data-root data/history \
  --state-root data/runtime \
  --once
```

The process bootstraps only from verified persisted datasets, reconciles durable cursors, catches up public OKX closed candles without gaps, runs the diagnostic pipeline and writes:

```text
data/runtime/okx/BTC-USDT-SWAP/
  mtf.sqlite3
  cursors.json
  engine_outbox.sqlite3
  health.json
```

Check the health receipt:

```bash
python scripts/check_live_diagnostic_health.py \
  --health-file data/runtime/okx/BTC-USDT-SWAP/health.json \
  --max-age-seconds 120
```

Exit code `0` means the runtime is responsive. Exit code `2` means the receipt is missing, invalid, stale, STARTING or SAFE_MODE.

`DEGRADED` is responsive but requires investigation, for example when the durable backend outbox is accumulating undelivered events.

## 3. Docker Compose deployment

Historical data stays read-only inside the container. Runtime state uses a persistent named volume.

Build and start:

```bash
docker compose -f compose.live-diagnostic.yml up -d --build
```

Inspect:

```bash
docker compose -f compose.live-diagnostic.yml ps
docker compose -f compose.live-diagnostic.yml logs -f crypto-bot-live-diagnostic
```

Stop without deleting durable runtime state:

```bash
docker compose -f compose.live-diagnostic.yml down
```

Do **not** add `-v` unless the durable cursor/MTF/outbox state is intentionally being discarded and the restart procedure has been reviewed.

## 4. systemd deployment

Reference paths used by the unit:

- repository: `/opt/crypto-bot`
- virtual environment: `/opt/crypto-bot/.venv`
- verified history: `/opt/crypto-bot/data/history`
- writable runtime state: `/var/lib/crypto-bot`
- service account: `cryptobot`

Example host preparation:

```bash
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin cryptobot || true
sudo mkdir -p /opt/crypto-bot /var/lib/crypto-bot
sudo chown cryptobot:cryptobot /var/lib/crypto-bot

cd /opt/crypto-bot
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Copy/install the unit:

```bash
sudo cp deploy/systemd/crypto-bot-live-diagnostic.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now crypto-bot-live-diagnostic.service
```

Inspect:

```bash
systemctl status crypto-bot-live-diagnostic.service
journalctl -u crypto-bot-live-diagnostic.service -f
```

Health check:

```bash
/opt/crypto-bot/.venv/bin/python \
  /opt/crypto-bot/scripts/check_live_diagnostic_health.py \
  --health-file /var/lib/crypto-bot/okx/BTC-USDT-SWAP/health.json \
  --max-age-seconds 120
```

## 5. Restart/recovery contract

The service is designed for at-least-once recovery:

1. verified historical candles seed the durable MTF store idempotently;
2. durable cursor is reconciled against the persisted MTF store;
3. if the cursor is behind, exact stored candles can replay idempotently;
4. if the process was offline longer than one OKX page, polling paginates backwards until the durable cursor is reached;
5. any missing closed candle fails closed instead of silently skipping it;
6. cursor advances only after the candle is accepted by durable MTF state;
7. diagnostic events are fingerprinted and outbox insertion is idempotent.

A cursor that is ahead of durable MTF state is treated as corruption and fails closed.

## 6. Operational incidents

### `MARKET_DATA_STALE_<TF>` / SAFE_MODE

Do not repair this by manually moving cursors. Inspect OKX connectivity, host clock, logs and the last persisted candles. The runtime intentionally remains diagnostic-only and fail-closed.

### `ENGINE_OUTBOX_BACKLOG` / DEGRADED

The Strategy Engine side is producing durable diagnostic events faster than the backend handoff is acknowledging them. Preserve the outbox database. Investigate the future backend delivery worker/API rather than deleting pending events.

### catch-up gap detected

Do not skip the gap. Re-fetch/verify the affected historical interval and reconcile the durable state using an audited procedure. A silent continuity hole would invalidate causal replay.

### health file stale

A stale `health.json` normally means the service stopped completing successful cycles. Inspect the process/container and OKX public connectivity. Fatal cycles deliberately leave the last good receipt untouched so it becomes stale and external monitoring fails naturally.

## 7. Current non-goals

This deployment does not yet provide:

- private OKX API/order placement;
- LIVE trading;
- automatic resolution of unresolved PURE SOURCE semantics;
- PROJECT policy selection inside PURE SOURCE;
- TradingView as a production dependency.

Those boundaries must remain intact until separate project gates explicitly change them.
