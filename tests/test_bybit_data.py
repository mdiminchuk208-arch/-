import unittest
from urllib.parse import parse_qs, urlparse

from crypto_bot.data.bybit import BybitAPIError, BybitPublicClient


class FakeBybitTransport:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if parsed.path.endswith("/time"):
            return {
                "retCode": 0, "retMsg": "OK", "time": 360_000,
                "result": {"timeSecond": "360", "timeNano": "360000000000"},
            }
        if parsed.path.endswith("/instruments-info"):
            return {
                "retCode": 0,
                "retMsg": "OK",
                "time": 1_000_000,
                "result": {
                    "list": [{
                        "symbol": "BTCUSDT",
                        "contractType": "LinearPerpetual",
                        "symbolType": "",
                        "marketRegion": "",
                        "baseCoin": "BTC",
                        "quoteCoin": "USDT",
                        "settleCoin": "USDT",
                        "status": "Trading",
                        "launchTime": "1000",
                        "deliveryTime": "0",
                        "priceFilter": {"tickSize": "0.1"},
                        "lotSizeFilter": {
                            "qtyStep": "0.001", "minOrderQty": "0.001",
                            "maxOrderQty": "100", "maxMktOrderQty": "50",
                            "minNotionalValue": "5"
                        },
                        "fundingInterval": 480,
                        "leverageFilter": {"maxLeverage": "100"},
                    }]
                },
            }
        if parsed.path.endswith("/kline"):
            end = int(qs["end"][0])
            rows = {
                300_000: [
                    ["240000", "104", "106", "103", "105", "3", "315"],
                    ["180000", "103", "105", "102", "104", "2", "208"],
                ],
                179_999: [
                    ["120000", "102", "104", "101", "103", "2", "206"],
                    ["60000", "101", "103", "100", "102", "2", "204"],
                ],
            }
            return {
                "retCode": 0,
                "retMsg": "OK",
                "time": 360_000,
                "result": {"list": rows.get(end, [])},
            }
        raise AssertionError(url)


class BybitDataTests(unittest.TestCase):
    def test_page_is_normalized_to_ascending_time_and_unfinished_removed(self):
        transport = lambda url: {
            "retCode": 0,
            "retMsg": "OK",
            "time": 179_999,
            "result": {"list": [
                ["120000", "2", "3", "1", "2.5", "10", "25"],  # still open at server time
                ["60000", "1", "2", "0.5", "1.5", "9", "13.5"],
            ]},
        }
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        page = client.get_kline_page(symbol="BTCUSDT", interval="1", end_ms=120000)
        self.assertEqual([c.open_time_ms for c in page.candles], [60000])
        self.assertTrue(all(c.is_closed for c in page.candles))

    def test_pagination_moves_backwards_and_deduplicates(self):
        transport = FakeBybitTransport()
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        result = client.fetch_klines(symbol="BTCUSDT", interval="1", start_ms=60_000, end_ms=300_000, limit=2)
        self.assertEqual([c.open_time_ms for c in result.candles], [60_000, 120_000, 180_000, 240_000])
        self.assertEqual(len([u for u in transport.urls if "/kline?" in u]), 2)

    def test_weekly_interval_is_not_silently_treated_as_epoch_aligned(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        with self.assertRaises(ValueError):
            client.interval_ms("W")


    def test_server_time_uses_exchange_clock(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        self.assertEqual(client.get_server_time_ms(), 360_000)

    def test_instrument_is_verified_as_usdt_linear_perpetual(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        info = client.get_instrument_info("BTCUSDT")
        self.assertEqual(info.contract_type, "LinearPerpetual")
        self.assertTrue(info.is_usdt_linear_perpetual)
        self.assertEqual(info.max_market_order_qty, 50.0)
        self.assertEqual(info.min_notional_value, 5.0)
        self.assertEqual(info.funding_interval_min, 480)
        self.assertEqual(info.max_leverage, 100.0)

    def test_fetch_does_not_stop_when_limit_one_first_row_is_unfinished(self):
        calls = []
        def transport(url):
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            calls.append(url)
            end = int(qs["end"][0])
            if end == 180_000:
                return {
                    "retCode": 0, "retMsg": "OK", "time": 179_999,
                    "result": {"list": [["120000", "2", "3", "1", "2.5", "10", "25"]]},
                }
            if end == 119_999:
                return {
                    "retCode": 0, "retMsg": "OK", "time": 179_999,
                    "result": {"list": [["60000", "1", "2", "0.5", "1.5", "9", "13.5"]]},
                }
            return {"retCode": 0, "retMsg": "OK", "time": 179_999, "result": {"list": []}}
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        result = client.fetch_klines(symbol="BTCUSDT", interval="1", start_ms=60_000, end_ms=180_000, limit=1)
        self.assertEqual([c.open_time_ms for c in result.candles], [60_000])
        self.assertEqual(len(calls), 2)


    def test_tradfi_like_market_region_is_not_accepted_as_crypto_perpetual(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        info = client.get_instrument_info("BTCUSDT")
        from dataclasses import replace
        tradfi = replace(info, market_region="US")
        self.assertFalse(tradfi.is_usdt_linear_perpetual)


    def test_tradfi_like_symbol_type_is_not_accepted_as_crypto_perpetual(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        info = client.get_instrument_info("BTCUSDT")
        from dataclasses import replace
        tradfi = replace(info, symbol_type="US")
        self.assertFalse(tradfi.is_usdt_linear_perpetual)

    def test_kline_response_symbol_mismatch_is_rejected(self):
        transport = lambda url: {
            "retCode": 0, "retMsg": "OK", "time": 180_000,
            "result": {"category": "linear", "symbol": "ETHUSDT", "list": []},
        }
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        with self.assertRaises(BybitAPIError):
            client.get_kline_page(symbol="BTCUSDT", interval="1", end_ms=120_000)

    def test_negative_volume_is_rejected_as_invalid_exchange_row(self):
        transport = lambda url: {
            "retCode": 0, "retMsg": "OK", "time": 180_000,
            "result": {"list": [["60000", "3", "4", "2", "3.5", "-1", "3.5"]]},
        }
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        with self.assertRaises(BybitAPIError):
            client.get_kline_page(symbol="BTCUSDT", interval="1", end_ms=120_000)

    def test_invalid_exchange_ohlc_fails_with_stable_api_error(self):
        transport = lambda url: {
            "retCode": 0, "retMsg": "OK", "time": 180_000,
            "result": {"list": [["60000", "5", "4", "3", "3.5", "1", "3.5"]]},
        }
        client = BybitPublicClient(transport=transport, request_delay_s=0)
        with self.assertRaises(BybitAPIError):
            client.get_kline_page(symbol="BTCUSDT", interval="1", end_ms=120_000)

    def test_instrument_info_parses_contract_specification(self):
        client = BybitPublicClient(transport=FakeBybitTransport(), request_delay_s=0)
        info = client.get_instrument_info("BTCUSDT")
        self.assertEqual(info.base_coin, "BTC")
        self.assertEqual(info.tick_size, 0.1)
        self.assertEqual(info.qty_step, 0.001)
        self.assertIsNone(info.delivery_time_ms)


if __name__ == "__main__":
    unittest.main()
