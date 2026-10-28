import unittest
from urllib.parse import parse_qs, urlparse

from crypto_bot.data.okx import OKXAPIError, OKXPublicClient


class FakeOKXTransport:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if parsed.path.endswith("/public/time"):
            return {"code": "0", "msg": "", "data": [{"ts": "360000"}]}
        if parsed.path.endswith("/public/instruments"):
            return {
                "code": "0",
                "msg": "",
                "data": [{
                    "instType": "SWAP",
                    "instId": "BTC-USDT-SWAP",
                    "instFamily": "BTC-USDT",
                    "ctType": "linear",
                    "ctValCcy": "BTC",
                    "baseCcy": "",
                    "quoteCcy": "",
                    "settleCcy": "USDT",
                    "state": "live",
                    "listTime": "1000",
                    "expTime": "",
                    "tickSz": "0.1",
                    "lotSz": "0.01",
                    "minSz": "0.01",
                    "maxLmtSz": "1000",
                    "maxMktSz": "500",
                }],
            }
        if parsed.path.endswith("/history-candles"):
            after = int(qs["after"][0])
            rows = {
                300_001: [
                    ["240000", "104", "106", "103", "105", "30", "3", "315", "1"],
                    ["180000", "103", "105", "102", "104", "20", "2", "208", "1"],
                ],
                180_000: [
                    ["120000", "102", "104", "101", "103", "20", "2", "206", "1"],
                    ["60000", "101", "103", "100", "102", "20", "2", "204", "1"],
                ],
            }
            return {"code": "0", "msg": "", "data": rows.get(after, [])}
        raise AssertionError(url)


class OKXDataTests(unittest.TestCase):
    def test_repository_intervals_map_to_okx_bars_and_daily_is_utc(self):
        self.assertEqual(OKXPublicClient.api_bar("5"), "5m")
        self.assertEqual(OKXPublicClient.api_bar("15"), "15m")
        self.assertEqual(OKXPublicClient.api_bar("60"), "1H")
        self.assertEqual(OKXPublicClient.api_bar("240"), "4H")
        self.assertEqual(OKXPublicClient.api_bar("D"), "1Dutc")

    def test_weekly_interval_is_not_silently_assumed_fixed(self):
        with self.assertRaises(ValueError):
            OKXPublicClient.interval_ms("W")

    def test_server_time_uses_exchange_clock(self):
        client = OKXPublicClient(transport=FakeOKXTransport(), request_delay_s=0)
        self.assertEqual(client.get_server_time_ms(), 360_000)

    def test_page_uses_confirm_as_authoritative_closed_flag(self):
        def transport(url):
            parsed = urlparse(url)
            if parsed.path.endswith("/public/time"):
                return {"code": "0", "msg": "", "data": [{"ts": "999999"}]}
            if parsed.path.endswith("/history-candles"):
                return {
                    "code": "0",
                    "msg": "",
                    "data": [
                        ["120000", "2", "3", "1", "2.5", "10", "9", "22.5", "0"],
                        ["60000", "1", "2", "0.5", "1.5", "10", "9", "13.5", "1"],
                    ],
                }
            raise AssertionError(url)

        client = OKXPublicClient(transport=transport, request_delay_s=0)
        page = client.get_kline_page(symbol="BTC-USDT-SWAP", interval="1", after_ms=180_000)
        self.assertEqual([c.open_time_ms for c in page.candles], [60_000])
        self.assertTrue(page.candles[0].is_closed)
        self.assertEqual(page.candles[0].volume_base, 9.0)
        self.assertEqual(page.candles[0].turnover_quote, 13.5)

    def test_pagination_moves_backwards_and_deduplicates(self):
        transport = FakeOKXTransport()
        client = OKXPublicClient(transport=transport, request_delay_s=0)
        result = client.fetch_klines(
            symbol="BTC-USDT-SWAP",
            interval="1",
            start_ms=60_000,
            end_ms=300_000,
            limit=2,
        )
        self.assertEqual([c.open_time_ms for c in result.candles], [60_000, 120_000, 180_000, 240_000])
        history_urls = [url for url in transport.urls if "/history-candles?" in url]
        self.assertEqual(len(history_urls), 2)
        self.assertEqual(parse_qs(urlparse(history_urls[0]).query)["after"], ["300001"])
        self.assertEqual(parse_qs(urlparse(history_urls[1]).query)["after"], ["180000"])

    def test_fetch_filters_unfinished_rows_without_breaking_pagination(self):
        calls = []

        def transport(url):
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            calls.append(url)
            if parsed.path.endswith("/public/time"):
                return {"code": "0", "msg": "", "data": [{"ts": "999999"}]}
            if parsed.path.endswith("/history-candles"):
                after = int(qs["after"][0])
                if after == 180_001:
                    return {
                        "code": "0", "msg": "",
                        "data": [["120000", "2", "3", "1", "2.5", "10", "9", "22.5", "0"]],
                    }
                if after == 120_000:
                    return {
                        "code": "0", "msg": "",
                        "data": [["60000", "1", "2", "0.5", "1.5", "10", "9", "13.5", "1"]],
                    }
                return {"code": "0", "msg": "", "data": []}
            raise AssertionError(url)

        client = OKXPublicClient(transport=transport, request_delay_s=0)
        result = client.fetch_klines(
            symbol="BTC-USDT-SWAP",
            interval="1",
            start_ms=60_000,
            end_ms=180_000,
            limit=1,
        )
        self.assertEqual([c.open_time_ms for c in result.candles], [60_000])
        self.assertEqual(len([url for url in calls if "/history-candles?" in url]), 2)

    def test_instrument_parses_usdt_linear_swap_into_existing_model(self):
        client = OKXPublicClient(transport=FakeOKXTransport(), request_delay_s=0)
        info = client.get_instrument_info("BTC-USDT-SWAP")
        self.assertEqual(info.exchange, "OKX")
        self.assertEqual(info.contract_type, "LinearPerpetual")
        self.assertEqual(info.base_coin, "BTC")
        self.assertEqual(info.quote_coin, "USDT")
        self.assertEqual(info.settle_coin, "USDT")
        self.assertTrue(info.is_usdt_linear_perpetual)
        self.assertEqual(info.tick_size, 0.1)
        self.assertEqual(info.qty_step, 0.01)
        self.assertEqual(info.max_market_order_qty, 500.0)
        self.assertIsNone(info.delivery_time_ms)

    def test_api_error_is_stable(self):
        client = OKXPublicClient(
            transport=lambda url: {"code": "51000", "msg": "Parameter error", "data": []},
            request_delay_s=0,
        )
        with self.assertRaises(OKXAPIError):
            client.get_server_time_ms()

    def test_invalid_kline_row_is_rejected(self):
        def transport(url):
            parsed = urlparse(url)
            if parsed.path.endswith("/public/time"):
                return {"code": "0", "msg": "", "data": [{"ts": "999999"}]}
            if parsed.path.endswith("/history-candles"):
                return {"code": "0", "msg": "", "data": [["60000", "5", "4", "3", "3.5", "1", "1", "3.5", "1"]]}
            raise AssertionError(url)

        client = OKXPublicClient(transport=transport, request_delay_s=0)
        with self.assertRaises(OKXAPIError):
            client.get_kline_page(symbol="BTC-USDT-SWAP", interval="1", after_ms=120_000)


if __name__ == "__main__":
    unittest.main()
