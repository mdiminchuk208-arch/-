from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crypto_bot.data.models import HistoricalFetch, InstrumentInfo, MarketCandle


OKX_MAINNET = "https://www.okx.com"

# Keep the repository's existing canonical interval vocabulary at the adapter
# boundary. OKX's UTC daily bar is used deliberately so D1 does not inherit the
# exchange's UTC+8 daily session boundary.
OKX_BAR_BY_INTERVAL: dict[str, str] = {
    "1": "1m",
    "3": "3m",
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "1H",
    "120": "2H",
    "240": "4H",
    "360": "6Hutc",
    "720": "12Hutc",
    "D": "1Dutc",
}
SUPPORTED_FIXED_INTERVAL_MS: dict[str, int] = {
    "1": 60_000,
    "3": 3 * 60_000,
    "5": 5 * 60_000,
    "15": 15 * 60_000,
    "30": 30 * 60_000,
    "60": 60 * 60_000,
    "120": 120 * 60_000,
    "240": 240 * 60_000,
    "360": 360 * 60_000,
    "720": 720 * 60_000,
    "D": 24 * 60 * 60_000,
}


class OKXAPIError(RuntimeError):
    pass


Transport = Callable[[str], Mapping[str, Any]]


def _default_transport(url: str) -> Mapping[str, Any]:
    request = Request(url, headers={"User-Agent": "crypto-bot-okx-public/0.1"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # stable project error for CLI/tests
        raise OKXAPIError(f"OKX request failed: {exc}") from exc


@dataclass(frozen=True)
class OKXKlinePage:
    server_time_ms: int
    candles: tuple[MarketCandle, ...]


class OKXPublicClient:
    """Minimal unauthenticated OKX V5 public market-data client.

    The adapter is deliberately limited to public data. It does not contain
    private API authentication or order methods. The default instrument type is
    USDT perpetual swaps (``SWAP``), matching the project's production target.

    ``base_url`` is configurable because OKX documents regional API domains for
    some registrations. Public data callers can inject the appropriate domain
    without changing any strategy code.
    """

    def __init__(
        self,
        *,
        base_url: str = OKX_MAINNET,
        transport: Transport | None = None,
        inst_type: str = "SWAP",
        request_delay_s: float = 0.05,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport or _default_transport
        self.inst_type = inst_type.upper()
        self.request_delay_s = max(0.0, request_delay_s)

    @staticmethod
    def interval_ms(interval: str) -> int:
        if interval in {"W", "M"}:
            raise ValueError(
                "Weekly/monthly candles require explicit session-boundary validation "
                "and are not supported by fixed-interval QA yet"
            )
        try:
            return SUPPORTED_FIXED_INTERVAL_MS[interval]
        except KeyError as exc:
            raise ValueError(f"Unsupported fixed OKX interval: {interval}") from exc

    @staticmethod
    def api_bar(interval: str) -> str:
        try:
            return OKX_BAR_BY_INTERVAL[interval]
        except KeyError as exc:
            raise ValueError(f"Unsupported OKX interval: {interval}") from exc

    def _get(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        payload = self.transport(url)
        code = str(payload.get("code", ""))
        if code != "0":
            raise OKXAPIError(f"OKX API error {code or 'UNKNOWN'}: {payload.get('msg', 'unknown error')}")
        data = payload.get("data")
        if not isinstance(data, list):
            raise OKXAPIError("Unexpected OKX response: data must be a list")
        return payload

    def get_server_time_ms(self) -> int:
        payload = self._get("/api/v5/public/time", {})
        rows = payload["data"]
        if not rows or not isinstance(rows[0], Mapping):
            raise OKXAPIError("OKX server-time response did not contain a timestamp")
        value = rows[0].get("ts")
        if value in (None, ""):
            raise OKXAPIError("OKX server-time response did not contain ts")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise OKXAPIError(f"Invalid OKX server timestamp: {value!r}") from exc

    def _parse_kline_page(
        self,
        *,
        symbol: str,
        interval: str,
        payload: Mapping[str, Any],
        server_time_ms: int,
        closed_only: bool,
    ) -> OKXKlinePage:
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise OKXAPIError("Unexpected OKX kline response: data must be a list")

        candles: list[MarketCandle] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 9:
                raise OKXAPIError("Unexpected OKX kline row shape")
            try:
                confirm = str(row[8])
                if confirm not in {"0", "1"}:
                    raise ValueError(f"invalid confirm flag {confirm!r}")
                is_closed = confirm == "1"
                if closed_only and not is_closed:
                    continue
                candle = MarketCandle(
                    exchange="OKX",
                    symbol=symbol.upper(),
                    interval=interval,
                    open_time_ms=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    # For FUTURES/SWAP, OKX documents vol as contracts, volCcy as
                    # base-currency volume and volCcyQuote as quote-currency volume.
                    volume_base=float(row[6]),
                    turnover_quote=float(row[7]),
                    is_closed=is_closed,
                )
            except (TypeError, ValueError) as exc:
                raise OKXAPIError(f"Invalid OKX kline row for {symbol.upper()}: {row!r}: {exc}") from exc
            candles.append(candle)

        candles.sort(key=lambda candle: candle.open_time_ms)
        return OKXKlinePage(server_time_ms=server_time_ms, candles=tuple(candles))

    def get_kline_page(
        self,
        *,
        symbol: str,
        interval: str,
        after_ms: int | None = None,
        before_ms: int | None = None,
        limit: int = 300,
        closed_only: bool = True,
    ) -> OKXKlinePage:
        self.interval_ms(interval)
        bar = self.api_bar(interval)
        if not 1 <= limit <= 300:
            raise ValueError("OKX history-candles limit must be within [1, 300]")
        if after_ms is not None and before_ms is not None and before_ms >= after_ms:
            # OKX defines `after` as older-than and `before` as newer-than. When
            # both are supplied, the requested window must therefore be non-empty.
            raise ValueError("before_ms must be less than after_ms for OKX history pagination")

        server_time_ms = self.get_server_time_ms()
        payload = self._get(
            "/api/v5/market/history-candles",
            {
                "instId": symbol.upper(),
                "after": after_ms,
                "before": before_ms,
                "bar": bar,
                "limit": limit,
            },
        )
        return self._parse_kline_page(
            symbol=symbol,
            interval=interval,
            payload=payload,
            server_time_ms=server_time_ms,
            closed_only=closed_only,
        )

    def fetch_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 300,
        closed_only: bool = True,
        max_pages: int = 20_000,
    ) -> HistoricalFetch:
        if start_ms > end_ms:
            raise ValueError("start_ms cannot be greater than end_ms")
        self.interval_ms(interval)
        bar = self.api_bar(interval)
        if not 1 <= limit <= 300:
            raise ValueError("OKX history-candles limit must be within [1, 300]")

        # One exchange clock observation per fetch. Candle closure itself is
        # exchange-authoritative via OKX's `confirm` field.
        server_time_ms = self.get_server_time_ms()
        all_by_open_time: dict[int, MarketCandle] = {}
        # `after` returns records earlier than the requested timestamp. +1 keeps
        # a candle exactly at end_ms eligible for the first page.
        current_after = end_ms + 1

        for _ in range(max_pages):
            payload = self._get(
                "/api/v5/market/history-candles",
                {
                    "instId": symbol.upper(),
                    "after": current_after,
                    "bar": bar,
                    "limit": limit,
                },
            )
            page = self._parse_kline_page(
                symbol=symbol,
                interval=interval,
                payload=payload,
                server_time_ms=server_time_ms,
                # Pagination must observe unfinished rows too, then apply the
                # closed-only filter while storing them.
                closed_only=False,
            )
            if not page.candles:
                break

            for candle in page.candles:
                if start_ms <= candle.open_time_ms <= end_ms and (not closed_only or candle.is_closed):
                    all_by_open_time[candle.open_time_ms] = candle

            earliest = page.candles[0].open_time_ms
            if earliest <= start_ms:
                break
            next_after = earliest
            if next_after >= current_after:
                raise OKXAPIError("Kline pagination did not move backward")
            current_after = next_after
            if self.request_delay_s:
                time.sleep(self.request_delay_s)
        else:
            raise OKXAPIError("max_pages reached while downloading OKX klines")

        candles = tuple(sorted(all_by_open_time.values(), key=lambda candle: candle.open_time_ms))
        return HistoricalFetch(
            exchange="OKX",
            symbol=symbol.upper(),
            interval=interval,
            requested_start_ms=start_ms,
            requested_end_ms=end_ms,
            server_time_ms=server_time_ms,
            candles=candles,
        )

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        payload = self._get(
            "/api/v5/public/instruments",
            {"instType": self.inst_type, "instId": symbol.upper()},
        )
        rows = payload["data"]
        row = next(
            (
                item
                for item in rows
                if isinstance(item, Mapping) and str(item.get("instId", "")).upper() == symbol.upper()
            ),
            None,
        )
        if row is None:
            raise OKXAPIError(f"Instrument not found in OKX response: {symbol.upper()}")

        response_inst_type = str(row.get("instType", "")).upper()
        if response_inst_type and response_inst_type != self.inst_type:
            raise OKXAPIError(
                f"OKX instrument type mismatch: requested {self.inst_type}, got {response_inst_type}"
            )

        def optional_float(value: Any) -> float | None:
            if value in (None, ""):
                return None
            return float(value)

        def optional_int(value: Any) -> int | None:
            if value in (None, "", "0", 0):
                return None
            return int(value)

        inst_family = str(row.get("instFamily", ""))
        family_parts = inst_family.split("-") if inst_family else []
        base_coin = str(row.get("baseCcy", "")) or str(row.get("ctValCcy", ""))
        quote_coin = str(row.get("quoteCcy", ""))
        if not base_coin and family_parts:
            base_coin = family_parts[0]
        if not quote_coin and len(family_parts) >= 2:
            quote_coin = family_parts[1]
        settle_coin = str(row.get("settleCcy", ""))

        contract_type = ""
        if response_inst_type == "SWAP" and str(row.get("ctType", "")).lower() == "linear":
            contract_type = "LinearPerpetual"

        return InstrumentInfo(
            exchange="OKX",
            symbol=str(row.get("instId", symbol.upper())),
            contract_type=contract_type,
            symbol_type="",
            market_region="",
            base_coin=base_coin,
            quote_coin=quote_coin,
            settle_coin=settle_coin,
            status=str(row.get("state", "")),
            launch_time_ms=optional_int(row.get("listTime")),
            delivery_time_ms=optional_int(row.get("expTime")),
            tick_size=optional_float(row.get("tickSz")),
            qty_step=optional_float(row.get("lotSz")),
            min_order_qty=optional_float(row.get("minSz")),
            max_order_qty=optional_float(row.get("maxLmtSz")),
            max_market_order_qty=optional_float(row.get("maxMktSz")),
            min_notional_value=None,
            funding_interval_min=None,
            max_leverage=None,
        )
