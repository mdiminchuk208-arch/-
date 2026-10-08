"""Exact input-bound caching of immutable structural reports, never signal fitting."""
from __future__ import annotations

from contextlib import contextmanager
from bisect import bisect_right
import gzip
from hashlib import sha256
import pickle
from os import getpid

from crypto_bot.strategy import auto_levels, historical_replay, trade_plan
from run_historical_portfolio import canonical


@contextmanager
def validated_prefix_reuse(histories):
    """Reuse full-series validation only for exact immutable source prefixes.

    The frozen index already validates its entire offline series. Equality is
    checked on every supplied prefix; a changed/interior foreign candle falls
    back to the original validator. Only closed bars at/before as_of are returned.
    This removes repeated Python validation, not any evidence/knowledge gate.
    Gap seeds are also retained once per immutable series and sliced by their
    confirmation close. This preserves the original prefix seed order and never
    exposes a seed formed by a future candle.
    """
    original=auto_levels._prefix
    original_seeds=auto_levels._seeds
    known={}
    for candles in histories.values():
        source=tuple(candles)
        if source:
            checked,minutes=original(source,source[-1].close_time)
            assert checked==source
            seeds=original_seeds(source)
            known[id(source[0])]=(source,tuple(c.close_time for c in source),minutes,
                                  seeds,tuple(seed.known_at for seed in seeds))
    def prefix(candles,as_of):
        record=known.get(id(candles[0])) if candles else None
        if record is not None:
            source,closes,minutes,_,_=record
            supplied=tuple(candles)
            if supplied==source[:len(supplied)]:
                count=min(len(supplied),bisect_right(closes,as_of))
                return (source[:count],minutes) if count else ((),0)
        return original(candles,as_of)
    def seeds(candles):
        record=known.get(id(candles[0])) if candles else None
        if record is not None:
            source,_,_,saved,times=record
            supplied=tuple(candles)
            if supplied==source[:len(supplied)]:
                return saved[:bisect_right(times,supplied[-1].close_time)]
        return original_seeds(candles)
    try:
        auto_levels._prefix=prefix
        auto_levels._seeds=seeds
        yield
    finally:
        auto_levels._prefix=original
        auto_levels._seeds=original_seeds


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
