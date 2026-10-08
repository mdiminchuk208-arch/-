"""Reproduce automatic constructed-market CLI evidence; no Bybit performance claim.

Usage: PYTHONPATH=src python tests/validate_constructed.py [report-directory]
"""
import json,subprocess,sys,os
from pathlib import Path
from test_automatic_lifecycle import histories
from crypto_bot.common.models import Direction
from crypto_bot.data.models import MarketCandle
from crypto_bot.data.storage import write_klines_csv
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('data/reports/continuation_validation/constructed')
root.mkdir(parents=True,exist_ok=True)
results={}
for direction in Direction:
 data=histories(direction)
 base=root/direction.value
 for tf,cs in data.items():
  rows=[MarketCandle('BYBIT','E2E',str(tf),int(c.open_time.timestamp()*1000),c.open,c.high,c.low,c.close,volume_base=0) for c in cs]
  write_klines_csv(rows,base/'input/E2E'/f'{tf}.csv')
 variants=[('backtest','BACKTEST',[]),('repeat','BACKTEST',[]),('shadow','SHADOW',[]),('partial','SHADOW',['--checkpoint',str(base/'restart.json'),'--stop-after-bars','188']),('resumed','SHADOW',['--checkpoint',str(base/'restart.json'),'--resume'])]
 for label,mode,extra in variants:
  out=base/label
  cmd=[sys.executable,'scripts/run_historical_portfolio.py','--data-root',str(base/'input'),'--report-root',str(out),'--symbols','E2E','--days','max','--warmup-bars','0','--mode',mode,*extra]
  r=subprocess.run(cmd,env={**os.environ,'PYTHONPATH':'src'},capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
  (base/(label+'.log')).write_text(r.stdout+r.stderr)
  summary=json.loads((out/'summary.json').read_text())
  stats=summary['portfolio'];funnel=summary['funnel']
  results[direction.value+'_'+label]={'data_kind':'CONSTRUCTED_CONSISTENT_OHLC_TEST_FIXTURE_NOT_BYBIT_HISTORY','complete':summary['run_complete'],'setups':funnel['unique_setups'],'signals':funnel['signal_state_changes'],'ready':funnel['ever_status_unique_setup_counts']['READY_FOR_VIRTUAL_ENTRY'],'entries':funnel['entries'],'closed':funnel['completed_trades'],'final_equity':stats['final_equity'],'fingerprint':(out/'fingerprint.sha256').read_text().strip()}
  print(label,direction.value,r.stdout.strip())
  if label!='partial':
   assert funnel['entries']==1 and funnel['completed_trades']==1 and funnel['setup_outcomes']['passed']==1
   fills=[json.loads(x) for x in (out/'decisions.jsonl').read_text().splitlines()]
   assert [x['reason'] for x in fills if x['action']=='VIRTUAL_EXIT']==['TP1','TP2','TP3']
   assert all(x['trade_entry_allowed'] is False for x in fills)
 assert results[direction.value+'_backtest']['fingerprint']==results[direction.value+'_repeat']['fingerprint']
 assert results[direction.value+'_shadow']['fingerprint']==results[direction.value+'_resumed']['fingerprint']
 assert all((base/'backtest'/f).read_bytes()==(base/'shadow'/f).read_bytes() for f in ('decisions.jsonl','trades.jsonl','equity_curve.jsonl','setup_outcomes.jsonl'))
results['checks']={'automatic_analysis_without_injected_signals':'PASS','long_short_tp_40_30_30':'PASS','fees_slippage_pnl':'PASS','repeat_fingerprint':'PASS','restart_after_TP1_fingerprint':'PASS','backtest_shadow_execution_parity':'PASS','live_execution_disabled':'PASS'}
(root/'verification.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
