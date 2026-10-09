"""Additive causal source replay. See SOURCE_RECONSTRUCTION_2026_10_09.md.

This is an explicit machine interpretation, not the frozen research detector.
No private client, execution adapter, exchange credentials or live admission.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from bisect import bisect_left
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
import json
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEvent, MarketEventKind as K, TrendState
from crypto_bot.strategy.range_engine import RangeAnalysisReport

MAPPINGS = ((15, 5), (60, 5), (60, 15), (240, 5), (240, 15), (240, 60))
ZONE_TYPES = frozenset({'ORDER_BLOCK', 'BREAKER', 'DEMAND', 'SUPPLY', 'MANIPULATION', 'STB', 'BTS', 'FVG', 'RANGE_POI'})


def identity(*values: object) -> str:
    return sha256('|'.join(str(v) for v in values).encode()).hexdigest()[:24]


def sign(direction: str) -> int:
    if direction not in ('LONG', 'SHORT'):
        raise ValueError('invalid direction')
    return 1 if direction == 'LONG' else -1


def event_direction(event: MarketEvent) -> str | None:
    if event.kind in (K.BULLISH_STRUCTURE_CONFIRMED, K.BULLISH_CONF_CONFIRMED, K.BEARISH_STRUCTURE_BROKEN_BOS):
        return 'LONG'
    if event.kind in (K.BEARISH_STRUCTURE_CONFIRMED, K.BEARISH_CONF_CONFIRMED, K.BULLISH_STRUCTURE_BROKEN_BOS):
        return 'SHORT'
    return None


def evidence_json(value: object) -> str:
    return json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, datetime) else x.value,
                      sort_keys=True, separators=(',', ':'))


@dataclass(frozen=True)
class Raid:
    direction: str
    known_at: datetime
    price: float
    extreme: float
    candle_index: int
    liquidity_ids: tuple[str, ...]
    sfp: bool = False


@dataclass
class Pool:
    pool_id: str
    side: str
    price: float
    known_at: datetime
    origin: str
    classification: str


@dataclass
class Zone:
    zone_id: str
    kind: str
    direction: str
    low: float
    high: float
    formed_at: datetime
    known_at: datetime
    origin_index: int
    raid: Raid | None
    leg_low: float
    leg_high: float
    structural_proof: dict | None = None
    aliases: tuple[str, ...] = ()
    first_test: datetime | None = None
    last_test: datetime | None = None
    test_count: int = 0
    invalidated_at: datetime | None = None
    stop_extreme: float | None = None
    range_id: str | int | None = None

    def __post_init__(self) -> None:
        if self.kind not in ZONE_TYPES or not 0 < self.low < self.high:
            raise ValueError('invalid source POI')
        sign(self.direction)
        if self.known_at < self.formed_at:
            raise ValueError('POI cannot be known before formation')

    def fresh(self, cutoff: datetime) -> bool:
        return self.known_at <= cutoff and (self.first_test is None or self.first_test > cutoff) and (
            self.invalidated_at is None or self.invalidated_at > cutoff)

    def test_allowed(self, cutoff: datetime, *, reaction_confirmed_at: datetime | None = None) -> bool:
        """No universal freshness gate; secondary repeat-OB path is explicit."""
        if self.invalidated_at is not None and self.invalidated_at <= cutoff:
            return False
        if self.first_test is None or self.first_test >= cutoff:
            return self.known_at <= cutoff
        if self.kind == 'ORDER_BLOCK':
            return (reaction_confirmed_at is not None and self.last_test is not None
                    and self.last_test < reaction_confirmed_at <= cutoff)
        return False


def pd_location(direction: str, price: float, low: float, high: float) -> tuple[bool, bool, float]:
    if not 0 < low < high:
        return False, False, float('nan')
    retracement = (high - price) / (high - low) if sign(direction) == 1 else (price - low) / (high - low)
    return 0.5 < retracement <= 1, 0.705 <= retracement <= 0.79, retracement


def opposing_liquidity(pools: Sequence[Pool], direction: str, entry: float, stop: float) -> list[dict]:
    """Contextual adverse pools in the planned sweep/stop-to-entry path."""
    s = sign(direction)
    return [asdict(p) for p in pools if p.side == ('low' if s == 1 else 'high')
            and min(entry, stop) < p.price < max(entry, stop)]


class SourceSeries:
    """Replay immutable causal events, never inspect a report's final level state.

    Full-history analysis is an optimization. Only events for the current prefix
    are applied; every decision uses current pools/zones/state, not future metadata.
    """
    def __init__(self, symbol: str, tf: int, candles: Sequence[Candle], report: MarketAnalysisReport,
                 ranges: RangeAnalysisReport | None = None):
        self.symbol, self.tf, self.candles = symbol, tf, candles
        self.events: dict[int, list[MarketEvent]] = defaultdict(list)
        for e in report.events:
            if e.recovery_transition_ids:
                raise ValueError('technical recovery is forbidden in source replay')
            self.events[e.candle_index].append(e)
        self.range_events: dict[int, list[MarketEvent]] = defaultdict(list)
        self.range_bounds: dict[int, tuple[float, float, datetime, str]] = {}
        if ranges is not None:
            for r in ranges.ranges:
                # Later lifecycle status/clarity is deliberately not a selection filter.
                if r.midpoint_reaction_time is not None and r.lower < r.upper:
                    causal_id = identity(symbol, tf, r.first_boundary_time, r.first_boundary_price,
                                         r.second_boundary_time, r.second_boundary_price)
                    self.range_bounds[r.range_id] = (r.lower, r.upper, r.midpoint_reaction_time, causal_id)
            for e in ranges.events:
                self.range_events[e.candle_index].append(e)
        self.index = -1
        self.trend = TrendState.UNKNOWN
        self.structure: dict | None = None
        self.bos: dict[str, dict] = {}
        self.conf: dict[str, dict] = {}
        self.pools: dict[str, Pool] = {}
        self.raids: list[Raid] = []
        self.latest_raid: dict[str, Raid] = {}
        self.sfps: list[Raid] = []
        self.zones: list[Zone] = []
        self.zone_registry: dict[str, Zone] = {}
        self.context_watches: dict[str, Zone] = {}
        self.origins: set[tuple[str, int]] = set()
        self.broken_obs: list[tuple[int, Zone]] = []
        self.pending: list[Zone] = []
        self.last_opposite: dict[str, int] = {}
        self.counts: Counter = Counter()
        self.day: object = None
        self.day_high = self.day_low = 0.0
        self.day_complete = False

    def _zone(self, kind: str, direction: str, low: float, high: float, now: datetime,
              origin: int, raid: Raid | None, *, aliases: tuple[str, ...] = ()) -> Zone:
        c = self.candles[self.index]
        return Zone(identity(self.symbol, self.tf, kind, direction, origin, now, low, high), kind, direction,
                    low, high, now, now, origin, raid, min(low, c.low, raid.extreme if raid else low),
                    max(high, c.high, raid.extreme if raid else high), aliases=aliases)

    def _qualify(self, zone: Zone, proof: dict) -> None:
        zone.known_at = proof['known_at']
        zone.structural_proof = dict(proof)
        zone.leg_low = min(zone.leg_low, self.candles[self.index].low, proof['protected'], proof['extreme'])
        zone.leg_high = max(zone.leg_high, self.candles[self.index].high, proof['protected'], proof['extreme'])
        self.zones.append(zone)
        self.zone_registry[zone.zone_id] = zone
        self.counts['zone_' + zone.kind] += 1

    def raids_after(self, start: datetime) -> list[Raid]:
        return self.raids[bisect_left(self.raids, start, key=lambda r: r.known_at):]

    def _day_pools(self, c: Candle) -> None:
        day = c.open_time.date()
        if day != self.day:
            if self.day is not None and self.day_complete:
                for side, price in [('high', self.day_high), ('low', self.day_low)]:
                    key = f'PD{side}:{self.day}'
                    self.pools[key] = Pool(key, side, price, c.open_time, 'PREVIOUS_COMPLETED_UTC_DAY', 'EXTERNAL')
            self.day = day
            self.day_high, self.day_low = c.high, c.low
            self.day_complete = c.open_time.hour == 0 and c.open_time.minute == 0
        else:
            self.day_high, self.day_low = max(self.day_high, c.high), min(self.day_low, c.low)

    def advance(self, index: int) -> tuple[list[Zone], list[MarketEvent]]:
        if index != self.index + 1:
            raise ValueError('source series must advance contiguously')
        self.index = index
        c = self.candles[index]
        if not c.is_closed:
            raise ValueError('unfinished source candle')
        now = c.close_time
        self._day_pools(c)
        touched = []
        broken = []
        watched = {z.zone_id: z for z in self.zones}
        watched.update(self.context_watches)
        for z in watched.values():
            if z.invalidated_at is not None or z.known_at >= now:
                continue
            overlap = c.low <= z.high and c.high >= z.low
            if overlap:
                first = z.first_test is None
                # Count visits, not consecutive overlapping bars as repeated tests.
                if z.last_test != c.open_time:
                    z.test_count += 1
                z.last_test = now
                if first:
                    z.first_test = now
                    touched.append(z)
            if (z.direction == 'LONG' and c.close < z.low) or (z.direction == 'SHORT' and c.close > z.high):
                z.invalidated_at = now
                if z.kind == 'ORDER_BLOCK':
                    broken.append(z)
        self.broken_obs = [(i, z) for i, z in self.broken_obs if i >= index - 1] + [(index, z) for z in broken]
        for z in self.pending:
            if (z.direction == 'LONG' and c.close < z.low) or (z.direction == 'SHORT' and c.close > z.high):
                z.invalidated_at = now
        removed: dict[str, list[Pool]] = defaultdict(list)
        for key, p in list(self.pools.items()):
            if p.known_at < now and (c.high > p.price if p.side == 'high' else c.low < p.price):
                removed[p.side].append(p)
                del self.pools[key]
        for side, members in removed.items():
            direction = 'LONG' if side == 'low' else 'SHORT'
            price = min(p.price for p in members) if side == 'low' else max(p.price for p in members)
            raid = Raid(direction, now, price, c.low if side == 'low' else c.high, index,
                        tuple(p.pool_id for p in members))
            self.raids.append(raid)
            self.latest_raid[direction] = raid
            self.counts['liquidity_raids'] += 1
        applied = []
        proofs: list[dict] = []
        for e in sorted(self.events.get(index, ()), key=lambda e: e.event_time):
            if e.event_time > now:
                raise ValueError('event not yet known')
            applied.append(e)
            self.counts[e.kind.value] += 1
            if e.kind in (K.SWING_HIGH_CONFIRMED, K.SWING_LOW_CONFIRMED):
                side = 'high' if e.kind == K.SWING_HIGH_CONFIRMED else 'low'
                equal = any(p.side == side and p.price == e.price for p in self.pools.values())
                key = f'SWING:{e.level_id}'
                location = 'EXTERNAL' if self.structure is None or not min(self.structure['protected'], self.structure['extreme']) < e.price < max(self.structure['protected'], self.structure['extreme']) else 'INTERNAL'
                self.pools[key] = Pool(key, side, e.price, now, ('EQH' if side == 'high' else 'EQL') if equal else ('BSL' if side == 'high' else 'SSL'), location)
            event_dir = event_direction(e)
            if event_dir is not None:
                proof: dict = {'kind': e.kind.value, 'direction': event_dir, 'known_at': now,
                         'protected': e.level_price, 'extreme': e.price, 'level_id': e.level_id}
                proofs.append(proof)
                if e.kind in (K.BULLISH_STRUCTURE_BROKEN_BOS, K.BEARISH_STRUCTURE_BROKEN_BOS):
                    self.bos[event_dir] = proof
                    self.trend = TrendState.BROKEN
                    self.structure = None
                elif e.kind in (K.BULLISH_CONF_CONFIRMED, K.BEARISH_CONF_CONFIRMED):
                    proof['new_structure'] = dict(self.structure) if self.structure else None
                    self.conf[event_dir] = proof
                else:
                    self.trend = TrendState.BULLISH if event_dir == 'LONG' else TrendState.BEARISH
                    self.structure = proof
            if e.kind in (K.BULLISH_SFP_FORMATION_CONFIRMED, K.BEARISH_SFP_FORMATION_CONFIRMED):
                direction = 'LONG' if e.kind == K.BULLISH_SFP_FORMATION_CONFIRMED else 'SHORT'
                if e.sfp_pattern_extreme_price is not None:
                    self.sfps.append(Raid(direction, now, e.level_price, e.sfp_pattern_extreme_price,
                                          max(0, index - 1), tuple(f'SWING:{v}' for v in e.member_level_ids) or (f'SWING:{e.level_id}',), True))
        if index >= 2:
            a, b = self.candles[index - 2:index]
            gap_direction = 'LONG' if c.low > a.high else 'SHORT' if c.high < a.low else None
            if gap_direction is not None:
                low, high = (a.high, c.low) if gap_direction == 'LONG' else (c.high, a.low)
                gap = self._zone('FVG', gap_direction, low, high, now, index - 2, None)
                gap.structural_proof = self.structure.copy() if self.structure else None
                self.zones.append(gap)
                self.zone_registry[gap.zone_id] = gap
                self.counts['zone_FVG'] += 1
                origin = self.last_opposite.get(gap_direction)
                if origin is not None and origin < index - 1:
                    ob = self.candles[origin]
                    raids = [r for r in self.raids_after(ob.open_time) if r.direction == gap_direction]
                    if raids:
                        raid = raids[-1]
                        engulf = ((b.open <= ob.close and b.close >= ob.open and b.close > b.open) if gap_direction == 'LONG'
                                  else (b.open >= ob.close and b.close <= ob.open and b.close < b.open))
                        body = abs(ob.close - ob.open)
                        dominance = body > ob.high - ob.low - body
                        # DOC19: the OB candle itself raids the old high/low/wick.
                        # A later raid can qualify the broader forming D/S move,
                        # but must not silently manufacture an OB candle.
                        candle_raid = next((r for r in reversed(raids) if r.candle_index == origin), None)
                        kind = 'ORDER_BLOCK' if engulf and dominance and candle_raid is not None else 'DEMAND' if gap_direction == 'LONG' else 'SUPPLY'
                        if kind == 'ORDER_BLOCK':
                            assert candle_raid is not None
                            raid = candle_raid
                        aliases = ('DEMAND' if gap_direction == 'LONG' else 'SUPPLY',) if kind == 'ORDER_BLOCK' else ()
                        candidate = self._zone(kind, gap_direction, ob.low, ob.high, now, origin, raid, aliases=aliases)
                        if (kind, origin) not in self.origins:
                            self.origins.add((kind, origin))
                            self.pending.append(candidate)
                for _, old in self.broken_obs:
                    if old.direction != gap_direction:
                        direction = gap_direction
                        recent = [r for r in self.raids_after(old.known_at) if r.direction == direction]
                        if recent:
                            breaker = self._zone('BREAKER', direction, old.low, old.high, now, old.origin_index, recent[-1])
                            breaker.stop_extreme = min(c.low, recent[-1].extreme) if direction == 'LONG' else max(c.high, recent[-1].extreme)
                            self.pending.append(breaker)
        # Absorption uses a completed close beyond the whole manipulation candle.
        for direction in ('LONG', 'SHORT'):
            latest_raid = self.latest_raid.get(direction)
            if latest_raid is not None and latest_raid.known_at < now:
                raid = latest_raid
                origin_c = self.candles[raid.candle_index]
                if sign(direction) * (c.close - raid.extreme) < 0:
                    del self.latest_raid[direction]
                    continue
                absorbed = c.close > origin_c.high if direction == 'LONG' else c.close < origin_c.low
                if absorbed and ('MANIPULATION', raid.candle_index) not in self.origins:
                    self.origins.add(('MANIPULATION', raid.candle_index))
                    self.pending.append(self._zone('STB' if direction == 'LONG' else 'BTS', direction,
                                                   origin_c.low, origin_c.high, now, raid.candle_index, raid,
                                                   aliases=('MANIPULATION',)))
        for z in list(self.pending):
            if z.invalidated_at is not None:
                self.pending.remove(z)
                continue
            pending_proof = next((p for p in proofs if p['direction'] == z.direction and p['known_at'] >= z.formed_at), None)
            if pending_proof is not None:
                self._qualify(z, pending_proof)
                self.pending.remove(z)
        for e in self.range_events.get(index, ()):
            if e.kind not in (K.BULLISH_SFP_FORMATION_CONFIRMED, K.BEARISH_SFP_FORMATION_CONFIRMED) or e.range_id not in self.range_bounds:
                continue
            low, high, known, causal_id = self.range_bounds[e.range_id]
            if known > now or e.event_time > now or e.sfp_pattern_extreme_price is None:
                continue
            direction = 'LONG' if e.kind == K.BULLISH_SFP_FORMATION_CONFIRMED else 'SHORT'
            raid = Raid(direction, now, e.level_price, e.sfp_pattern_extreme_price, max(0, index - 1), (f'RANGE:{causal_id}',), True)
            z = self._zone('RANGE_POI', direction, low, high, now, index - 1, raid)
            z.leg_low, z.leg_high = low, high
            z.range_id = causal_id
            z.first_test = z.last_test = now
            z.test_count = 1
            z.structural_proof = {'kind': 'IMPULSE_BOUNDARIES_MIDPOINT_DEVIATION_RECLAIM', 'known_at': known}
            self.zones.append(z)
            self.zone_registry[z.zone_id] = z
            touched.append(z)
            self.counts['zone_RANGE_POI'] += 1
        if c.close < c.open:
            self.last_opposite['LONG'] = index
        if c.close > c.open:
            self.last_opposite['SHORT'] = index
        # Fresh-only zones remain in the registry for provenance/cancellation,
        # but cannot remain active targets after their first visit.
        self.zones = [z for z in self.zones if z.invalidated_at is None
                      and (z.first_test is None or z.kind in ('ORDER_BLOCK', 'RANGE_POI'))]
        return touched, applied

    def target(self, direction: str, entry: float, now: datetime) -> Zone | None:
        s = sign(direction)
        opposite = 'SHORT' if s == 1 else 'LONG'
        eligible = [z for z in self.zones if z.direction == opposite and z.kind != 'RANGE_POI'
                    and z.fresh(now) and s * ((z.low if s == 1 else z.high) - entry) > 0]
        return min(eligible, key=lambda z: (s * (z.low if s == 1 else z.high), z.zone_id), default=None)


@dataclass
class Setup:
    setup_id: str
    htf: int
    ltf: int
    poi: Zone
    interaction_at: datetime
    stages: set[str] = field(default_factory=set)
    invalidated_at: datetime | None = None
    ready_id: str | None = None
    reason: str = 'WAIT_LTF_RAID_BOS_NEW_STRUCTURE_CONF'


@dataclass(frozen=True)
class SourceSignal:
    signal_id: str
    setup_id: str
    symbol: str
    known_at: datetime
    direction: str
    htf: int
    ltf: int
    setup_type: str
    poi_type: str
    entry: float
    stop: float
    targets: tuple[float, ...]
    fractions: tuple[float, ...]
    evidence: dict
    trade_entry_allowed: bool = False

    def __post_init__(self) -> None:
        s = sign(self.direction)
        if self.trade_entry_allowed is not False:
            raise ValueError('live admission is forbidden')
        if not self.targets or len(self.targets) != len(self.fractions) or abs(sum(self.fractions) - 1) > 1e-10:
            raise ValueError('invalid source exits')
        if s * (self.entry - self.stop) <= 0 or any(s * (t - self.entry) <= 0 for t in self.targets):
            raise ValueError('invalid entry/SL/target geometry')
        if any(v <= 0 for v in self.fractions):
            raise ValueError('invalid partial fraction')


class SourceEngine:
    def __init__(self, symbol: str, series: dict[int, SourceSeries]):
        self.symbol, self.series = symbol, series
        self.setups: list[Setup] = []
        self.active_setups: list[Setup] = []
        self.funnel: Counter = Counter()
        self.blockers: Counter = Counter()
        self.signals: list[SourceSignal] = []
        self.cancellations: list[dict] = []
        self.decisions: list[dict] = []
        self._cancelled: set[str] = set()

    def _stage(self, setup: Setup, name: str) -> None:
        if name not in setup.stages:
            setup.stages.add(name)
            self.funnel[name] += 1

    def _cancel(self, setup: Setup, now: datetime, reason: str) -> None:
        setup.invalidated_at = now
        setup.reason = reason
        if setup.ready_id is not None and setup.ready_id not in self._cancelled:
            self._cancelled.add(setup.ready_id)
            self.cancellations.append({'signal_id': setup.ready_id, 'known_at': now, 'reason': reason})

    def advance(self, tf: int, index: int) -> None:
        series = self.series[tf]
        # Target pruning cannot stop lifecycle observation of an active context.
        # Watch shared zones once even when several mappings use the same POI.
        series.context_watches = {s.poi.zone_id: s.poi for s in self.active_setups
                                 if s.htf == tf and s.invalidated_at is None}
        touched, events = series.advance(index)
        now = series.candles[index].close_time
        # A raid candle can be OB, D/S and STB/BTS simultaneously. One physical
        # first interaction produces one context, with semantic aliases retained.
        priority = {'ORDER_BLOCK': 0, 'BREAKER': 1, 'DEMAND': 2, 'SUPPLY': 2,
                    'STB': 3, 'BTS': 3, 'MANIPULATION': 4, 'FVG': 5, 'RANGE_POI': 0}
        physical: dict[tuple, Zone] = {}
        for candidate in sorted(touched, key=lambda p: (priority[p.kind], p.zone_id)):
            key = (candidate.direction, candidate.origin_index, candidate.low, candidate.high, candidate.range_id)
            if key in physical:
                chosen = physical[key]
                chosen.aliases = tuple(sorted((set(chosen.aliases) | set(candidate.aliases) | {candidate.kind}) - {chosen.kind}))
            else:
                physical[key] = candidate
        for z in physical.values():
            if z.kind == 'FVG' and (z.raid is None or z.structural_proof is None):
                continue
            if z.invalidated_at is not None or z.raid is None:
                continue
            self.funnel['source_contexts'] += 1
            for htf, ltf in MAPPINGS:
                if htf != tf:
                    continue
                setup_id = identity(self.symbol, htf, ltf, z.zone_id, now)
                setup = Setup(setup_id, htf, ltf, z, now)
                self.setups.append(setup)
                self.active_setups.append(setup)
                self._stage(setup, 'setups')
        # Apply setup invalidation on any native HTF update, separately from READY.
        for setup in self.active_setups:
            if setup.invalidated_at is not None:
                continue
            h = self.series[setup.htf]
            z = setup.poi
            if z.invalidated_at is not None and z.invalidated_at <= now:
                self._cancel(setup, now, 'HTF_POI_BODY_INVALIDATION')
                continue
            if z.test_count > 1 and z.kind in ('DEMAND', 'SUPPLY'):
                self._cancel(setup, now, 'DEMAND_SUPPLY_SECOND_VISIT_NOT_FRESH')
                continue
            if z.test_count > 1 and z.kind == 'ORDER_BLOCK':
                # The registered primary sample is first-test only. The separate
                # Zone.test_allowed contract exposes the secondary repeat-OB
                # exception without extending it to D/S or certifying missing SW9.
                self._cancel(setup, now, 'PRIMARY_FIRST_TEST_OB_REPEAT_SECONDARY_ONLY')
                continue
            if tf == setup.htf and z.raid is not None:
                c = series.candles[index]
                if sign(z.direction) * (c.close - z.raid.extreme) < 0:
                    self._cancel(setup, now, 'HTF_RAID_EXTREME_BODY_INVALIDATION')
                    continue
            expected = TrendState.BULLISH if z.direction == 'LONG' else TrendState.BEARISH
            if tf == setup.htf and h.trend not in (expected, TrendState.BROKEN, TrendState.UNKNOWN) and z.kind != 'RANGE_POI':
                self._cancel(setup, now, 'HTF_FLOW_DIRECTION_CHANGED')
                continue
            if setup.ready_id is not None:
                if tf == setup.ltf and series.trend != expected:
                    self._cancel(setup, now, 'CONFIRMED_LTF_STRUCTURE_BROKEN')
                    continue
                if tf == setup.htf and h.trend != expected and z.kind != 'RANGE_POI':
                    self._cancel(setup, now, 'ACTIVE_HTF_STRUCTURE_BROKEN')
                    continue
                signal = next(s for s in self.signals if s.signal_id == setup.ready_id)
                destination = signal.evidence['fta']['zone_id']
                if any((p := t.zone_registry.get(destination)) is not None and p.first_test is not None and p.first_test <= now
                       for t in (self.series[setup.htf], self.series[setup.ltf])):
                    self._cancel(setup, now, 'FLOW_DESTINATION_TESTED')
                continue
            if setup.ltf != tf or not events:
                continue
            self._evaluate(setup, now)
        self.active_setups = [s for s in self.active_setups if s.invalidated_at is None]

    def _evaluate(self, setup: Setup, now: datetime) -> None:
        l, h, z = self.series[setup.ltf], self.series[setup.htf], setup.poi
        direction = z.direction
        if z.raid is None:
            setup.reason = 'WAIT_HTF_RAID_PROVENANCE'
            return
        s = sign(direction)
        local_raids = [r for r in l.raids_after(setup.interaction_at) if r.direction == direction]
        bos = l.bos.get(direction)
        conf = l.conf.get(direction)
        structure = conf.get('new_structure') if conf else None
        expected = TrendState.BULLISH if s == 1 else TrendState.BEARISH
        if not local_raids or bos is None or conf is None or structure is None or l.trend != expected:
            setup.reason = 'WAIT_LTF_RAID_BOS_NEW_STRUCTURE_CONF'
            return
        raid = next((r for r in reversed(local_raids) if r.known_at <= bos['known_at']), None)
        if raid is None or not setup.interaction_at <= raid.known_at <= bos['known_at'] < structure['known_at'] <= conf['known_at'] <= now:
            setup.reason = 'WAIT_CAUSAL_RAID_BOS_NEW_STRUCTURE_CONF_ORDER'
            return
        if s * (l.candles[l.index].close - raid.extreme) <= 0:
            setup.reason = 'WAIT_LTF_RAID_INVALIDATED'
            return
        self._stage(setup, 'qualified_structure')
        local_zones = [p for p in l.zones if p.kind != 'RANGE_POI' and p.direction == direction and p.fresh(now)
                       and raid.known_at <= p.formed_at <= p.known_at <= now and p.structural_proof is not None]
        if not local_zones:
            setup.reason = 'WAIT_NEW_FRESH_LTF_POI'
            return
        local = max(local_zones, key=lambda p: (p.known_at, p.kind != 'FVG', p.zone_id))
        entry = local.high if s == 1 else local.low
        stop = min(local.low, raid.extreme, local.stop_extreme or local.low) if s == 1 else max(local.high, raid.extreme, local.stop_extreme or local.high)
        adverse = opposing_liquidity(list(l.pools.values()) + list(h.pools.values()), direction, entry, stop)
        if adverse:
            setup.reason = 'WAIT_MEANINGFUL_LIQUIDITY_AGAINST_SETUP'
            return
        self._stage(setup, 'liquidity_passed')
        self._stage(setup, 'poi_passed')
        destinations = [p for t in (h, l) if (p := t.target(direction, entry, now)) is not None]
        if not destinations:
            setup.reason = 'WAIT_FIRST_OPPOSING_POI_FTA'
            return
        destination = min(destinations, key=lambda p: (s * (p.low if s == 1 else p.high), p.zone_id))
        if z.kind != 'RANGE_POI' and (h.trend != expected or h.structure is None):
            setup.reason = 'WAIT_ACTIVE_HTF_ORDER_FLOW'
            return
        self._stage(setup, 'order_flow_passed')
        good_pd, ote, retracement = pd_location(direction, entry, z.leg_low, z.leg_high)
        if not good_pd:
            setup.reason = 'WAIT_DISCOUNT_OR_PREMIUM'
            return
        self._stage(setup, 'pd_passed')
        fta = destination.low if s == 1 else destination.high
        targets: tuple[float, ...] = (fta,)
        fractions: tuple[float, ...] = (1.0,)
        exit_kind = 'FULL_FTA_SOURCE_INTERPRETATION'
        if z.kind == 'RANGE_POI':
            # Exact boundary is the most conservative available quote; "inside"
            # uses the adjacent float toward the interior, not a fitted offset.
            import math
            boundary = math.nextafter(z.high if s == 1 else z.low, z.low if s == 1 else z.high)
            if s * (fta - boundary) > 0:
                targets, fractions = (boundary, fta), (0.8, 0.2)
                exit_kind = 'RANGE_80_INSIDE_20_EXTERNAL_FTA'
            else:
                first = min(fta, boundary) if s == 1 else max(fta, boundary)
                # Source permits declining the optional breakout remainder;
                # preserve the80/20 accounting even when both close inside.
                targets, fractions = (first, first), (0.8, 0.2)
                exit_kind = 'RANGE_EARLIER_FTA_OPTIONAL_REMAINDER_CLOSED'
        if s * (l.candles[l.index].close - entry) <= 0 or s * (entry - stop) <= 0:
            setup.reason = 'WAIT_PROPER_SIDE_LIMIT_APPROACH'
            return
        # All evidence is copied at this observation, never a future mutable zone.
        proof = {'htf_poi': asdict(z), 'ltf_poi': asdict(local), 'liquidity_sweep': asdict(raid),
                 'bos': dict(bos), 'new_structure': dict(structure), 'conf': dict(conf),
                 'meaningful_liquidity_against': adverse, 'fta': asdict(destination),
                 'order_flow': {'direction': direction, 'structure': dict(h.structure or structure),
                                'raid': asdict(z.raid), 'destination_poi_id': destination.zone_id,
                                'known_at': now, 'invalid_on': ['STRUCTURE_BREAK', 'RAID_BODY_VIOLATION', 'DESTINATION_TEST']},
                 'premium_discount': {'low': z.leg_low, 'high': z.leg_high, 'retracement': retracement,
                                      'ote_confluence': ote}, 'exit_policy': exit_kind,
                 'classification': 'SOURCE_RULES_WITH_DECLARED_INTERPRETATIONS',
                 'ltf_scope': 'SECONDARY_CONSERVATIVE_1_TO_15' if setup.ltf <= 15 else 'ANY_TF_INTERPRETATION',
                 'stop_policy': 'BEHIND_LOCAL_POI_AND_REACTION_RAID_NO_AUTOMATIC_BE'}
        signal_id = identity(setup.setup_id, local.zone_id, now)
        signal = SourceSignal(signal_id, setup.setup_id, self.symbol, now, direction, setup.htf, setup.ltf,
                              'RANGE_DEVIATION' if z.kind == 'RANGE_POI' else 'HTF_POI_LTF_RAID_BOS_CONF',
                              z.kind, entry, stop, targets, fractions, proof)
        self.signals.append(signal)
        setup.ready_id = signal_id
        setup.reason = 'READY'
        self._stage(setup, 'READY')
        self.decisions.append({'setup_id': setup.setup_id, 'signal_id': signal_id, 'known_at': now,
                               'status': 'READY', 'trade_entry_allowed': False})

    def finish(self) -> dict:
        self.blockers = Counter(s.reason for s in self.setups)
        return {'symbol': self.symbol, 'funnel': dict(self.funnel), 'latest_setup_reasons': dict(self.blockers),
                'series': {str(tf): dict(s.counts) for tf, s in self.series.items()},
                'trade_entry_allowed': False}
