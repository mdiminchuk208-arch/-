from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crypto_bot.common.models import Direction
from crypto_bot.strategy.virtual_portfolio import VirtualPortfolio
from test_virtual_portfolio import bar,signal


class PortfolioCheckpointTests(unittest.TestCase):
    def test_json_restart_pending_and_partial_position_is_identical(self):
        for direction in Direction:
            p=VirtualPortfolio(equity=1170,mode='SHADOW')
            s=signal(direction=direction,mode='SHADOW')
            p.step({'TEST':bar(0)},[s])
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'state.json'
                p.save_checkpoint(path)
                restored=VirtualPortfolio.load_checkpoint(path)
                self.assertEqual(restored.snapshot(),p.snapshot())
                for instance in (p,restored):
                    instance.step({'TEST':bar(1)})
                    instance.step({'TEST':bar(2,108,111,107,110) if direction==Direction.LONG else bar(2,92,93,89,90)})
                self.assertEqual(restored.snapshot(),p.snapshot())
                restored.save_checkpoint(path)
                restored=VirtualPortfolio.load_checkpoint(path)
                for instance in (p,restored):
                    instance.step({'TEST':bar(3,115,121,114,120) if direction==Direction.LONG else bar(3,85,86,79,80)})
                    instance.step({'TEST':bar(4,125,131,124,130) if direction==Direction.LONG else bar(4,75,76,69,70)})
                self.assertEqual(restored.snapshot(),p.snapshot())
                self.assertEqual(p.positions,{})
                self.assertEqual(p.trades['one']['status'],'CLOSED')
                self.assertFalse(restored.trade_entry_allowed)

    def test_daily_loss_and_consumed_identity_survive_restart(self):
        p=VirtualPortfolio(equity=1170)
        p.step({'TEST':bar(0)},[signal()]);p.step({'TEST':bar(1)})
        p.step({'TEST':bar(2,88,89,87,88)})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'state.json';p.save_checkpoint(path)
            q=VirtualPortfolio.load_checkpoint(path)
            self.assertEqual(q.snapshot(),p.snapshot())
            self.assertTrue(q._daily_blocked)
            q.step({'TEST':bar(3)},[signal(3,ident='new')]);q.step({'TEST':bar(4)})
            self.assertEqual(q.positions,{})
            self.assertIn('new',q.consumed_ids)
            with self.assertRaises(ValueError):q.step({'TEST':bar(4)})

    def test_corruption_and_live_mode_never_restore(self):
        import json
        p=VirtualPortfolio()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'state.json';p.save_checkpoint(path)
            payload=json.loads(path.read_text());payload['state']['mode']='LIVE'
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):VirtualPortfolio.load_checkpoint(path)
            path.write_text('{malformed')
            with self.assertRaises(ValueError):VirtualPortfolio.load_checkpoint(path)

    def test_failed_atomic_replace_keeps_previous_complete_state(self):
        p=VirtualPortfolio()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'state.json';p.save_checkpoint(path)
            previous=path.read_bytes()
            p.step({'TEST':bar(0)},[signal()])
            with patch('crypto_bot.strategy.checkpoint.os.replace',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):p.save_checkpoint(path)
            self.assertEqual(path.read_bytes(),previous)
            self.assertEqual(VirtualPortfolio.load_checkpoint(path).positions,{})
            self.assertEqual(list(Path(temp).iterdir()),[path])

    def test_valid_digest_cannot_enable_live_mode_or_real_entry_flag(self):
        import json
        from hashlib import sha256
        from crypto_bot.strategy.checkpoint import _canonical
        p=VirtualPortfolio()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'state.json';p.save_checkpoint(path)
            original=path.read_text()
            for change in ('LIVE','real_flag'):
                payload=json.loads(original);payload.pop('sha256')
                if change=='LIVE':payload['state']['mode']='LIVE'
                else:payload['trade_entry_allowed']=True
                payload['sha256']=sha256(_canonical(payload).encode()).hexdigest()
                path.write_text(json.dumps(payload))
                with self.subTest(change=change),self.assertRaises(ValueError):
                    VirtualPortfolio.load_checkpoint(path)


if __name__=='__main__':unittest.main()
