"""Source identity, prefix and release clock tests only."""

import sys
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from okx_qualification_data_v1 import DataInvalid
from okx_v3_input_bridge_v1 import (
    NativeBar,
    aggregate,
    private_or_financial_transport,
    validate,
    visible_prefix,
)


def bars(count=16):
    return [
        NativeBar(
            i * 900,
            (i + 1) * 900,
            Decimal(100),
            Decimal(102),
            Decimal(99),
            Decimal(101),
            "BTC-USDT-SWAP",
        )
        for i in range(count)
    ]


class BridgeTests(unittest.TestCase):
    def test_exact_groups_release_on_complete_end(self):
        derived, omitted = aggregate(bars(), 3600)
        self.assertEqual(len(derived), 4)
        self.assertEqual(omitted, [])
        self.assertEqual(len(visible_prefix(derived, 3599)), 0)
        self.assertEqual(len(visible_prefix(derived, 3600)), 1)

    def test_future_mutation_cannot_change_visible_prefix(self):
        original = bars()
        changed = original[:4] + [replace(b, high=Decimal(999)) for b in original[4:]]
        a, _ = aggregate(original, 3600)
        b, _ = aggregate(changed, 3600)
        self.assertEqual(visible_prefix(a, 3600), visible_prefix(b, 3600))

    def test_interior_missing_bar_rejected(self):
        b = bars()
        with self.assertRaises(DataInvalid):
            aggregate(b[:3] + b[4:], 3600)

    def test_edge_incomplete_group_not_invented(self):
        derived, omitted = aggregate(bars(5), 3600)
        self.assertEqual(len(derived), 1)
        self.assertEqual(omitted, [3600])

    def test_product_mix_rejected(self):
        b = bars()
        b[-1] = replace(b[-1], product="ETH-USDT-SWAP")
        with self.assertRaises(DataInvalid):
            validate(b, 900)

    def test_source_description_does_not_claim_Bybit_or_actual_latency(self):
        record = bars(1)[0].observed(15)
        self.assertNotIn("Bybit", record["evidence"])
        self.assertIn("modeled availability", record["evidence"])

    def test_direct_private_or_financial_boundary_fails_closed(self):
        with self.assertRaisesRegex(DataInvalid, "STAGE_A_FORBIDS"):
            private_or_financial_transport(trade_entry_allowed=True)


if __name__ == "__main__":
    unittest.main()
