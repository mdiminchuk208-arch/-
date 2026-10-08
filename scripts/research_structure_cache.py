"""Exact input-bound caching of immutable structural reports, never signal fitting."""
from __future__ import annotations

from contextlib import contextmanager
import gzip
from hashlib import sha256
import pickle
from os import getpid

from crypto_bot.strategy import historical_replay, trade_plan
from run_historical_portfolio import canonical


@contextmanager
def structure_cache(root, source_hashes, baseline):
    names=('analyze_market','augment_market_report_with_range_sfps','link_sfp_formations_to_ltf_bos')
    original={name:getattr(historical_replay,name) for name in names}
    identities=[]
    try:
        for name in names:
            def call(*args,_name=name,**kwargs):
                if _name=='link_sfp_formations_to_ltf_bos':
                    # MTF linking also attaches OTE geometry. Unlike raw market
                    # and Range reports, this result depends on OTE parameters.
                    inputs=dict(report_inputs=identities,kwargs=kwargs,
                                ote_shallow=trade_plan.OTE_SHALLOW,ote_deep=trade_plan.OTE_DEEP)
                else:
                    candles=args[0]
                    minutes=int((candles[0].close_time-candles[0].open_time).total_seconds()/60)
                    inputs=dict(source_sha256=source_hashes[minutes],minutes=minutes,
                        first_open=candles[0].open_time,last_close=candles[-1].close_time,count=len(candles),kwargs=kwargs)
                key=sha256(canonical(dict(function=_name,inputs=inputs,baseline=baseline,version=1)).encode()).hexdigest()
                identities.append(key)
                path=root/(key+'.structural.pickle.gz')
                if path.exists():
                    with gzip.open(path,'rb') as handle:
                        return pickle.load(handle)
                result=original[_name](*args,**kwargs)
                root.mkdir(parents=True,exist_ok=True)
                # Only locally generated objects are cached, never downloaded.
                temporary=path.with_suffix(f'.{getpid()}.tmp')
                with gzip.open(temporary,'wb') as handle:
                    pickle.dump(result,handle,pickle.HIGHEST_PROTOCOL)
                temporary.replace(path)
                return result
            setattr(historical_replay,name,call)
        yield
    finally:
        for name,fn in original.items():
            setattr(historical_replay,name,fn)
