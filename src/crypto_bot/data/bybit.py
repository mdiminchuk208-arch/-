from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crypto_bot.data.models import HistoricalFetch, InstrumentInfo, MarketCandle


BYBIT_MAINNET = "https://api.bybit.com"
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


class BybitAPIError(RuntimeError):
    pass


Transport = Callable[[str], Mapping[str, Any]]


def _default_transport(url: str) -> Mapping[str, Any]:
    request = Request(url, headers={"User-Agent": "crypto-bot-phase1/0.4.14"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # converted to a stable project error for CLI/tests
        raise BybitAPIError(f"Bybit request failed: {exc}") from exc


@dataclass(frozen=True)
class KlinePage:
    server_time_ms: int
    candles: tuple[MarketCandle, ...]


class BybitPublicClient:
    """
    Minimal unauthenticated Bybit V5 public market-data client.

    Phase 1.2 intentionally uses the Python standard library only so the user's
    current environment can run it without installing third-party packages.
    """

    def __init__(
        self,
        *,
        base_url: str = BYBIT_MAINNET,
        transport: Transport | None = None,
        category: str = "linear",
        request_delay_s: float = 0.05,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport or _default_transport
        self.category = category
        self.request_delay_s = max(0.0, request_delay_s)

    @staticmethod
    def interval_ms(interval: str) -> int:
        if interval in {"W", "M"}:
            raise ValueError("Weekly/monthly candles require exchange-session boundary validation and are not supported by fixed-interval QA yet")
        try:
            return SUPPORTED_FIXED_INTERVAL_MS[interval]
        except KeyError as exc:
            raise ValueError(f"Unsupported fixed Bybit interval: {interval}") from exc

    def _get(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        payload = self.transport(f"{self.base_url}{path}?{query}")
        ret_code = payload.get("retCode")
        if ret_code != 0:
            raise BybitAPIError(f"Bybit API error {ret_code}: {payload.get('retMsg', 'unknown error')}")
        return payload

    def get_server_time_ms(self) -> int:
        """Return Bybit server time from the public V5 time endpoint."""
        payload = self._get("/v5/market/time", {})
        result = payload.get("result", {})
        value = result.get("timeNano")
        if value not in (None, ""):
            # The official response labels this field timeNano; convert nanoseconds to ms.
            return int(value) // 1_000_000
        value = result.get("timeSecond")
        if value not in (None, ""):
            return int(value) * 1000
        return int(payload.get("time", int(time.time() * 1000)))

    def get_kline_page(
        self,
        *,
        symbol: str,
        interval: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int = 1000,
        closed_only: bool = True,
    ) -> KlinePage:
        interval_ms = self.interval_ms(interval)
        if not 1 <= limit <= 1000:
            raise ValueError("Bybit kline limit must be within [1, 1000]")
        if start_ms is not None and end_ms is not None and start_ms > end_ms:
            raise ValueError("start_ms cannot be greater than end_ms")

        payload = self._get(
            "/v5/market/kline",
            {
                "category": self.category,
                "symbol": symbol.upper(),
                "interval": interval,
                "start": start_ms,
                "end": end_ms,
                "limit": limit,
            },
        )
        server_time_ms = int(payload.get("time", int(time.time() * 1000)))
        result = payload.get("result", {})
        result_symbol = str(result.get("symbol", ""))
        result_category = str(result.get("category", ""))
        if result_symbol and result_symbol != symbol.upper():
            raise BybitAPIError(f"Bybit kline symbol mismatch: requested {symbol.upper()}, got {result_symbol}")
        if result_category and result_category != self.category:
            raise BybitAPIError(f"Bybit kline category mismatch: requested {self.category}, got {result_category}")
        rows = result.get("list", [])
        candles: list[MarketCandle] = []
        for row in rows:
            if len(row) < 7:
                raise BybitAPIError("Unexpected Bybit kline row shape")
            open_time_ms = int(row[0])
            is_closed = open_time_ms + interval_ms <= server_time_ms
            if closed_only and not is_closed:
                continue
            try:
                candle = MarketCandle(
                    exchange="BYBIT",
                    symbol=symbol.upper(),
                    interval=interval,
                    open_time_ms=open_time_ms,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume_base=float(row[5]),
                    turnover_quote=float(row[6]),
                    is_closed=is_closed,
                )
            except (TypeError, ValueError) as exc:
                raise BybitAPIError(f"Invalid Bybit kline row for {symbol.upper()}: {row!r}: {exc}") from exc
            candles.append(candle)
        # Bybit documents that rows are reverse-sorted by startTime. The project
        # normalizes history to ascending time before any strategy code sees it.
        candles.sort(key=lambda candle: candle.open_time_ms)
        return KlinePage(server_time_ms=server_time_ms, candles=tuple(candles))

    def fetch_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
        closed_only: bool = True,
        max_pages: int = 20_000,
    ) -> HistoricalFetch:
        if start_ms > end_ms:
            raise ValueError("start_ms cannot be greater than end_ms")
        self.interval_ms(interval)  # validate before requests

        all_by_open_time: dict[int, MarketCandle] = {}
        current_end = end_ms
        server_time_ms = int(time.time() * 1000)

        for _ in range(max_pages):
            page = self.get_kline_page(
                symbol=symbol,
                interval=interval,
                start_ms=start_ms,
                end_ms=current_end,
                limit=limit,
                # Pagination must be based on raw returned rows, not only closed rows.
                # Otherwise limit=1 on the current unfinished candle could stop history
                # retrieval prematurely. Filtering is applied when storing candles below.
                closed_only=False,
            )
            server_time_ms = page.server_time_ms
            if not page.candles:
                break

            for candle in page.candles:
                if start_ms <= candle.open_time_ms <= end_ms and (not closed_only or candle.is_closed):
                    all_by_open_time[candle.open_time_ms] = candle

            earliest = page.candles[0].open_time_ms
            if earliest <= start_ms:
                break
            next_end = earliest - 1
            if next_end >= current_end:
                raise BybitAPIError("Kline pagination did not move backward")
            current_end = next_end
            if self.request_delay_s:
                time.sleep(self.request_delay_s)
        else:
            raise BybitAPIError("max_pages reached while downloading Bybit klines")

        candles = tuple(sorted(all_by_open_time.values(), key=lambda candle: candle.open_time_ms))
        return HistoricalFetch(
            exchange="BYBIT",
            symbol=symbol.upper(),
            interval=interval,
            requested_start_ms=start_ms,
            requested_end_ms=end_ms,
            server_time_ms=server_time_ms,
            candles=candles,
        )

    def get_instrument_info(self, symbol: str) -> InstrumentInfo:
        payload = self._get(
            "/v5/market/instruments-info",
            {"category": self.category, "symbol": symbol.upper(), "limit": 1000},
        )
        result = payload.get("result", {})
        result_category = str(result.get("category", ""))
        if result_category and result_category != self.category:
            raise BybitAPIError(f"Bybit instrument category mismatch: requested {self.category}, got {result_category}")
        rows = result.get("list", [])
        if not rows:
            raise BybitAPIError(f"Instrument not found: {symbol.upper()}")
        row = next((item for item in rows if str(item.get("symbol", "")).upper() == symbol.upper()), None)
        if row is None:
            raise BybitAPIError(f"Instrument response did not contain requested symbol: {symbol.upper()}")
        price_filter = row.get("priceFilter", {})
        lot = row.get("lotSizeFilter", {})
        leverage = row.get("leverageFilter", {})

        def optional_float(value: Any) -> float | None:
            if value in (None, ""):
                return None
            return float(value)

        def optional_int(value: Any) -> int | None:
            if value in (None, "", "0", 0):
                return None
            return int(value)

        return InstrumentInfo(
            exchange="BYBIT",
            symbol=str(row.get("symbol", symbol.upper())),
            contract_type=str(row.get("contractType", "")),
            symbol_type=str(row.get("symbolType", "")),
            market_region=str(row.get("marketRegion", "")),
            base_coin=str(row.get("baseCoin", "")),
            quote_coin=str(row.get("quoteCoin", "")),
            settle_coin=str(row.get("settleCoin", "")),
            status=str(row.get("status", "")),
            launch_time_ms=optional_int(row.get("launchTime")),
            delivery_time_ms=optional_int(row.get("deliveryTime")),
            tick_size=optional_float(price_filter.get("tickSize")),
            qty_step=optional_float(lot.get("qtyStep")),
            min_order_qty=optional_float(lot.get("minOrderQty")),
            max_order_qty=optional_float(lot.get("maxOrderQty")),
            max_market_order_qty=optional_float(lot.get("maxMktOrderQty")),
            min_notional_value=optional_float(lot.get("minNotionalValue")),
            funding_interval_min=optional_int(row.get("fundingInterval")),
            max_leverage=optional_float(leverage.get("maxLeverage")),
        )
