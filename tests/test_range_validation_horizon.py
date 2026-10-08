"""A range decision must not allocate prices beyond its first terminal event."""
from collections.abc import Sequence
import unittest

from crypto_bot.strategy.range_engine import (
    RangeDetectionParams, _make_range_candidates, _validate_candidates,
)
from test_range_engine import base_report, bullish_range_events, c


class CountedCandles(Sequence):
    def __init__(self,rows):
        self.rows=rows
        self.reads=0

    def __len__(self):
        return len(self.rows)

    def __getitem__(self,index):
        self.reads+=1
        return self.rows[index]


class RangeValidationHorizonTests(unittest.TestCase):
    def test_long_suffix_does_not_expand_prevalidation_price_work(self):
        short=[c(i) for i in range(10)]
        full=[*short,*[c(i) for i in range(10,2010)]]
        report=base_report(full,bullish_range_events())
        candidates=_make_range_candidates(report)
        expected=_validate_candidates(short,base_report(short,bullish_range_events()),
                                      candidates,RangeDetectionParams())
        counted=CountedCandles(full)
        actual=_validate_candidates(counted,report,candidates,RangeDetectionParams())
        self.assertEqual(actual,expected)
        self.assertLess(counted.reads,30)
