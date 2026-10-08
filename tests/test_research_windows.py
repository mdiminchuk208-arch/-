from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

from crypto_bot.common.models import Candle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_robustness_research import common_segments, slice_bars

START = datetime(2020, 1, 1, tzinfo=timezone.utc)


def bar(index):
    return Candle(START+timedelta(minutes=5*index), START+timedelta(minutes=5*(index+1)),
                  100, 101, 99, 100, True)


class ResearchWindowTests(unittest.TestCase):
    def test_every_symbol_gap_partitions_shared_execution_clock(self):
        a = [bar(i) for i in range(8) if i != 2]
        b = [bar(i) for i in range(8) if i != 3]
        segments, gaps = common_segments({'A': a, 'B': b})
        self.assertEqual(gaps, [(bar(2).open_time, bar(3).close_time)])
        self.assertEqual(segments, [(START, bar(1).close_time), (bar(4).open_time, bar(7).close_time)])
        for begin, end in segments:
            self.assertEqual([c.close_time for c in slice_bars(a, begin, end)],
                             [c.close_time for c in slice_bars(b, begin, end)])

    def test_slicing_excludes_candle_not_closed_at_cutoff(self):
        rows = [bar(i) for i in range(8)]
        self.assertEqual(slice_bars(rows, START, START+timedelta(minutes=12)), rows[:2])
        self.assertEqual(slice_bars(rows, START+timedelta(minutes=6), START+timedelta(minutes=16)), rows[2:3])


if __name__ == '__main__':
    unittest.main()
