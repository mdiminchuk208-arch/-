from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from crypto_bot.data.models import MarketCandle


DATASET_MANIFEST_SCHEMA = "crypto-bot.dataset-manifest.v1"


@dataclass(frozen=True)
class DatasetManifest:
    schema: str
    dataset_id: str
    exchange: str
    symbol: str
    interval: str
    interval_ms: int
    row_count: int
    first_open_time_ms: int | None
    last_open_time_ms: int | None
    closed_only: bool
    content_sha256: str
    source: str
    requested_start_ms: int | None = None
    requested_end_ms: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _stable_number(value: float | None) -> str | None:
    if value is None:
        return None
    # Round-trip-safe representation for Python binary64. This makes the
    # identity deterministic across JSON writers and independent of locale.
    return format(value, ".17g")


def canonical_candle_record(candle: MarketCandle) -> list[object]:
    return [
        candle.exchange,
        candle.symbol,
        candle.interval,
        candle.open_time_ms,
        _stable_number(candle.open),
        _stable_number(candle.high),
        _stable_number(candle.low),
        _stable_number(candle.close),
        _stable_number(candle.volume_base),
        _stable_number(candle.turnover_quote),
        candle.is_closed,
    ]


def candle_content_sha256(candles: Iterable[MarketCandle]) -> str:
    rows = sorted(candles, key=lambda candle: candle.open_time_ms)
    digest = hashlib.sha256()
    for candle in rows:
        encoded = json.dumps(
            canonical_candle_record(candle),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
    return digest.hexdigest()


def build_dataset_manifest(
    candles: Iterable[MarketCandle],
    *,
    interval_ms: int,
    source: str,
    requested_start_ms: int | None = None,
    requested_end_ms: int | None = None,
) -> DatasetManifest:
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")
    if not source.strip():
        raise ValueError("source must be non-empty")

    rows = sorted(candles, key=lambda candle: candle.open_time_ms)
    if not rows:
        raise ValueError("cannot build a dataset manifest for an empty candle series")

    identity = (rows[0].exchange, rows[0].symbol, rows[0].interval)
    for candle in rows:
        if (candle.exchange, candle.symbol, candle.interval) != identity:
            raise ValueError("dataset manifest cannot mix exchange/symbol/interval identities")

    content_hash = candle_content_sha256(rows)
    base = {
        "schema": DATASET_MANIFEST_SCHEMA,
        "exchange": identity[0],
        "symbol": identity[1],
        "interval": identity[2],
        "interval_ms": interval_ms,
        "row_count": len(rows),
        "first_open_time_ms": rows[0].open_time_ms,
        "last_open_time_ms": rows[-1].open_time_ms,
        "closed_only": all(candle.is_closed for candle in rows),
        "content_sha256": content_hash,
        "source": source,
        "requested_start_ms": requested_start_ms,
        "requested_end_ms": requested_end_ms,
    }
    dataset_id = hashlib.sha256(
        json.dumps(base, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return DatasetManifest(dataset_id=dataset_id, **base)


def write_dataset_manifest(manifest: DatasetManifest, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(manifest.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


def read_dataset_manifest(path: str | Path) -> DatasetManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != DATASET_MANIFEST_SCHEMA:
        raise ValueError(f"unsupported dataset manifest schema: {payload.get('schema')!r}")
    return DatasetManifest(**payload)
