"""OKX-only nonfinancial input bridge; does not import or run strategy code."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256

from okx_qualification_data_v1 import DEST, PRODUCTS, DataInvalid


@dataclass(frozen=True)
class NativeBar:
    start: int
    end: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    product: str

    def observed(self, tf):
        return {
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "open_time": self.start,
            "completed_at": self.end,
            "known_at": self.end,
            "tf": tf,
            "product": self.product,
            "evidence": "Official historical OKX completed OHLC; modeled availability at close, not observed historical API latency",
        }


def load_native(product):
    if product not in PRODUCTS:
        raise DataInvalid("OKX_EXACT_PRODUCT_REQUIRED")
    report = json.loads((DEST / f"checkpoints/{product}.json").read_text())
    if report.get("state") != "CONTINUOUS_NATIVE_M15_VERIFIED":
        raise DataInvalid("NATIVE_DATA_NOT_COMPLETE")
    path = DEST / "data" / (product + ".M15.jsonl.gz")
    if sha256(path.read_bytes()).hexdigest() != report["stored_sha256"]:
        raise DataInvalid("PINNED_NATIVE_SOURCE_CHANGED")
    content = gzip.decompress(path.read_bytes())
    if sha256(content).hexdigest() != report["content_sha256"]:
        raise DataInvalid("NATIVE_CONTENT_CHANGED")
    bars = []
    for line in content.splitlines():
        row = json.loads(line)
        if row[8] != "1":
            raise DataInvalid("UNCOMPLETED_NATIVE_BAR")
        at = int(row[0]) // 1000
        bars.append(NativeBar(at, at + 900, *(Decimal(x) for x in row[1:5]), product))
    validate(bars, 900)
    return bars


def validate(bars, seconds):
    if not bars:
        raise DataInvalid("EMPTY_NATIVE_PREFIX")
    for i, bar in enumerate(bars):
        if (
            bar.start % seconds
            or bar.end - bar.start != seconds
            or i
            and (bar.start != bars[i - 1].end or bar.product != bars[i - 1].product)
        ):
            raise DataInvalid("GRID_GAP_OR_PRODUCT_MIX")
        values = (bar.open, bar.high, bar.low, bar.close)
        if (
            any(not v.is_finite() or v <= 0 for v in values)
            or not bar.low
            <= min(bar.open, bar.close)
            <= max(bar.open, bar.close)
            <= bar.high
        ):
            raise DataInvalid("INVALID_NATIVE_OHLC")


def aggregate(bars, seconds):
    if seconds not in (3600, 14400, 86400):
        raise DataInvalid("UNREGISTERED_DERIVATION_TIMEFRAME")
    validate(bars, 900)
    groups = {}
    for bar in bars:
        groups.setdefault(bar.start // seconds * seconds, []).append(bar)
    derived, omitted = [], []
    for at, group in sorted(groups.items()):
        if (
            len(group) != seconds // 900
            or group[0].start != at
            or group[-1].end != at + seconds
        ):
            omitted.append(at)
            continue
        derived.append(
            NativeBar(
                at,
                at + seconds,
                group[0].open,
                max(b.high for b in group),
                min(b.low for b in group),
                group[-1].close,
                group[0].product,
            )
        )
    if derived:
        validate(derived, seconds)
    return derived, omitted


def visible_prefix(bars, decision_at):
    return [b for b in bars if b.end <= decision_at]


def private_or_financial_transport(*args, **kwargs):
    raise DataInvalid("STAGE_A_FORBIDS_PRIVATE_ORDERS_AND_FINANCIAL_EVALUATION")
