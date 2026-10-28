BEGIN;

CREATE TABLE IF NOT EXISTS engine_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_created_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    payload JSONB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    CONSTRAINT engine_events_event_id_nonempty CHECK (length(btrim(event_id)) > 0),
    CONSTRAINT engine_events_event_type_nonempty CHECK (length(btrim(event_type)) > 0),
    CONSTRAINT engine_events_payload_object CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT engine_events_payload_sha256_hex CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT engine_events_received_not_before_source CHECK (received_at >= source_created_at)
);

CREATE INDEX IF NOT EXISTS idx_engine_events_type_created
    ON engine_events(event_type, source_created_at, event_id);

CREATE INDEX IF NOT EXISTS idx_engine_events_received
    ON engine_events(received_at, event_id);

CREATE INDEX IF NOT EXISTS idx_engine_events_payload_gin
    ON engine_events USING GIN(payload jsonb_path_ops);

COMMENT ON TABLE engine_events IS
    'Append-only idempotent Strategy Engine event store. event_id is the transport identity; receivers must validate the envelope before insert.';
COMMENT ON COLUMN engine_events.payload_sha256 IS
    'Application-computed SHA-256 of canonical payload JSON. Used to reject event_id collisions with a different payload.';

-- Append-only protection at the database boundary. The application may insert
-- an event once or verify an identical existing row, but it must never mutate
-- a previously accepted Strategy Engine event in place.
CREATE OR REPLACE FUNCTION reject_engine_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'engine_events is append-only; % is not allowed', TG_OP
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS engine_events_no_update ON engine_events;
CREATE TRIGGER engine_events_no_update
BEFORE UPDATE ON engine_events
FOR EACH ROW EXECUTE FUNCTION reject_engine_event_mutation();

DROP TRIGGER IF EXISTS engine_events_no_delete ON engine_events;
CREATE TRIGGER engine_events_no_delete
BEFORE DELETE ON engine_events
FOR EACH ROW EXECUTE FUNCTION reject_engine_event_mutation();

-- Receiver acknowledgements are operational state and therefore live in a
-- separate mutable table instead of altering the immutable event itself.
CREATE TABLE IF NOT EXISTS engine_event_receipts (
    event_id TEXT PRIMARY KEY REFERENCES engine_events(event_id) ON DELETE RESTRICT,
    first_received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    last_received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    receive_count BIGINT NOT NULL DEFAULT 1,
    CONSTRAINT engine_event_receipts_count_positive CHECK (receive_count > 0),
    CONSTRAINT engine_event_receipts_time_order CHECK (last_received_at >= first_received_at)
);

COMMENT ON TABLE engine_event_receipts IS
    'Operational idempotency receipts for repeated delivery attempts of immutable engine events.';

COMMIT;
