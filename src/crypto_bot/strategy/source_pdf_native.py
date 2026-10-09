"""Primary PDF causal source interpretation, native observation timing v2.

See SOURCE_PDF_PROTOCOL.md and SOURCE_PDF_NATIVE_PROTOCOL.md.

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
import math
from typing import Sequence

from crypto_bot.common.models import Candle
from crypto_bot.strategy.market_analysis import MarketAnalysisReport, MarketEvent, MarketEventKind as K, TrendState
from crypto_bot.strategy.range_engine import RangeAnalysisReport
from crypto_bot.strategy.source_engine import SourceSignal

MAPPINGS = ((15, 5), (60, 5), (60, 15), (240, 5), (240, 15))
ANY_TF_MAPPINGS = ((240, 60),)
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
    move_end_index: int | None = None
    external_poi: dict | None = None
    range_reclaim_at: datetime | None = None
    range_retest_at: datetime | None = None
    visit_started_at: datetime | None = None
    confluence: dict = field(default_factory=dict)
    native_touch_clock: bool = False
    last_native_test_at: datetime | None = None

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


def poi_entry_policy(zone: Zone, reaction: Raid) -> tuple[float, float, str, str]:
    """Registered type-specific choices; no outcomes are inputs."""
    s = sign(zone.direction)
    edge = zone.high if s == 1 else zone.low
    extreme = math.nextafter(zone.low, -math.inf) if s == 1 else math.nextafter(zone.high, math.inf)
    if zone.kind == 'ORDER_BLOCK':
        return edge, extreme, 'OB_PROXIMAL_WICK_BOUNDARY', 'OB_FULL_WICK_EXTREME'
    if zone.kind == 'BREAKER':
        stop = math.nextafter(min(extreme, zone.stop_extreme or extreme, reaction.extreme), -math.inf) if s == 1 else math.nextafter(max(extreme, zone.stop_extreme or extreme, reaction.extreme), math.inf)
        return edge, stop, 'BREAKER_PROXIMAL_BOUNDARY', 'CONSERVATIVE_BREAKING_SWEEP_EXTREME'
    if zone.kind in ('STB', 'BTS', 'MANIPULATION'):
        stop = min(extreme, zone.raid.extreme if zone.raid else extreme) if s == 1 else max(extreme, zone.raid.extreme if zone.raid else extreme)
        return (zone.low + zone.high) / 2, stop, 'ABSORBED_MANIPULATION_MIDPOINT', 'MANIPULATION_FULL_WICK_SWEEP'
    if zone.kind in ('DEMAND', 'SUPPLY'):
        return (zone.low + zone.high) / 2, extreme, 'DS_LAST_MOVE_MIDPOINT', 'DS_FULL_MOVE_EXTREME'
    if zone.kind == 'FVG':
        stop = math.nextafter(reaction.extreme, -math.inf if s == 1 else math.inf)
        return (zone.low + zone.high) / 2, stop, 'FVG_MIDPOINT_WITH_INDEPENDENT_CONTEXT', 'REACTION_RAID_EXTREME'
    raise ValueError('no registered entry policy for POI type')


def liquidity_roles(h, l, context: Zone, direction: str, entry: float, now: datetime) -> list[dict]:
    """Whole structural context and equal pools, independent of selected SL."""
    s = sign(direction)
    low, high = context.leg_low, context.leg_high
    if h.flow is not None:
        low = min(low, h.flow['structure']['protected'], h.flow['structure']['extreme'])
        high = max(high, h.flow['structure']['protected'], h.flow['structure']['extreme'])
    result = []
    for series in (h, l):
        for p in series.pools.values():
            if p.known_at > now:
                continue
            adverse_side = p.side == ('low' if s == 1 else 'high') and s * (entry - p.price) > 0
            against = adverse_side and low <= p.price <= high
            destination = p.side == ('high' if s == 1 else 'low') and s * (p.price - entry) > 0
            result.append({**asdict(p), 'timeframe': series.tf,
                           'role': 'AGAINST_SETUP' if against else 'DESTINATION_OR_FUEL' if destination else 'UNRELATED_WITHOUT_CONTEXT',
                           'context_low': low, 'context_high': high})
    return result


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
        self.range_pending: list[Zone] = []
        self.range_audit: list[dict] = []
        self.swing_history: dict[str, list[dict]] = {'high': [], 'low': []}
        self.flow: dict | None = None
        self.flow_history: list[dict] = []
        self.last_flow_conf: datetime | None = None
        self.structural_key_history: dict[str, list[dict]] = {'LONG': [], 'SHORT': []}
        self.day: object = None
        self.day_high = self.day_low = 0.0
        self.day_complete = False
        self.native_touch_clock = False

    def _zone(self, kind: str, direction: str, low: float, high: float, now: datetime,
              origin: int, raid: Raid | None, *, aliases: tuple[str, ...] = ()) -> Zone:
        c = self.candles[self.index]
        return Zone(identity(self.symbol, self.tf, kind, direction, origin, now, low, high), kind, direction,
                    low, high, now, now, origin, raid, min(low, c.low, raid.extreme if raid else low),
                    max(high, c.high, raid.extreme if raid else high), aliases=aliases,
                    native_touch_clock=self.native_touch_clock)

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

    def _demand_supply(self, c: Candle) -> None:
        # Independent last opposite move, with no FVG or failed-OB dependency.
        for direction in ('LONG', 'SHORT'):
            s = sign(direction)
            if s * (c.close - c.open) <= 0:
                continue
            end = self.last_opposite.get(direction, -1)
            if end < 0 or s * (self.candles[end].close - self.candles[end].open) >= 0:
                continue
            start = end
            while start > 0 and s * (self.candles[start - 1].close - self.candles[start - 1].open) < 0:
                start -= 1
            move = self.candles[start:end + 1]
            low, high = min(v.low for v in move), max(v.high for v in move)
            if s * (c.close - (high if s == 1 else low)) <= 0:
                continue
            raids = [r for r in self.raids_after(move[0].open_time)
                     if r.direction == direction and start <= r.candle_index <= end]
            kind = 'DEMAND' if s == 1 else 'SUPPLY'
            if not raids or (kind, start) in self.origins:
                continue
            self.origins.add((kind, start))
            zone = self._zone(kind, direction, low, high, c.close_time, start, raids[-1])
            zone.move_end_index = end
            self.pending.append(zone)

    def _range_contexts(self, c: Candle, touched: list[Zone]) -> None:
        now, index = c.close_time, self.index
        for z in list(self.range_pending):
            assert z.raid is not None
            if sign(z.direction) * (c.close - z.raid.extreme) <= 0:
                self.range_pending.remove(z)
                self.counts['range_invalidated_before_retest'] += 1
                continue
            inside = z.low < c.close < z.high
            if z.range_reclaim_at is None:
                if now > z.formed_at and inside:
                    z.range_reclaim_at = now
            elif now > z.range_reclaim_at and inside and (c.low <= z.low if z.direction == 'LONG' else c.high >= z.high):
                z.range_retest_at = z.known_at = now
                z.first_test = z.last_test = now
                z.test_count = 1
                self.zones.append(z)
                self.zone_registry[z.zone_id] = z
                touched.append(z)
                self.range_pending.remove(z)
                self.counts['zone_RANGE_POI'] += 1
        for e in self.range_events.get(index, ()):
            if e.kind not in (K.BULLISH_SFP_FORMATION_CONFIRMED, K.BEARISH_SFP_FORMATION_CONFIRMED) or e.range_id not in self.range_bounds:
                continue
            low, high, known, causal_id = self.range_bounds[e.range_id]
            if known > now or e.event_time > now or e.sfp_pattern_extreme_price is None:
                continue
            direction = 'LONG' if e.kind == K.BULLISH_SFP_FORMATION_CONFIRMED else 'SHORT'
            deviation = self.candles[max(0, index - 1)]
            relevant = [z for z in self.zone_registry.values() if z.kind not in ('FVG', 'RANGE_POI')
                        and z.direction == direction and z.known_at <= deviation.open_time
                        and (z.first_test is None or z.first_test >= deviation.open_time)
                        and z.invalidated_at is None
                        and (z.high <= low if direction == 'LONG' else z.low >= high)
                        and deviation.low <= z.high and deviation.high >= z.low]
            external = max(relevant, key=lambda z: (z.high if direction == 'LONG' else -z.low, z.zone_id), default=None)
            self.range_audit.append({'known_at': now, 'range_id': causal_id, 'low': low, 'high': high,
                                     'direction': direction, 'deviation_open': deviation.open_time,
                                     'external_poi': asdict(external) if external else None})
            if external is None:
                self.counts['range_sfp_without_required_external_poi'] += 1
                continue
            raid = Raid(direction, now, e.level_price, e.sfp_pattern_extreme_price,
                        max(0, index - 1), (f'RANGE:{causal_id}',), True)
            z = self._zone('RANGE_POI', direction, low, high, now, index - 1, raid)
            z.leg_low, z.leg_high, z.range_id = low, high, causal_id
            z.external_poi = asdict(external)
            z.structural_proof = {'kind': 'EXTERNAL_POI_DEVIATION_RECLAIM_BOUNDARY_RETEST', 'known_at': known}
            self.range_pending.append(z)

    def _update_flow(self, c: Candle, proofs: list[dict]) -> None:
        now = c.close_time
        if self.flow is not None and self.flow.get('invalidated_at') is None:
            f = self.flow
            destination = self.zone_registry.get(f['destination_poi']['zone_id'])
            reason = None
            if destination is None or destination.invalidated_at is not None or destination.first_test is not None:
                reason = 'GLOBAL_DESTINATION_TESTED_OR_INVALIDATED'
            elif self.trend != (TrendState.BULLISH if f['direction'] == 'LONG' else TrendState.BEARISH):
                reason = 'PROTECTED_STRUCTURE_BROKEN_OR_DIRECTION_CHANGED'
            elif sign(f['direction']) * (c.close - f['liquidity_work']['extreme']) <= 0:
                reason = 'FLOW_KEY_RAID_BODY_VIOLATION'
            if reason:
                f['invalidated_at'], f['invalidation_reason'] = now, reason
                self.counts['flow_invalidations'] += 1
        for proof in proofs:
            if proof['kind'] not in (K.BULLISH_CONF_CONFIRMED.value, K.BEARISH_CONF_CONFIRMED.value,
                                     K.BULLISH_STRUCTURE_CONFIRMED.value, K.BEARISH_STRUCTURE_CONFIRMED.value):
                continue
            direction, s = proof['direction'], sign(proof['direction'])
            keys = self.structural_key_history[direction]
            if not keys or (keys[-1]['protected'], keys[-1]['extreme']) != (proof['protected'], proof['extreme']):
                keys.append(dict(proof))
            # SW22 p6: the original global destination stays fixed until tested.
            if self.flow is not None and self.flow.get('invalidated_at') is None and self.flow['direction'] == direction:
                continue
            if self.last_flow_conf is not None and now <= self.last_flow_conf:
                continue
            self.last_flow_conf = now
            if len(keys) < 2 or self.structure is None:
                continue
            if s * (keys[-1]['extreme'] - keys[-2]['extreme']) <= 0 or s * (keys[-1]['protected'] - keys[-2]['protected']) <= 0:
                continue
            highs = self.swing_history['high']
            lows = self.swing_history['low']
            cause = None
            broken_key = None
            broken_at = None
            for r in reversed(self.raids):
                if r.direction != direction or not any(k.startswith('SWING:') for k in r.liquidity_ids):
                    continue
                rc = self.candles[r.candle_index]
                if s * (rc.close - r.price) <= 0:
                    continue
                # Break a causally known key structural extreme, not any tiny swing.
                previous = next((v for v in reversed(keys) if v['known_at'] < r.known_at), None)
                key = ({'price': previous['extreme'], 'known_at': previous['known_at'],
                        'level_id': previous['level_id']} if previous else None)
                if key is None:
                    continue
                body_break = next((v for v in self.candles[r.candle_index + 1:self.index + 1]
                                   if s * (v.close - key['price']) > 0), None)
                if body_break is not None:
                    cause, broken_key, broken_at = r, key, body_break.close_time
                    break
            if cause is None:
                continue
            assert broken_key is not None
            destination = self.target(direction, c.close, now, global_only=True)
            if destination is None:
                continue
            f = {'flow_id': identity(self.symbol, self.tf, direction, now, destination.zone_id),
                 'direction': direction, 'known_at': now, 'structure': dict(self.structure),
                 'sequence': {'structural_keys': keys[-2:], 'highs': highs[-2:], 'lows': lows[-2:]},
                 'key_test': {'price': cause.price, 'known_at': cause.known_at, 'reclaimed': True},
                 'liquidity_work': asdict(cause), 'broken_key': dict(broken_key),
                 'body_break_at': broken_at, 'conf': dict(proof),
                 'destination_poi': asdict(destination), 'invalidated_at': None}
            # A new CONF may update flow; each previous generation stays auditable.
            self.flow = f
            self.flow_history.append(f)
            self.counts['active_flow_generations'] += 1

    def _order_blocks(self, c: Candle) -> None:
        """SW9 p2: actual raid candle followed immediately by full absorption."""
        if self.index < 1:
            return
        origin = self.index - 1
        ob = self.candles[origin]
        for direction in ('LONG', 'SHORT'):
            s = sign(direction)
            raid = next((r for r in reversed(self.raids) if r.candle_index == origin and r.direction == direction), None)
            engulf = s * (ob.close - ob.open) < 0 and s * (c.close - c.open) > 0
            engulf = engulf and (c.open <= ob.close and c.close > ob.high if s == 1 else c.open >= ob.close and c.close < ob.low)
            if raid is None or not engulf or ('ORDER_BLOCK', origin) in self.origins:
                continue
            self.origins.add(('ORDER_BLOCK', origin))
            zone = self._zone('ORDER_BLOCK', direction, ob.low, ob.high, c.close_time, origin, raid)
            self.pending.append(zone)

    def _manipulations(self, c: Candle) -> None:
        """SW22 p2–4: absorb the entire key-to-sweep move, not just raid bar."""
        for direction in ('LONG', 'SHORT'):
            raid = self.latest_raid.get(direction)
            if raid is None or raid.known_at >= c.close_time:
                continue
            s = sign(direction)
            if s * (c.close - raid.extreme) < 0:
                del self.latest_raid[direction]
                continue
            side = 'high' if s == 1 else 'low'
            key = next((v for v in reversed(self.swing_history[side])
                        if v['known_at'] < raid.known_at and v['origin_index'] < raid.candle_index), None)
            if key is None:
                continue
            start = key['origin_index']
            move = self.candles[start:raid.candle_index + 1]
            low, high = min(v.low for v in move), max(v.high for v in move)
            absorbed = c.close > high if s == 1 else c.close < low
            if absorbed and ('MANIPULATION', raid.candle_index) not in self.origins:
                self.origins.add(('MANIPULATION', raid.candle_index))
                zone = self._zone('STB' if s == 1 else 'BTS', direction, low, high, c.close_time, start, raid,
                                  aliases=('MANIPULATION',))
                zone.move_end_index = raid.candle_index
                zone.confluence = {'source': 'SW22 p2–4', 'move_start_key': dict(key),
                                   'full_absorption_at': c.close_time}
                self.pending.append(zone)

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
            if overlap and not z.native_touch_clock:
                first = z.first_test is None
                # Count visits, not consecutive overlapping bars as repeated tests.
                if z.last_test != c.open_time:
                    z.test_count += 1
                    z.visit_started_at = now
                    if not first and z.kind == 'ORDER_BLOCK':
                        touched.append(z)
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
            if z.kind in ('DEMAND', 'SUPPLY') and z.formed_at < now and c.low <= z.high and c.high >= z.low:
                # A return while waiting for structural confirmation already tests D/S.
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
                self.swing_history[side].append({'side': side, 'price': e.price, 'known_at': now, 'level_id': e.level_id, 'origin_index': index - 1})
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
                # IMB is confluence for the already independently formed OB.
                for ob_zone in self.pending + self.zones:
                    if ob_zone.kind == 'ORDER_BLOCK' and ob_zone.direction == gap_direction and ob_zone.origin_index == index - 2:
                        ob_zone.confluence['imbalance'] = {'low': low, 'high': high, 'known_at': now}
                for _, old in self.broken_obs:
                    piercing = b.close > old.high if gap_direction == 'LONG' else b.close < old.low
                    crossed = b.open <= old.high if gap_direction == 'LONG' else b.open >= old.low
                    if old.direction != gap_direction and piercing and crossed:
                        direction = gap_direction
                        recent = [r for r in self.raids_after(old.known_at) if r.direction == direction]
                        if recent:
                            breaker = self._zone('BREAKER', direction, old.low, old.high, now, old.origin_index, recent[-1])
                            breaker.stop_extreme = min(c.low, recent[-1].extreme) if direction == 'LONG' else max(c.high, recent[-1].extreme)
                            self.pending.append(breaker)
        self._demand_supply(c)
        self._order_blocks(c)
        self._manipulations(c)
        for z in list(self.pending):
            if z.invalidated_at is not None:
                self.pending.remove(z)
                continue
            pending_proof = next((p for p in proofs if p['direction'] == z.direction and p['known_at'] >= z.formed_at), None)
            if pending_proof is not None:
                self._qualify(z, pending_proof)
                self.pending.remove(z)
        self._range_contexts(c, touched)
        self._update_flow(c, proofs)
        if c.close < c.open:
            self.last_opposite['LONG'] = index
        if c.close > c.open:
            self.last_opposite['SHORT'] = index
        # Fresh-only zones remain in the registry for provenance/cancellation,
        # but cannot remain active targets after their first visit.
        self.zones = [z for z in self.zones if z.invalidated_at is None
                      and (z.first_test is None or z.kind in ('ORDER_BLOCK', 'RANGE_POI'))]
        return touched, applied

    def target(self, direction: str, entry: float, now: datetime, *, global_only=False) -> Zone | None:
        s = sign(direction)
        opposite = 'SHORT' if s == 1 else 'LONG'
        eligible = [z for z in self.zones if z.direction == opposite and z.kind != 'RANGE_POI'
                    and (not global_only or z.kind != 'FVG')
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
    visit_number: int = 1




class SourceEngine:
    def __init__(self, symbol: str, series: dict[int, SourceSeries], *, mappings=MAPPINGS):
        self.symbol, self.series = symbol, series
        if 5 in series:
            for tf, owner in series.items():
                owner.native_touch_clock = tf > 5
        self.mappings = mappings
        self.setups: list[Setup] = []
        self.active_setups: list[Setup] = []
        self.funnel: Counter = Counter()
        self.blockers: Counter = Counter()
        self.signals: list[SourceSignal] = []
        self.cancellations: list[dict] = []
        self.decisions: list[dict] = []
        self._cancelled: set[str] = set()

    def _native_touches(self, candle: Candle) -> list[tuple[int, Zone]]:
        result = []
        for tf, owner in self.series.items():
            if tf <= 5:
                continue
            watched = {z.zone_id: z for z in owner.zones}
            watched.update(owner.context_watches)
            for z in watched.values():
                if z.kind == 'RANGE_POI' or z.known_at > candle.open_time or z.invalidated_at is not None:
                    continue
                if candle.low <= z.high and candle.high >= z.low:
                    first = z.first_test is None
                    new_visit = z.last_native_test_at != candle.open_time
                    if new_visit:
                        z.test_count += 1
                        z.visit_started_at = candle.close_time
                    z.last_test = z.last_native_test_at = candle.close_time
                    if first:
                        z.first_test = candle.close_time
                    if first or (new_visit and z.kind == 'ORDER_BLOCK'):
                        result.append((tf, z))
        return result

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
        observed = series.candles[index]
        touches = [(tf, z) for z in touched]
        if tf == 5:
            touches.extend(self._native_touches(observed))
        # A known global zone's first test can be observed on a smaller native
        # candle; waiting for the larger bar would incorrectly keep flow alive.
        for owner in self.series.values():
            flow = owner.flow
            if flow is None or flow.get('invalidated_at') is not None or tf > owner.tf or flow['known_at'] > observed.open_time:
                continue
            destination = flow['destination_poi']
            if observed.low <= destination['high'] and observed.high >= destination['low']:
                flow['invalidated_at'], flow['invalidation_reason'] = now, 'GLOBAL_DESTINATION_TESTED_NATIVE_LOWER_TF'
                owner.counts['flow_invalidations'] += 1
        # A raid candle can be OB, D/S and STB/BTS simultaneously. One physical
        # first interaction produces one context, with semantic aliases retained.
        priority = {'ORDER_BLOCK': 0, 'BREAKER': 1, 'DEMAND': 2, 'SUPPLY': 2,
                    'STB': 3, 'BTS': 3, 'MANIPULATION': 4, 'FVG': 5, 'RANGE_POI': 0}
        physical: dict[tuple, tuple[int, Zone]] = {}
        for owner_tf, candidate in sorted(touches, key=lambda p: (priority[p[1].kind], p[1].zone_id, p[0])):
            key = (owner_tf, candidate.direction, candidate.origin_index, candidate.low, candidate.high, candidate.range_id)
            if key in physical:
                _, chosen = physical[key]
                chosen.aliases = tuple(sorted((set(chosen.aliases) | set(candidate.aliases) | {candidate.kind}) - {chosen.kind}))
            else:
                physical[key] = (owner_tf, candidate)
        for owner_tf, z in physical.values():
            if z.kind == 'FVG' and (z.raid is None or z.structural_proof is None):
                continue
            if z.invalidated_at is not None or z.raid is None:
                continue
            self.funnel['source_contexts'] += 1
            for htf, ltf in self.mappings:
                if htf != owner_tf:
                    continue
                setup_id = identity(self.symbol, htf, ltf, z.zone_id, now)
                setup = Setup(setup_id, htf, ltf, z, z.formed_at if z.kind == 'RANGE_POI' else now, visit_number=z.test_count)
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
            if z.kind == 'ORDER_BLOCK' and z.test_count > setup.visit_number:
                self._cancel(setup, now, 'OB_NEW_VISIT_REQUIRES_NEW_LTF_REACTION')
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
                if h.flow is None or h.flow.get('invalidated_at') is not None or h.flow['direction'] != z.direction:
                    self._cancel(setup, now, 'GLOBAL_ORDER_FLOW_INACTIVE')
                    continue
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
                       and raid.known_at <= p.formed_at <= p.known_at <= now and p.structural_proof is not None
                       and p.structural_proof.get('direction') == direction
                       and bos['known_at'] <= p.structural_proof['known_at'] <= p.known_at
                       and (p.kind != 'ORDER_BLOCK' or (p.low <= z.high and p.high >= z.low))]
        if not local_zones:
            setup.reason = 'WAIT_NEW_FRESH_LTF_POI'
            return
        local = max(local_zones, key=lambda p: (p.known_at, p.kind != 'FVG', p.zone_id))
        entry, stop, entry_policy, stop_policy = poi_entry_policy(local, raid)
        roles = liquidity_roles(h, l, z, direction, entry, now)
        adverse = [p for p in roles if p['role'] == 'AGAINST_SETUP']
        if adverse:
            setup.reason = 'WAIT_MEANINGFUL_LIQUIDITY_AGAINST_SETUP'
            return
        self._stage(setup, 'liquidity_passed')
        self._stage(setup, 'poi_passed')
        destinations = [p for t in (h,) if (p := t.target(direction, entry, now)) is not None]
        if not destinations:
            setup.reason = 'WAIT_FIRST_OPPOSING_POI_FTA'
            return
        destination = min(destinations, key=lambda p: (s * (p.low if s == 1 else p.high), p.zone_id))
        if h.flow is None or h.flow['direction'] != direction or h.flow.get('invalidated_at') is not None:
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
        current_close = l.candles[l.index].close
        if s * (targets[0] - current_close) <= 0:
            setup.reason = 'WAIT_FTA_ALREADY_PASSED_AT_READY'
            return
        if s * (current_close - entry) <= 0 or s * (entry - stop) <= 0:
            setup.reason = 'WAIT_PROPER_SIDE_LIMIT_APPROACH'
            return
        # All evidence is copied at this observation, never a future mutable zone.
        proof = {'htf_poi': asdict(z), 'ltf_poi': asdict(local), 'liquidity_sweep': asdict(raid),
                 'bos': dict(bos), 'new_structure': dict(structure), 'conf': dict(conf),
                 'meaningful_liquidity_against': adverse, 'fta': asdict(destination),
                 'order_flow': json.loads(evidence_json(h.flow)),
                 'liquidity_roles': roles, 'entry_policy': entry_policy,
                 'premium_discount': {'low': z.leg_low, 'high': z.leg_high, 'retracement': retracement,
                                      'ote_confluence': ote}, 'exit_policy': exit_kind,
                 'classification': 'PRIMARY_PDF_SOURCE_RULES_WITH_DECLARED_INTERPRETATIONS',
                 'htf_interaction_at': setup.interaction_at, 'htf_visit_number': setup.visit_number,
                 'source_citations': ['SW5 p2–7', 'SW9 p2–16', 'SW11 p2–4,8', 'SW12 p15', 'SW22 p2–6'],
                 'ltf_scope': 'SECONDARY_CONSERVATIVE_1_TO_15' if setup.ltf <= 15 else 'ANY_TF_INTERPRETATION',
                 'stop_policy': stop_policy}
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
