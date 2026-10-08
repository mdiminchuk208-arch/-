"""Read-only causal grouping of the frozen development 40 READY / 7 fills."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from crypto_bot.data.storage import read_klines_csv
from import_public_research_data import aggregate
from research_support import check_baseline, regime


def main():
    repo=Path(__file__).resolve().parents[1]
    check_baseline(repo)
    source=repo/'data/reports/historical_blocker_investigation/stage4/entry_first_outcomes.json'
    records=json.loads(source.read_text())['records']
    days={}
    hashes={str(source.relative_to(repo)):sha256(source.read_bytes()).hexdigest()}
    groups=defaultdict(Counter)
    annotated=[]
    for row in records:
        s=row['symbol']
        if s not in days:
            p=repo/f'data/history/bybit/{s}/60.csv'
            candles=read_klines_csv(p)
            rows,_=aggregate(candles,60,1440)
            days[s]=[c.to_strategy_candle(86400000) for c in rows]
            hashes[str(p.relative_to(repo))]=sha256(p.read_bytes()).hexdigest()
        market,vol=regime(days[s],datetime.fromisoformat(row['ready_time']))
        filled=row['terminal_reason'].startswith('VIRTUAL_TRADE_')
        annotated.append(dict(**row,ready_regime=market,ready_volatility_bucket=vol,filled=filled))
        for dimension,value in [('symbol',s),('direction',row['direction']),('mapping',row['mapping']),
                                ('ready_regime',market),('ready_volatility_bucket',vol)]:
            groups[(dimension,value)]['ready']+=1
            groups[(dimension,value)]['filled']+=int(filled)
    counts=Counter(r['terminal_reason'] for r in records)
    assert len(annotated)==40 and sum(r['filled'] for r in annotated)==7
    result=dict(cohort='BYBIT_2026_DEVELOPMENT_ALREADY_USED',ready=40,filled=7,fill_rate=7/40,
        outcomes=dict(counts),source_hashes=hashes,records=annotated,
        groups=[dict(dimension=k[0],value=k[1],**v,fill_rate=v['filled']/v['ready']) for k,v in sorted(groups.items())],
        market_label_policy='31_CONSECUTIVE_PRIOR_COMPLETE_UTC_DAILY_CLOSES_AT_FIRST_READY',
        missing_prior_history='UNKNOWN_NO_FUTURE_BACKFILL',
        normal_events={
            'LIMIT_NOT_FILLED_BEFORE_OB_FIRST_TEST_CONSUMED':'First OB touch can miss the interior executable quote; no retrospective fill.',
            'ISOLATED_MARGIN_BUDGET':'2% cost-aware risk sizing may require more than 1170 available equity at 3x leverage.',
            'TARGET_EVIDENCE_WITHDRAWN':'A previously fresh selected target is actually touched before the entry quote fills.',
            'PRICE_NOT_FILLED_BEFORE_OBSERVATION_END':'Censored at dataset end, not an invented trade or a market failure.'},
        prior_exact_price_target_audits='historical_blocker_investigation/stage4/real_exit_price_audit.json and withdrawn_target_evidence.json',
        trade_entry_allowed=False)
    target=repo/'data/reports/robustness_research/development_fill_frequency.json'
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('Development READY/fill frequency: 40 / 7; all 33 nonfills retained.')


if __name__=='__main__':
    main()
