from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from crypto_bot.strategy.causal_objects import CausalObjectRegistry, CausalSourceObject, RejectionCategory, SourceObjectType
from crypto_bot.strategy.profile import PURE_SOURCE_CONFIG, PolicyClass, StrategyProfile, StrategyRuntimeConfig

_ZONE_TYPE_MAP = {"ORDER_BLOCK": SourceObjectType.ORDER_BLOCK, "BREAKER": SourceObjectType.BREAKER,
                  "STB": SourceObjectType.STB_BTS, "BTS": SourceObjectType.STB_BTS,
                  "MANIPULATION": SourceObjectType.STB_BTS, "RANGE_POI": SourceObjectType.RANGE,
                  "FVG": SourceObjectType.FVG, "DEMAND": SourceObjectType.POI, "SUPPLY": SourceObjectType.POI}

@dataclass
class PureSourceRuntime:
    """Stage-1 entry point: isolate policy and persist SOURCE objects apart from trade admission."""
    symbol: str
    series: Mapping[int, Any]
    config: StrategyRuntimeConfig = PURE_SOURCE_CONFIG
    engine_factory: Callable[[str, Mapping[int, Any]], Any] | None = None

    def __post_init__(self) -> None:
        if self.config.strategy_profile != StrategyProfile.PURE_SOURCE:
            raise ValueError("PureSourceRuntime requires strategy_profile=PURE_SOURCE")
        self.config.__post_init__()
        self.registry = CausalObjectRegistry()
        self._legacy_ids: dict[tuple[str, str], str] = {}
        if self.engine_factory is None:
            from crypto_bot.strategy.source_engine import SourceEngine
            self.engine = SourceEngine(self.symbol, dict(self.series))
        else:
            self.engine = self.engine_factory(self.symbol, self.series)

    @property
    def trade_entry_allowed(self) -> bool:
        return False

    def apply_policy(self, policy_id: str, policy_class: PolicyClass) -> None:
        self.config = self.config.record_policy(policy_id, policy_class)

    def advance(self, timeframe: int, index: int) -> None:
        series = self.series[timeframe]
        candle = series.candles[index]
        if not candle.is_closed:
            raise ValueError("unfinished candle is forbidden in PURE_SOURCE")
        self.engine.advance(timeframe, index)
        now = candle.close_time
        self._capture_series(timeframe, now)
        self._capture_setups(now)

    def finish(self) -> dict:
        result = dict(self.engine.finish())
        result["strategy_profile"] = StrategyProfile.PURE_SOURCE.value
        result["trade_entry_allowed"] = False
        result["causal_object_count"] = len(self.registry)
        return result

    def _capture_series(self, timeframe: int, now: datetime) -> None:
        series = self.series[timeframe]
        for pool in getattr(series, "pools", {}).values():
            if pool.known_at <= now:
                self._register_pool(timeframe, pool)
        for zone in getattr(series, "zone_registry", {}).values():
            if zone.known_at <= now:
                self._register_zone(timeframe, zone, now)
        for event in getattr(series, "events", {}).get(getattr(series, "index", -1), ()):
            if event.event_time <= now:
                self._register_event(timeframe, event)
        for range_id, value in getattr(series, "range_bounds", {}).items():
            lower, upper, known_at, causal_id = value
            if known_at <= now:
                self._register_range(timeframe, range_id, lower, upper, known_at, causal_id)

    def _register_pool(self, timeframe: int, pool: Any) -> None:
        key = ("pool", str(pool.pool_id))
        if key in self._legacy_ids:
            return
        obj = CausalSourceObject.formed(object_type=SourceObjectType.LIQUIDITY_POOL, symbol=self.symbol,
            timeframe=timeframe, direction=None, formation_at=pool.known_at, known_at=pool.known_at,
            identity_parts={"legacy_pool_id": pool.pool_id, "side": pool.side, "price": pool.price, "origin": pool.origin},
            source_rule_ids=("SOURCE_LIQUIDITY_GEOMETRY",),
            provenance="legacy SourceSeries pool adapted at causal known_at")
        self.registry.add(obj); self._legacy_ids[key] = obj.object_id

    def _register_zone(self, timeframe: int, zone: Any, now: datetime) -> None:
        key = ("zone", str(zone.zone_id)); object_id = self._legacy_ids.get(key)
        if object_id is None:
            obj = CausalSourceObject.formed(object_type=_ZONE_TYPE_MAP.get(zone.kind, SourceObjectType.POI),
                symbol=self.symbol, timeframe=timeframe, direction=zone.direction,
                formation_at=zone.formed_at, known_at=zone.known_at,
                identity_parts={"legacy_zone_id": zone.zone_id, "kind": zone.kind,
                                "origin_index": zone.origin_index, "low": zone.low, "high": zone.high},
                source_rule_ids=("SOURCE_ZONE_FORMATION",),
                provenance="legacy SourceSeries zone adapted without changing trading semantics")
            self.registry.add(obj); self._legacy_ids[key] = obj.object_id; object_id = obj.object_id
        obj = self.registry.get(object_id); invalidated_at = getattr(zone, "invalidated_at", None)
        if invalidated_at is not None and invalidated_at <= now and obj.invalidated_at is None:
            self.registry.replace(obj.invalidate(invalidated_at, "SOURCE_ZONE_INVALIDATION"))

    def _register_event(self, timeframe: int, event: Any) -> None:
        name = event.kind.value
        if "SWING_" in name: object_type = SourceObjectType.SWING
        elif "SFP_" in name: object_type = SourceObjectType.SFP
        elif "LIQUIDITY" in name: object_type = SourceObjectType.LIQUIDITY_POOL
        elif "STRUCTURE" in name or "CONF_" in name: object_type = SourceObjectType.STRUCTURE
        else: return
        key = ("event", f"{timeframe}:{name}:{event.candle_index}:{event.level_id}:{event.event_time.isoformat()}")
        if key in self._legacy_ids: return
        obj = CausalSourceObject.formed(object_type=object_type, symbol=self.symbol, timeframe=timeframe,
            direction=None, formation_at=event.event_time, known_at=event.event_time,
            identity_parts={"event_kind": name, "candle_index": event.candle_index, "level_id": event.level_id,
                            "level_price": event.level_price, "price": event.price, "episode_id": event.episode_id},
            source_rule_ids=("SOURCE_MARKET_EVENT",), provenance="MarketAnalysis causal event")
        self.registry.add(obj); self._legacy_ids[key] = obj.object_id

    def _register_range(self, timeframe: int, range_id: Any, lower: float, upper: float,
                        known_at: datetime, causal_id: str) -> None:
        key = ("range", str(causal_id))
        if key in self._legacy_ids: return
        obj = CausalSourceObject.formed(object_type=SourceObjectType.RANGE, symbol=self.symbol,
            timeframe=timeframe, direction=None, formation_at=known_at, known_at=known_at,
            identity_parts={"legacy_range_id": range_id, "causal_id": causal_id, "lower": lower, "upper": upper},
            source_rule_ids=("SOURCE_RANGE_GEOMETRY",),
            technical_normalization_ids=("TN_LEGACY_RANGE_FORMATION_AT_CAUSAL_KNOWN_AT",),
            provenance="legacy range adapter; exact earlier physical formation is not backfilled")
        self.registry.add(obj); self._legacy_ids[key] = obj.object_id

    def _capture_setups(self, now: datetime) -> None:
        for setup in getattr(self.engine, "setups", ()):
            if setup.interaction_at > now: continue
            poi_id = self._legacy_ids.get(("zone", str(setup.poi.zone_id)))
            physical_key = ("physical", f"{setup.poi.zone_id}:{setup.interaction_at.isoformat()}")
            physical_id = self._legacy_ids.get(physical_key)
            if physical_id is None:
                physical = CausalSourceObject.formed(object_type=SourceObjectType.PHYSICAL_IDEA,
                    symbol=self.symbol, timeframe=setup.htf, direction=setup.poi.direction,
                    formation_at=setup.interaction_at, known_at=setup.interaction_at,
                    identity_parts={"poi_zone_id": setup.poi.zone_id, "interaction_at": setup.interaction_at},
                    source_rule_ids=("SOURCE_PHYSICAL_CONTEXT",), parent_object_ids=(poi_id,) if poi_id else (),
                    provenance="physical idea identity excludes branch, score and future outcome")
                self.registry.add(physical); physical_id = physical.object_id; self._legacy_ids[physical_key] = physical_id
            setup_key = ("setup", str(setup.setup_id)); setup_object_id = self._legacy_ids.get(setup_key)
            if setup_object_id is None:
                obj = CausalSourceObject.formed(object_type=SourceObjectType.SETUP, symbol=self.symbol,
                    timeframe=f"{setup.htf}/{setup.ltf}", direction=setup.poi.direction,
                    formation_at=setup.interaction_at, known_at=setup.interaction_at,
                    identity_parts={"physical_idea_id": physical_id, "htf": setup.htf, "ltf": setup.ltf},
                    source_rule_ids=("SOURCE_SETUP_ASSEMBLY_LEGACY",),
                    parent_object_ids=tuple(v for v in (physical_id, poi_id) if v),
                    provenance="legacy setup adapted; trade eligibility remains independent")
                self.registry.add(obj); setup_object_id = obj.object_id; self._legacy_ids[setup_key] = setup_object_id
            obj = self.registry.get(setup_object_id)
            if setup.ready_id is not None and not obj.trade_eligible:
                signal = next((s for s in getattr(self.engine, "signals", ()) if s.signal_id == setup.ready_id), None)
                ready_at = signal.known_at if signal is not None else now
                self.registry.replace(obj.set_trade_eligible(True, ready_at, "SOURCE_CHAIN_READY")); obj = self.registry.get(setup_object_id)
            invalidated_at = getattr(setup, "invalidated_at", None)
            if invalidated_at is not None and invalidated_at <= now and obj.status.value != "CANCELLED":
                category = RejectionCategory.CANCELLED_AFTER_READY if setup.ready_id is not None else RejectionCategory.SETUP_REJECTED_SOURCE
                if setup.ready_id is not None:
                    self.registry.replace(obj.cancel(invalidated_at, f"{category.value}:{setup.reason}"))
                else:
                    self.registry.replace(obj.reject(category, invalidated_at, setup.reason))
