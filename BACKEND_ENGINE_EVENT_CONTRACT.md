# Strategy Engine -> Backend Event Ingestion Contract

## Status

This document defines the backend persistence boundary for Strategy Engine events.

It does **not** define an HTTP path, web framework, host name or deployment URL. The Platform/Backend implementation must choose those separately and configure the engine outbox delivery worker explicitly.

The contract is fail-closed and diagnostic-only while PURE SOURCE remains non-executable.

## 1. Transport envelope

The delivery worker sends one JSON object:

```json
{
  "event_id": "<stable event fingerprint>",
  "event_type": "<schema/event type>",
  "created_at": "<timezone-aware ISO-8601 timestamp>",
  "payload": { }
}
```

Receiver validation is implemented in:

`src/crypto_bot/integration/receiver.py`

Before any database write, the backend must call the equivalent of:

```python
validate_engine_event_envelope(request_json)
```

Mandatory validation:

- exactly `event_id`, `event_type`, `created_at`, `payload` at envelope level;
- `event_id` and `event_type` non-empty;
- `created_at` timezone-aware;
- `payload` is a JSON object;
- when payload contains `event_id`, it equals envelope `event_id`;
- when payload contains `schema`, it equals envelope `event_type`;
- **no `trade_entry_allowed=true` anywhere recursively inside payload**.

The recursive execution-permission check is mandatory even for nested diagnostic artifacts.

## 2. Idempotency

The sender includes:

- `Idempotency-Key: <event_id>`
- `X-Crypto-Bot-Event-Id: <event_id>`
- `X-Crypto-Bot-Event-Type: <event_type>`

The database identity is still the JSON envelope `event_id`; headers are supporting transport metadata and must not override the body.

The backend must canonicalize the validated `payload` with deterministic JSON serialization and compute SHA-256 before insert.

Recommended canonical form:

```text
UTF-8
sort_keys=true
ensure_ascii=false
separators=(',', ':')
```

Store the resulting lowercase 64-character hex digest in `engine_events.payload_sha256`.

## 3. PostgreSQL schema

Migration:

`deploy/postgres/001_engine_events.sql`

Core table:

```text
engine_events
  event_id            TEXT PRIMARY KEY
  event_type          TEXT NOT NULL
  source_created_at   TIMESTAMPTZ NOT NULL
  received_at         TIMESTAMPTZ NOT NULL
  payload             JSONB NOT NULL
  payload_sha256      TEXT NOT NULL
```

`engine_events` is append-only. Database triggers reject UPDATE and DELETE.

Repeated delivery metadata is stored separately in:

```text
engine_event_receipts
  event_id            TEXT PRIMARY KEY/FK
  first_received_at   TIMESTAMPTZ
  last_received_at    TIMESTAMPTZ
  receive_count       BIGINT
```

## 4. Required transaction algorithm

For every validated envelope, execute one database transaction.

### Case A — first delivery

1. Compute canonical `payload_sha256`.
2. Attempt `INSERT` into `engine_events`.
3. Insert initial `engine_event_receipts` row.
4. Commit.
5. Return a 2xx response.

### Case B — exact duplicate

When `event_id` already exists:

1. Read the existing row under the transaction.
2. Verify all immutable identity fields:
   - `event_type` matches;
   - `source_created_at` matches;
   - `payload_sha256` matches;
   - stored JSON payload is semantically equal to validated payload.
3. Increment `engine_event_receipts.receive_count` and update only `last_received_at`.
4. Commit.
5. Return a 2xx response.

An exact duplicate is successful idempotent delivery, not an error.

### Case C — event_id collision

If an existing `event_id` has different immutable content:

- rollback;
- do **not** modify the old event;
- do **not** increment a successful receipt;
- emit a high-severity system/audit event;
- return a non-2xx response.

The sender will retain the original event as pending because its outbox acknowledges only 2xx responses.

## 5. Suggested SQL transaction pattern

The application may use `INSERT ... ON CONFLICT DO NOTHING`, then inspect the canonical existing row.

Pseudo-SQL:

```sql
BEGIN;

INSERT INTO engine_events(
    event_id,
    event_type,
    source_created_at,
    payload,
    payload_sha256
)
VALUES ($1, $2, $3, $4::jsonb, $5)
ON CONFLICT (event_id) DO NOTHING;

SELECT event_type, source_created_at, payload, payload_sha256
FROM engine_events
WHERE event_id = $1
FOR SHARE;

-- Application compares immutable values here.
-- If mismatch: ROLLBACK and return non-2xx.

INSERT INTO engine_event_receipts(event_id)
VALUES ($1)
ON CONFLICT (event_id) DO UPDATE
SET last_received_at = clock_timestamp(),
    receive_count = engine_event_receipts.receive_count + 1;

COMMIT;
```

Do not use an UPSERT that overwrites `engine_events.payload`, timestamps or hashes.

## 6. Response semantics expected by sender

The existing delivery worker treats:

- **2xx** -> successfully acknowledged; outbox event is marked delivered;
- **non-2xx** -> not acknowledged; event remains pending;
- network/transport exception -> not acknowledged; event remains pending.

Therefore backend responses should follow:

- first accepted event: 200/201/202/204;
- exact duplicate accepted: 200/204;
- malformed envelope: 400-class non-2xx;
- authentication failure: 401/403;
- event-id collision: 409 is recommended;
- temporary database/backend failure: 5xx.

The backend must not return 2xx for a collision or partially failed transaction.

## 7. Security boundary

The generic sender supports optional bearer authentication and requires HTTPS outside explicitly enabled localhost development.

Backend requirements:

- TLS in production;
- authentication configured outside source code/secrets repository;
- request body size limit;
- JSON parser depth/resource limits where supported;
- access/audit logs must not expose authentication secrets;
- rate limiting should not break idempotency semantics;
- database user for ingestion should have only the permissions needed for inserts/receipt updates and reads required for collision verification.

No OKX private API key belongs in this ingestion path.

## 8. Platform read model

The UI/backend may derive read models from `engine_events`, but the raw event table remains immutable.

Minimum read-model fields should retain:

- event ID/type;
- symbol/timeframe where present;
- object/setup/physical-idea IDs;
- formation/known/confirmed/invalidated timestamps where present;
- SOURCE rule references;
- SOURCE branch identity;
- unresolved/rejection reasons;
- engine version/git commit;
- dataset identity;
- diagnostic artifact identity;
- `trade_entry_allowed=false`.

A Platform UI must not invent an executable signal when the raw engine event does not contain source-permitted geometry or when the project remains fail-closed.

## 9. Current boundary

This event-ingestion contract is ready for the separate Platform/Backend implementation to consume.

Still intentionally absent here:

- a hardcoded backend URL/path;
- private exchange API;
- LIVE order execution;
- any mechanism that converts PROJECT risk PASS into SOURCE truth;
- any mechanism that resolves `NOT_IDENTIFIABLE` by optimization or historical PnL.
