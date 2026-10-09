from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Sequence, TypedDict

from crypto_bot.common.models import Candle
from crypto_bot.strategy.sfp import detect_sfp
from crypto_bot.strategy.structure import is_swing_high, is_swing_low


class StructureAnalysisMode(str, Enum):
    SOURCE_CONSERVATIVE = "SOURCE_CONSERVATIVE"
    TECHNICAL_RECOVERY = "TECHNICAL_RECOVERY"


class TrendState(str, Enum):
    UNKNOWN = "UNKNOWN"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    BROKEN = "BROKEN"


class _ActiveTransition(TypedDict):
    transition_id: int
    bos_kind: str
    bos_index: int
    bos_time: datetime
    from_trend: TrendState
    expected_trend: TrendState
    broken_protected_price: float
    broken_extreme_price: float | None
    post_bos_high_level_ids: list[int]
    post_bos_low_level_ids: list[int]
    selected_anchor_level_id: int | None
    selected_correction_level_id: int | None
    rejection_reasons: list[str]


@dataclass(frozen=True)
class TrendStateSegment:
    state: TrendState
    start_index: int
    end_index: int
    start_time: datetime
    end_time: datetime
    candle_count: int


@dataclass(frozen=True)
class StructureTransitionDiagnostic:
    transition_id: int
    bos_kind: str
    bos_index: int
    bos_time: datetime
    from_trend: TrendState
    expected_trend: TrendState
    broken_protected_price: float
    broken_extreme_price: float | None
    resolved_index: int | None
    resolved_time: datetime | None
    resolved_trend: TrendState | None
    resolution_mode: str
    broken_candles: int
    post_bos_high_level_ids: tuple[int, ...]
    post_bos_low_level_ids: tuple[int, ...]
    selected_anchor_level_id: int | None
    selected_correction_level_id: int | None
    rejection_reasons: tuple[str, ...]


class LiquidityState(str, Enum):
    ACTIVE = "ACTIVE"
    SWEPT = "SWEPT"
    CONSUMED = "CONSUMED"


class SweepEpisodeStatus(str, Enum):
    PENDING_NEXT_CANDLE = "PENDING_NEXT_CANDLE"
    CONSUMED_NO_SFP = "CONSUMED_NO_SFP"
    SFP_FORMED = "SFP_FORMED"
    AMBIGUOUS_DUAL_SIDE_SWEEP = "AMBIGUOUS_DUAL_SIDE_SWEEP"


class MarketEventKind(str, Enum):
    SWING_HIGH_CONFIRMED = "SWING_HIGH_CONFIRMED"
    SWING_LOW_CONFIRMED = "SWING_LOW_CONFIRMED"
    BULLISH_STRUCTURE_CONFIRMED = "BULLISH_STRUCTURE_CONFIRMED"
    BEARISH_STRUCTURE_CONFIRMED = "BEARISH_STRUCTURE_CONFIRMED"
    BULLISH_CONF_CONFIRMED = "BULLISH_CONF_CONFIRMED"
    BEARISH_CONF_CONFIRMED = "BEARISH_CONF_CONFIRMED"
    HIGH_LIQUIDITY_TAKEN = "HIGH_LIQUIDITY_TAKEN"
    LOW_LIQUIDITY_TAKEN = "LOW_LIQUIDITY_TAKEN"
    BULLISH_STRUCTURE_BROKEN_BOS = "BULLISH_STRUCTURE_BROKEN_BOS"
    BEARISH_STRUCTURE_BROKEN_BOS = "BEARISH_STRUCTURE_BROKEN_BOS"
    HIGH_LIQUIDITY_SWEEP_EPISODE = "HIGH_LIQUIDITY_SWEEP_EPISODE"
    LOW_LIQUIDITY_SWEEP_EPISODE = "LOW_LIQUIDITY_SWEEP_EPISODE"
    BEARISH_SFP_FORMATION_CONFIRMED = "BEARISH_SFP_FORMATION_CONFIRMED"
    BULLISH_SFP_FORMATION_CONFIRMED = "BULLISH_SFP_FORMATION_CONFIRMED"
    BEARISH_SFP_INVALIDATED_CLOSE = "BEARISH_SFP_INVALIDATED_CLOSE"
    BULLISH_SFP_INVALIDATED_CLOSE = "BULLISH_SFP_INVALIDATED_CLOSE"
    # Backward-compatible enum aliases. The output value now explicitly says FORMATION.
    BEARISH_SFP_CONFIRMED = "BEARISH_SFP_FORMATION_CONFIRMED"
    BULLISH_SFP_CONFIRMED = "BULLISH_SFP_FORMATION_CONFIRMED"


@dataclass(frozen=True)
class StructuralLevel:
    level_id: int
    side: str  # "high" | "low"
    price: float
    swing_index: int
    confirmed_index: int
    swing_time: datetime
    confirmed_time: datetime
    liquidity_state: LiquidityState = LiquidityState.ACTIVE
    liquidity_taken_index: int | None = None
    liquidity_resolved_index: int | None = None
    sweep_episode_id: int | None = None
    bos_broken_index: int | None = None

    @property
    def liquidity_active(self) -> bool:
        return self.liquidity_state == LiquidityState.ACTIVE

    @property
    def structure_unbroken(self) -> bool:
        return self.bos_broken_index is None


@dataclass(frozen=True)
class MarketEvent:
    kind: MarketEventKind
    candle_index: int
    event_time: datetime
    price: float
    level_id: int
    level_price: float
    note: str
    episode_id: int | None = None
    member_level_ids: tuple[int, ...] = ()
    # Phase 1.4.5: for SFP formation events this stores the already-known sweep-candle
    # extreme that invalidates the pattern if a later candle body closes beyond it.
    # The source defines invalidation by a close beyond the SFP minimum/maximum; using
    # the completed sweep candle's extreme is the causal software normalization used here.
    sfp_pattern_extreme_price: float | None = None
    # Optional provenance for SFP/liquidity events and structural descendants.
    # Same-direction recovery is a technical lineage marker, never a source signal.
    liquidity_origin: str | None = None  # STRUCTURAL_SWING | RANGE_BOUNDARY
    range_id: int | None = None
    recovery_transition_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class LiquiditySweepEpisode:
    episode_id: int
    side: str  # "high" | "low"
    sweep_candle_index: int
    sweep_time: datetime
    member_level_ids: tuple[int, ...]
    member_level_prices: tuple[float, ...]
    status: SweepEpisodeStatus = SweepEpisodeStatus.PENDING_NEXT_CANDLE
    resolved_index: int | None = None
    representative_level_id: int | None = None
    representative_level_price: float | None = None
    valid_sfp_level_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class OrderBlockReadiness:
    enabled: bool
    status: str
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class MarketAnalysisReport:
    candle_count: int
    final_trend: TrendState
    levels: tuple[StructuralLevel, ...]
    sweep_episodes: tuple[LiquiditySweepEpisode, ...]
    events: tuple[MarketEvent, ...]
    order_block_readiness: OrderBlockReadiness
    structure_policy: str
    sfp_timeframe_preference: str
    sfp_policy: str
    trend_state_segments: tuple[TrendStateSegment, ...] = ()
    structure_transition_diagnostics: tuple[StructureTransitionDiagnostic, ...] = ()
    sfp_liquidity_scope: str = "STRUCTURAL_SWING_ONLY_RANGE_BOUNDARY_PENDING"
    analysis_mode: StructureAnalysisMode = StructureAnalysisMode.SOURCE_CONSERVATIVE

    def state_candle_counts(self) -> dict[str, int]:
        out = {state.value: 0 for state in TrendState}
        for segment in self.trend_state_segments:
            out[segment.state.value] += segment.candle_count
        return out

    def longest_state_run(self, state: TrendState) -> int:
        return max((segment.candle_count for segment in self.trend_state_segments if segment.state == state), default=0)

    def events_of(self, kind: MarketEventKind) -> tuple[MarketEvent, ...]:
        return tuple(event for event in self.events if event.kind == kind)


class MarketAnalysisError(ValueError):
    pass


def _validate_candles(candles: Sequence[Candle], timeframe_minutes: int | None = None) -> None:
    if timeframe_minutes is not None and (type(timeframe_minutes) is not int or timeframe_minutes<=0):
        raise MarketAnalysisError('timeframe must be positive whole minutes')
    duration = candles[0].close_time-candles[0].open_time if candles else None
    if duration is not None and (duration.total_seconds()%60 or
            (timeframe_minutes is not None and duration.total_seconds()!=timeframe_minutes*60)):
        raise MarketAnalysisError('candle duration must match the declared whole-minute timeframe')
    previous_open: datetime | None = None
    previous_close: datetime | None = None
    for index, candle in enumerate(candles):
        if not candle.is_closed:
            raise MarketAnalysisError(f"unfinished candle at index {index}")
        if previous_open is not None and candle.open_time <= previous_open:
            raise MarketAnalysisError("candles must be strictly chronological")
        if duration is not None and candle.close_time-candle.open_time!=duration:
            raise MarketAnalysisError('candle duration cannot change within one analysis')
        if previous_close is not None and candle.open_time != previous_close:
            raise MarketAnalysisError("candles must be contiguous without gaps or overlaps")
        previous_open = candle.open_time
        previous_close = candle.close_time


def _level_by_id(levels: list[StructuralLevel], level_id: int | None) -> StructuralLevel | None:
    if level_id is None:
        return None
    return next((level for level in levels if level.level_id == level_id), None)


def _bullish_structure_ending_at_high(
    levels: list[StructuralLevel],
    *,
    new_high: StructuralLevel | None,
    min_swing_index: int | None = None,
    min_confirmed_after_index: int | None = None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Return ``(protected_hl, key_hh)`` for an interleaved HL->HH update.

    TECHNICAL_NORMALIZATION: the source defines market structure as a sequence of
    higher highs and higher lows. The machine therefore requires chronological
    alternation ``previous_low < previous_high < candidate_low < new_high`` instead
    of comparing two same-side highs and two same-side lows that may occur in a
    non-interleaved order.
    """
    if new_high is None:
        return None
    if min_swing_index is not None and new_high.swing_index < min_swing_index:
        return None
    if min_confirmed_after_index is not None and new_high.confirmed_index <= min_confirmed_after_index:
        return None

    def allowed(level: StructuralLevel) -> bool:
        if min_swing_index is not None and level.swing_index < min_swing_index:
            return False
        if min_confirmed_after_index is not None and level.confirmed_index <= min_confirmed_after_index:
            return False
        return True

    candidate_lows = [
        level for level in levels
        if level.side == "low" and allowed(level) and level.swing_index < new_high.swing_index
    ]
    if not candidate_lows:
        return None
    candidate_low = max(candidate_lows, key=lambda level: level.swing_index)

    previous_highs = [
        level for level in levels
        if level.side == "high" and allowed(level) and level.swing_index < candidate_low.swing_index
    ]
    if not previous_highs:
        return None
    previous_high = max(previous_highs, key=lambda level: level.swing_index)

    previous_lows = [
        level for level in levels
        if level.side == "low" and allowed(level) and level.swing_index < previous_high.swing_index
    ]
    if not previous_lows:
        return None
    previous_low = max(previous_lows, key=lambda level: level.swing_index)

    if new_high.price > previous_high.price and candidate_low.price > previous_low.price:
        return candidate_low, new_high
    return None


def _bearish_structure_ending_at_low(
    levels: list[StructuralLevel],
    *,
    new_low: StructuralLevel | None,
    min_swing_index: int | None = None,
    min_confirmed_after_index: int | None = None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Return ``(protected_lh, key_ll)`` for an interleaved LH->LL update.

    TECHNICAL_NORMALIZATION mirrors ``_bullish_structure_ending_at_high`` and
    requires ``previous_high < previous_low < candidate_high < new_low``.
    """
    if new_low is None:
        return None
    if min_swing_index is not None and new_low.swing_index < min_swing_index:
        return None
    if min_confirmed_after_index is not None and new_low.confirmed_index <= min_confirmed_after_index:
        return None

    def allowed(level: StructuralLevel) -> bool:
        if min_swing_index is not None and level.swing_index < min_swing_index:
            return False
        if min_confirmed_after_index is not None and level.confirmed_index <= min_confirmed_after_index:
            return False
        return True

    candidate_highs = [
        level for level in levels
        if level.side == "high" and allowed(level) and level.swing_index < new_low.swing_index
    ]
    if not candidate_highs:
        return None
    candidate_high = max(candidate_highs, key=lambda level: level.swing_index)

    previous_lows = [
        level for level in levels
        if level.side == "low" and allowed(level) and level.swing_index < candidate_high.swing_index
    ]
    if not previous_lows:
        return None
    previous_low = max(previous_lows, key=lambda level: level.swing_index)

    previous_highs = [
        level for level in levels
        if level.side == "high" and allowed(level) and level.swing_index < previous_low.swing_index
    ]
    if not previous_highs:
        return None
    previous_high = max(previous_highs, key=lambda level: level.swing_index)

    if new_low.price < previous_low.price and candidate_high.price < previous_high.price:
        return candidate_high, new_low
    return None



def _bullish_live_update(
    levels: list[StructuralLevel],
    *,
    new_high: StructuralLevel | None,
    protected_hl: StructuralLevel | None,
    key_hh: StructuralLevel | None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Update an already-live bullish structure from its key HH/protected HL.

    SOURCE-ALIGNED NORMALIZATION: while bullish structure is live, a new key HH must
    actually exceed the current key HH, and its correction low must be a later swing
    between the old HH and the new HH that remains above the current protected HL.
    Internal/lower swing highs are not allowed to reset the comparison reference.
    """
    if new_high is None or protected_hl is None or key_hh is None:
        return None
    if new_high.swing_index <= key_hh.swing_index or new_high.price <= key_hh.price:
        return None
    lows = [
        level for level in levels
        if level.side == "low"
        and key_hh.swing_index < level.swing_index < new_high.swing_index
        and level.confirmed_index <= new_high.confirmed_index
    ]
    if not lows:
        return None
    candidate_low = max(lows, key=lambda level: level.swing_index)
    if candidate_low.price <= protected_hl.price:
        return None
    return candidate_low, new_high


def _bearish_live_update(
    levels: list[StructuralLevel],
    *,
    new_low: StructuralLevel | None,
    protected_lh: StructuralLevel | None,
    key_ll: StructuralLevel | None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Update an already-live bearish structure from its key LL/protected LH."""
    if new_low is None or protected_lh is None or key_ll is None:
        return None
    if new_low.swing_index <= key_ll.swing_index or new_low.price >= key_ll.price:
        return None
    highs = [
        level for level in levels
        if level.side == "high"
        and key_ll.swing_index < level.swing_index < new_low.swing_index
        and level.confirmed_index <= new_low.confirmed_index
    ]
    if not highs:
        return None
    candidate_high = max(highs, key=lambda level: level.swing_index)
    if candidate_high.price >= protected_lh.price:
        return None
    return candidate_high, new_low

def _post_bos_bullish_structure(
    levels: list[StructuralLevel],
    *,
    bos_index: int,
    new_high: StructuralLevel | None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Find a causally confirmed, interleaved post-BOS HH+HL structure."""
    return _bullish_structure_ending_at_high(
        levels,
        new_high=new_high,
        min_swing_index=bos_index,
        min_confirmed_after_index=bos_index,
    )


def _post_bos_bearish_structure(
    levels: list[StructuralLevel],
    *,
    bos_index: int,
    new_low: StructuralLevel | None,
) -> tuple[StructuralLevel, StructuralLevel] | None:
    """Find a causally confirmed, interleaved post-BOS LL+LH structure."""
    return _bearish_structure_ending_at_low(
        levels,
        new_low=new_low,
        min_swing_index=bos_index,
        min_confirmed_after_index=bos_index,
    )


def _compress_trend_states(candles: Sequence[Candle], states: Sequence[TrendState]) -> tuple[TrendStateSegment, ...]:
    if not states:
        return ()
    if len(candles) != len(states):
        raise MarketAnalysisError("trend state trace length mismatch")
    out: list[TrendStateSegment] = []
    start = 0
    current = states[0]
    for i in range(1, len(states) + 1):
        if i == len(states) or states[i] != current:
            out.append(
                TrendStateSegment(
                    state=current,
                    start_index=start,
                    end_index=i - 1,
                    start_time=candles[start].open_time,
                    end_time=candles[i - 1].close_time,
                    candle_count=i - start,
                )
            )
            if i < len(states):
                start = i
                current = states[i]
    return tuple(out)


def analyze_market(candles: Sequence[Candle], *, timeframe_minutes: int | None = None, analysis_mode: StructureAnalysisMode | str = StructureAnalysisMode.SOURCE_CONSERVATIVE) -> MarketAnalysisReport:
    """Causal Phase-1.4.12 structure/liquidity analyzer.

    SOURCE RULES represented here:
    - Swing High / Swing Low are three-candle structural points.
    - Bullish structure has higher highs and higher lows.
    - Bearish structure has lower lows and lower highs.
    - BOS of an existing bullish structure is a break/close beyond its key Higher Low.
    - BOS of an existing bearish structure is a break/close beyond its key Lower High.
    - CONF is the later update of the key maximum/minimum of the new structure after BOS.
    - structural highs/lows are external liquidity locations.
    - SFP is checked only after the sweep candle and following candle are known.
    - SFP may form on structural highs/lows of any timeframe; the source explicitly says
      H1 and above are the preferred timeframes for searching for SFP.
    - A formed SFP becomes irrelevant if a candle body later closes beyond the pattern
      minimum (bullish/long case) or maximum (bearish/short case).

    TECHNICAL NORMALIZATIONS kept explicit:
    - HH/HL and LL/LH are derived from confirmed three-candle swings.
    - structure points must be chronologically interleaved; non-interleaved same-side
      highs/lows are not paired into a fake HH/HL or LL/LH sequence.
    - once a trend is live, a new key HH/LL must update the current key extreme, and the
      intervening correction must remain beyond the current protected HL/LH. Internal
      swing highs/lows do not silently replace the live key comparison reference.
    - after BOS, pre-BOS swing points are not allowed to form the new structure. The first
      opposite anchor may be the BOS candle/leg extreme itself if its three-candle swing is
      confirmed after the BOS event; otherwise it must be later. A strictly later correction
      swing then forms LL+LH / HH+HL relative to the broken structure's key points. CONF remains
      a separate later update: a body close through the new structure's first post-BOS extreme.
      This prevents the detector from staying indefinitely in BROKEN merely because CONF has not
      yet printed.
    - a liquidity take is strict wick penetration (high > level / low < level); no EQH/EQL
      tolerance is invented in this build.
    - all structural levels first swept by the same candle on the same side are grouped into
      one sweep episode. This avoids duplicate SFP formations without inventing a price-distance
      clustering threshold. Raw per-level sweep events are still preserved.
    - after the following candle resolves the episode, swept levels become CONSUMED.
    - at most one directional SFP formation is emitted per sweep episode. If several swept
      levels satisfy the SFP conditions, the outermost valid level is used as the representative
      (highest for a high-side sweep, lowest for a low-side sweep).

    The exact machine selection of protected points and post-BOS CONF anchors is a
    technical normalization and remains subject to manual chart conformance review.
    """
    analysis_mode = StructureAnalysisMode(analysis_mode)
    _validate_candles(candles, timeframe_minutes)
    # Causal ancestry, not a claim that every descendant disappears in ablation.
    # Never clear ancestry merely because a later transition is source-expected.
    recovery_transition_ids: tuple[int, ...] = ()

    levels: list[StructuralLevel] = []
    # Keep the full append-only list for report ordering, while indexing levels by
    # ID for the state-machine lookups below.  ``active_levels`` contains only
    # liquidity levels that can still be swept.  It is an insertion-ordered dict,
    # so iterating it preserves the exact event/member ordering of the full list.
    levels_by_id: dict[int, StructuralLevel] = {}
    def get_level(level_id: int | None) -> StructuralLevel | None:
        return levels_by_id.get(level_id) if level_id is not None else None

    level_indices: dict[int, int] = {}
    active_levels: dict[int, StructuralLevel] = {}

    def _store_level(level: StructuralLevel, *, sync_active: bool = True) -> None:
        """Store one level in all indexes without rebuilding ``levels``.

        ``sync_active=False`` is used while iterating ``active_levels``: assigning
        an existing dict value is safe, but changing its size during iteration is
        not.  The swept IDs are removed immediately after that scan.
        """
        index = level_indices.get(level.level_id)
        if index is None:
            level_indices[level.level_id] = len(levels)
            levels.append(level)
        else:
            levels[index] = level
        levels_by_id[level.level_id] = level
        if not sync_active:
            return
        if level.liquidity_active:
            active_levels[level.level_id] = level
        else:
            active_levels.pop(level.level_id, None)
    events: list[MarketEvent] = []
    next_level_id = 1
    trend = TrendState.UNKNOWN
    protected_level_id: int | None = None

    # Current key HH/LL for the live structure. This is separate from the protected HL/LH.
    # It gives the post-BOS transition a stable source-aligned reference instead of using an
    # arbitrary latest swing that may be only local noise.
    trend_extreme_level_id: int | None = None

    # Post-BOS structure-formation state. The first new anchor may be the BOS candle/leg
    # extreme itself, provided that swing is confirmed only after BOS; later correction points
    # must be strictly later than that anchor. The old protected price and old key extreme are
    # frozen at BOS so the first opposite
    # LL+LH / HH+HL can be evaluated causally against the structure that was actually broken.
    expected_new_trend: TrendState | None = None
    last_bos_index: int | None = None
    transition_anchor_level_id: int | None = None
    transition_correction_level_id: int | None = None
    broken_structure_protected_price: float | None = None
    broken_structure_extreme_price: float | None = None

    # CONF is deliberately separate from structure existence. Once the opposite structure is
    # formed, it becomes the live trend and can itself later break even if CONF never arrives.
    # CONF remains the source concept of a later update of the new structure's key extreme.
    pending_conf_trend: TrendState | None = None
    pending_conf_anchor_level_id: int | None = None
    pending_conf_correction_level_id: int | None = None

    # Phase 1.4.12: every BOS transition is audit-visible. BROKEN is a technical
    # transition state, not a source market regime, so diagnostics record why it
    # resolved (or why it remained unresolved at end-of-data).
    transition_diagnostics: list[StructureTransitionDiagnostic] = []
    next_transition_id = 1
    active_transition: _ActiveTransition | None = None

    def _start_transition(
        *,
        bos_kind: MarketEventKind,
        bos_index: int,
        bos_time: datetime,
        from_trend: TrendState,
        expected_trend: TrendState,
        protected_price: float,
        extreme_price: float | None,
    ) -> None:
        nonlocal active_transition, next_transition_id
        active_transition = {
            "transition_id": next_transition_id,
            "bos_kind": bos_kind.value,
            "bos_index": bos_index,
            "bos_time": bos_time,
            "from_trend": from_trend,
            "expected_trend": expected_trend,
            "broken_protected_price": protected_price,
            "broken_extreme_price": extreme_price,
            "post_bos_high_level_ids": [],
            "post_bos_low_level_ids": [],
            "selected_anchor_level_id": None,
            "selected_correction_level_id": None,
            "rejection_reasons": [],
        }
        next_transition_id += 1

    def _transition_reject(reason: str) -> None:
        if active_transition is None:
            return
        reasons = active_transition["rejection_reasons"]
        assert isinstance(reasons, list)
        if reason not in reasons:
            reasons.append(reason)

    def _transition_add_level(level: StructuralLevel | None) -> None:
        if active_transition is None or level is None:
            return
        bos_index = int(active_transition["bos_index"])
        # Audit fields named post_bos_* must contain only causally post-BOS swing centers.
        # A level confirmed on the BOS close but centered before BOS may be useful as a
        # rejection diagnostic, but it is not a post-BOS structural point.
        if level.swing_index < bos_index or level.confirmed_index <= bos_index:
            return
        values = (active_transition["post_bos_high_level_ids"] if level.side == "high"
                  else active_transition["post_bos_low_level_ids"])
        assert isinstance(values, list)
        if level.level_id not in values:
            values.append(level.level_id)

    def _finish_transition(
        *,
        resolved_index: int | None,
        resolved_time: datetime | None,
        resolved_trend: TrendState | None,
        resolution_mode: str,
        selected_anchor_level_id: int | None = None,
        selected_correction_level_id: int | None = None,
    ) -> None:
        nonlocal active_transition, recovery_transition_ids
        if active_transition is None:
            return
        if resolution_mode == "SAME_DIRECTION_POST_BOS_RECOVERY":
            recovery_transition_ids += (int(active_transition["transition_id"]),)
        bos_index = int(active_transition["bos_index"])
        if resolved_index is None:
            broken_candles = max(0, len(candles) - bos_index)
        else:
            # The BOS candle itself is traced as BROKEN; the resolution candle is traced
            # in the resolved live state, so the BROKEN run is the index difference.
            broken_candles = max(0, resolved_index - bos_index)
        highs = tuple(int(x) for x in active_transition["post_bos_high_level_ids"])
        lows = tuple(int(x) for x in active_transition["post_bos_low_level_ids"])
        reasons = tuple(str(x) for x in active_transition["rejection_reasons"])
        transition_diagnostics.append(
            StructureTransitionDiagnostic(
                transition_id=int(active_transition["transition_id"]),
                bos_kind=str(active_transition["bos_kind"]),
                bos_index=bos_index,
                bos_time=active_transition["bos_time"],
                from_trend=active_transition["from_trend"],
                expected_trend=active_transition["expected_trend"],
                broken_protected_price=float(active_transition["broken_protected_price"]),
                broken_extreme_price=(
                    float(active_transition["broken_extreme_price"])
                    if active_transition["broken_extreme_price"] is not None
                    else None
                ),
                resolved_index=resolved_index,
                resolved_time=resolved_time,
                resolved_trend=resolved_trend,
                resolution_mode=resolution_mode,
                broken_candles=broken_candles,
                post_bos_high_level_ids=highs,
                post_bos_low_level_ids=lows,
                selected_anchor_level_id=(
                    selected_anchor_level_id
                    if selected_anchor_level_id is not None
                    else active_transition["selected_anchor_level_id"]
                ),
                selected_correction_level_id=(
                    selected_correction_level_id
                    if selected_correction_level_id is not None
                    else active_transition["selected_correction_level_id"]
                ),
                rejection_reasons=reasons,
            )
        )
        active_transition = None

    trend_trace: list[TrendState] = []

    sweep_episodes: list[LiquiditySweepEpisode] = []
    episode_indices: dict[int, int] = {}
    next_episode_id = 1
    # Sweep episodes are resolved on the candle immediately following the sweep candle.
    pending_episode_ids: dict[int, list[int]] = {}
    # Active SFP formations remain relevant until a later candle body closes beyond the
    # completed sweep-candle extreme. The invalidation rule is source-derived; the
    # sweep-candle extreme as the machine representation of the SFP min/max is an
    # explicit causal normalization.
    active_sfps: dict[int, MarketEvent] = {}

    for i, candle in enumerate(candles):
        first_event_this_candle = len(events)
        # SFP/liquidity events are evaluated before any structure transition that
        # this same candle may resolve. Capture ancestry at candle open so a
        # recovery completed later on this candle is never attributed backwards.
        recovery_ids_at_candle_start = recovery_transition_ids
        # 1) Resolve each same-candle/same-side sweep episode only when the next candle is available.
        for episode_id in pending_episode_ids.pop(i, []):
            ep_index = episode_indices[episode_id]
            episode = sweep_episodes[ep_index]
            sweep_candle = candles[episode.sweep_candle_index]
            if episode.status == SweepEpisodeStatus.AMBIGUOUS_DUAL_SIDE_SWEEP:
                # A candle that first sweeps both high-side and low-side external structural
                # liquidity is not resolved into two opposite SFP formations automatically.
                # The source materials do not define this dual-sided edge case, so Phase 1.4.5
                # preserves the raw sweeps but conservatively blocks directional SFP formation.
                resolved_member_ids = set(episode.member_level_ids)
                for level_id in resolved_member_ids:
                    level = levels_by_id[level_id]
                    _store_level(replace(level, liquidity_state=LiquidityState.CONSUMED, liquidity_resolved_index=i))
                sweep_episodes[ep_index] = replace(episode, resolved_index=i)
                continue

            valid_levels: list[StructuralLevel] = []
            for level_id in episode.member_level_ids:
                level = levels_by_id[level_id]
                result = detect_sfp(sweep_candle, candle, level.price, episode.side)
                if result.valid:
                    valid_levels.append(level)

            # Once the next candle is known, the swept liquidity is no longer active regardless
            # of whether the SFP pattern completed. This is a lifecycle normalization, not a
            # new trading rule.
            resolved_member_ids = set(episode.member_level_ids)
            for level_id in resolved_member_ids:
                level = levels_by_id[level_id]
                _store_level(replace(level, liquidity_state=LiquidityState.CONSUMED, liquidity_resolved_index=i))

            if valid_levels:
                representative = (
                    max(valid_levels, key=lambda level: level.price)
                    if episode.side == "high"
                    else min(valid_levels, key=lambda level: level.price)
                )
                kind = (
                    MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED
                    if episode.side == "high"
                    else MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED
                )
                valid_ids = tuple(level.level_id for level in valid_levels)
                sweep_episodes[ep_index] = replace(
                    episode,
                    status=SweepEpisodeStatus.SFP_FORMED,
                    resolved_index=i,
                    representative_level_id=representative.level_id,
                    representative_level_price=representative.price,
                    valid_sfp_level_ids=valid_ids,
                )
                sfp_event = MarketEvent(
                    kind=kind,
                    candle_index=i,
                    event_time=candle.open_time,
                    price=candle.open,
                    level_id=representative.level_id,
                    level_price=representative.price,
                    episode_id=episode.episode_id,
                    member_level_ids=episode.member_level_ids,
                    sfp_pattern_extreme_price=(
                        candles[episode.sweep_candle_index].high
                        if episode.side == "high"
                        else candles[episode.sweep_candle_index].low
                    ),
                    liquidity_origin="STRUCTURAL_SWING",
                    recovery_transition_ids=recovery_ids_at_candle_start,
                    note=(
                        "SFP formation confirmed for one sweep episode; duplicate structural levels "
                        "swept by the same candle/side are not emitted as separate SFP formations. "
                        "LTF BOS remains a later confirmation layer before any entry candidate."
                    ),
                )
                events.append(sfp_event)
                active_sfps[episode.episode_id] = sfp_event
            else:
                sweep_episodes[ep_index] = replace(
                    episode,
                    status=SweepEpisodeStatus.CONSUMED_NO_SFP,
                    resolved_index=i,
                )

        # 1b) Source-defined SFP invalidation: once a pattern is formed, a later body
        # close below its minimum (long/bullish case) or above its maximum
        # (short/bearish case) makes the pattern no longer relevant. We represent the
        # pattern min/max by the already-completed sweep candle's low/high so this check
        # does not depend on future intrabar data.
        invalidated_episode_ids: list[int] = []
        for episode_id, sfp_event in active_sfps.items():
            pattern_extreme = sfp_event.sfp_pattern_extreme_price
            if pattern_extreme is None or candle.close_time <= sfp_event.event_time:
                continue
            if (
                sfp_event.kind == MarketEventKind.BULLISH_SFP_FORMATION_CONFIRMED
                and candle.close < pattern_extreme
            ):
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BULLISH_SFP_INVALIDATED_CLOSE,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=candle.close,
                        level_id=sfp_event.level_id,
                        level_price=pattern_extreme,
                        episode_id=episode_id,
                        member_level_ids=sfp_event.member_level_ids,
                        sfp_pattern_extreme_price=pattern_extreme,
                        liquidity_origin=sfp_event.liquidity_origin,
                        range_id=sfp_event.range_id,
                        recovery_transition_ids=sfp_event.recovery_transition_ids,
                        note=(
                            "Bullish SFP became irrelevant because a candle body closed below "
                            "the SFP pattern minimum/extreme."
                        ),
                    )
                )
                invalidated_episode_ids.append(episode_id)
            elif (
                sfp_event.kind == MarketEventKind.BEARISH_SFP_FORMATION_CONFIRMED
                and candle.close > pattern_extreme
            ):
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BEARISH_SFP_INVALIDATED_CLOSE,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=candle.close,
                        level_id=sfp_event.level_id,
                        level_price=pattern_extreme,
                        episode_id=episode_id,
                        member_level_ids=sfp_event.member_level_ids,
                        sfp_pattern_extreme_price=pattern_extreme,
                        liquidity_origin=sfp_event.liquidity_origin,
                        range_id=sfp_event.range_id,
                        recovery_transition_ids=sfp_event.recovery_transition_ids,
                        note=(
                            "Bearish SFP became irrelevant because a candle body closed above "
                            "the SFP pattern maximum/extreme."
                        ),
                    )
                )
                invalidated_episode_ids.append(episode_id)
        for episode_id in invalidated_episode_ids:
            active_sfps.pop(episode_id, None)

        # 2) Apply current wick only to liquidity levels already known before this candle.
        # Preserve raw per-level sweep events, but group same-candle/same-side sweeps into one
        # episode for later SFP resolution. No price-distance threshold is invented.
        swept_by_side: dict[str, list[StructuralLevel]] = {"high": [], "low": []}
        swept_level_ids: list[int] = []
        # ``active_levels`` is insertion ordered, matching the old ``levels`` scan
        # for all still-active entries while avoiding all historical, consumed levels.
        for level_id, level in active_levels.items():
            updated = level
            if level.side == "high" and candle.high > level.price:
                updated = replace(
                    level,
                    liquidity_state=LiquidityState.SWEPT,
                    liquidity_taken_index=i,
                )
                swept_by_side["high"].append(updated)
                swept_level_ids.append(level_id)
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.HIGH_LIQUIDITY_TAKEN,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=candle.high,
                        level_id=level.level_id,
                        level_price=level.price,
                        note="Strict wick penetration above a confirmed structural high.",
                    )
                )
            elif level.side == "low" and candle.low < level.price:
                updated = replace(
                    level,
                    liquidity_state=LiquidityState.SWEPT,
                    liquidity_taken_index=i,
                )
                swept_by_side["low"].append(updated)
                swept_level_ids.append(level_id)
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.LOW_LIQUIDITY_TAKEN,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=candle.low,
                        level_id=level.level_id,
                        level_price=level.price,
                        note="Strict wick penetration below a confirmed structural low.",
                    )
                )
            if updated is not level:
                _store_level(updated, sync_active=False)
                # Assigning an existing key preserves dict iteration order.  Removal
                # is deferred until after the scan to avoid changing its size here.
                active_levels[level_id] = updated
        for level_id in swept_level_ids:
            active_levels.pop(level_id, None)

        dual_side_sweep = bool(swept_by_side["high"] and swept_by_side["low"])
        for side in ("high", "low"):
            swept_levels = swept_by_side[side]
            if not swept_levels:
                continue
            episode_id = next_episode_id
            next_episode_id += 1
            member_ids = tuple(level.level_id for level in swept_levels)
            member_prices = tuple(level.price for level in swept_levels)
            representative = (
                max(swept_levels, key=lambda level: level.price)
                if side == "high"
                else min(swept_levels, key=lambda level: level.price)
            )
            for level in swept_levels:
                _store_level(replace(level, sweep_episode_id=episode_id))
            episode = LiquiditySweepEpisode(
                episode_id=episode_id,
                side=side,
                sweep_candle_index=i,
                sweep_time=candle.close_time,
                member_level_ids=member_ids,
                member_level_prices=member_prices,
                status=(
                    SweepEpisodeStatus.AMBIGUOUS_DUAL_SIDE_SWEEP
                    if dual_side_sweep
                    else SweepEpisodeStatus.PENDING_NEXT_CANDLE
                ),
            )
            sweep_episodes.append(episode)
            episode_indices[episode_id] = len(sweep_episodes) - 1
            pending_episode_ids.setdefault(i + 1, []).append(episode_id)
            events.append(
                MarketEvent(
                    kind=(
                        MarketEventKind.HIGH_LIQUIDITY_SWEEP_EPISODE
                        if side == "high"
                        else MarketEventKind.LOW_LIQUIDITY_SWEEP_EPISODE
                    ),
                    candle_index=i,
                    event_time=candle.close_time,
                    price=candle.high if side == "high" else candle.low,
                    level_id=representative.level_id,
                    level_price=representative.price,
                    episode_id=episode_id,
                    member_level_ids=member_ids,
                    note=(
                        (
                            "Dual-sided sweep: this candle first took structural liquidity on both sides. "
                            "Raw per-level takes are preserved, but automatic directional SFP formation is "
                            "blocked as an unresolved technical edge case."
                        )
                        if dual_side_sweep
                        else (
                            f"One {side}-side sweep episode grouped {len(member_ids)} structural liquidity "
                            "level(s) first taken by the same candle; raw per-level takes are preserved."
                        )
                    ),
                )
            )

        # 3) BOS can only break the protected level of an already-established trend.
        # Phase 1.4.8 freezes the broken structure's actual key HH/LL and protected HL/LH.
        # This avoids using an arbitrary latest swing as the post-BOS comparison reference.
        if protected_level_id is not None and trend in {TrendState.BULLISH, TrendState.BEARISH}:
            protected = get_level(protected_level_id)
            if protected is not None:
                extreme = get_level(trend_extreme_level_id)
                if trend == TrendState.BULLISH and candle.close < protected.price:
                    _store_level(replace(protected, bos_broken_index=i))
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=protected.level_id,
                            level_price=protected.price,
                            note="Bullish structure invalidated by a body close below its protected Higher Low.",
                        )
                    )
                    broken_structure_protected_price = protected.price
                    broken_structure_extreme_price = extreme.price if extreme is not None else None
                    _start_transition(
                        bos_kind=MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS,
                        bos_index=i,
                        bos_time=candle.close_time,
                        from_trend=TrendState.BULLISH,
                        expected_trend=TrendState.BEARISH,
                        protected_price=protected.price,
                        extreme_price=broken_structure_extreme_price,
                    )
                    trend = TrendState.BROKEN
                    protected_level_id = None
                    trend_extreme_level_id = None
                    expected_new_trend = TrendState.BEARISH
                    last_bos_index = i
                    transition_anchor_level_id = None
                    transition_correction_level_id = None
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None
                elif trend == TrendState.BEARISH and candle.close > protected.price:
                    _store_level(replace(protected, bos_broken_index=i))
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=protected.level_id,
                            level_price=protected.price,
                            note="Bearish structure invalidated by a body close above its protected Lower High.",
                        )
                    )
                    broken_structure_protected_price = protected.price
                    broken_structure_extreme_price = extreme.price if extreme is not None else None
                    _start_transition(
                        bos_kind=MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
                        bos_index=i,
                        bos_time=candle.close_time,
                        from_trend=TrendState.BEARISH,
                        expected_trend=TrendState.BULLISH,
                        protected_price=protected.price,
                        extreme_price=broken_structure_extreme_price,
                    )
                    trend = TrendState.BROKEN
                    protected_level_id = None
                    trend_extreme_level_id = None
                    expected_new_trend = TrendState.BULLISH
                    last_bos_index = i
                    transition_anchor_level_id = None
                    transition_correction_level_id = None
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None

        # 4) CONF is a later update of a new structure, not the prerequisite for the
        # new structure to exist. It is checked before confirming a new swing on this
        # candle so the close cannot use a swing that is only confirmed by the same close.
        if pending_conf_trend is not None:
            anchor = get_level(pending_conf_anchor_level_id)
            correction = get_level(pending_conf_correction_level_id)
            if anchor is not None and correction is not None and i > correction.confirmed_index:
                if pending_conf_trend == TrendState.BEARISH and candle.close < anchor.price:
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BEARISH_CONF_CONFIRMED,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=correction.level_id,
                            level_price=correction.price,
                            note=(
                                "Post-BOS bearish CONF: the already-formed LL+LH bearish structure "
                                "updated its first post-BOS key low; the LH remains the protected level."
                            ),
                        )
                    )
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None
                elif pending_conf_trend == TrendState.BULLISH and candle.close > anchor.price:
                    events.append(
                        MarketEvent(
                            kind=MarketEventKind.BULLISH_CONF_CONFIRMED,
                            candle_index=i,
                            event_time=candle.close_time,
                            price=candle.close,
                            level_id=correction.level_id,
                            level_price=correction.price,
                            note=(
                                "Post-BOS bullish CONF: the already-formed HH+HL bullish structure "
                                "updated its first post-BOS key high; the HL remains the protected level."
                            ),
                        )
                    )
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None

        # 5) Confirm new swings after the right-hand candle closes, then update structure.
        new_high: StructuralLevel | None = None
        new_low: StructuralLevel | None = None
        if i >= 2:
            left, center, right = candles[i - 2], candles[i - 1], candles[i]
            if is_swing_high(left, center, right):
                new_high = StructuralLevel(
                    level_id=next_level_id,
                    side="high",
                    price=center.high,
                    swing_index=i - 1,
                    confirmed_index=i,
                    swing_time=center.open_time,
                    confirmed_time=right.close_time,
                )
                _store_level(new_high)
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.SWING_HIGH_CONFIRMED,
                        candle_index=i,
                        event_time=right.close_time,
                        price=center.high,
                        level_id=next_level_id,
                        level_price=center.high,
                        note="Three-candle Swing High confirmed after the right candle closed.",
                    )
                )
                next_level_id += 1

            if is_swing_low(left, center, right):
                new_low = StructuralLevel(
                    level_id=next_level_id,
                    side="low",
                    price=center.low,
                    swing_index=i - 1,
                    confirmed_index=i,
                    swing_time=center.open_time,
                    confirmed_time=right.close_time,
                )
                _store_level(new_low)
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.SWING_LOW_CONFIRMED,
                        candle_index=i,
                        event_time=right.close_time,
                        price=center.low,
                        level_id=next_level_id,
                        level_price=center.low,
                        note="Three-candle Swing Low confirmed after the right candle closed.",
                    )
                )
                next_level_id += 1

        # A center candle can technically satisfy both three-candle swing tests (outside bar).
        # The source does not define how to assign HH/HL/LH/LL from that ambiguous dual swing,
        # so the analyzer records both liquidity levels but does not change trend on that confirmation.
        dual_swing = new_high is not None and new_low is not None

        # 6) Resolve the post-BOS transition causally.
        # SOURCE: after bullish BOS, bearish structure should form LL + LH; after bearish
        # BOS, bullish structure should form HL + HH. Phase 1.4.12 keeps that source-expected
        # opposite structure as the priority fast path.
        #
        # TECHNICAL_NORMALIZATION: BROKEN is only a software transition state, not a source
        # market regime. If the expected fast path never completes but strictly post-BOS
        # confirmed swings later form an unambiguous HH+HL or LL+LH sequence, the live market
        # structure is allowed to re-establish from those post-BOS points. This can represent
        # either the expected reversal or a same-direction recovery after a failed transition.
        # No timeout is invented and no pre-BOS swing is reused.
        transition_resolved_this_candle = False
        if trend == TrendState.BROKEN and active_transition is not None:
            _transition_add_level(new_high)
            _transition_add_level(new_low)
            if dual_swing:
                _transition_reject("DUAL_SWING_CONFIRMATION_SKIPPED")

        if (
            trend == TrendState.BROKEN
            and expected_new_trend is not None
            and last_bos_index is not None
            and not dual_swing
        ):
            if expected_new_trend == TrendState.BEARISH:
                if new_low is not None:
                    if new_low.swing_index < last_bos_index or new_low.confirmed_index <= last_bos_index:
                        _transition_reject("BEARISH_ANCHOR_NOT_CAUSALLY_POST_BOS")
                    elif broken_structure_protected_price is None:
                        _transition_reject("BROKEN_PROTECTED_PRICE_MISSING")
                    elif new_low.price >= broken_structure_protected_price:
                        _transition_reject("BEARISH_ANCHOR_NOT_LL_VS_BROKEN_HL")
                    elif transition_correction_level_id is None:
                        current_anchor = get_level(transition_anchor_level_id)
                        if current_anchor is None or new_low.price < current_anchor.price:
                            transition_anchor_level_id = new_low.level_id
                            if active_transition is not None:
                                active_transition["selected_anchor_level_id"] = new_low.level_id

                anchor = get_level(transition_anchor_level_id)
                if new_high is not None and anchor is not None:
                    if new_high.swing_index <= anchor.swing_index:
                        _transition_reject("BEARISH_CORRECTION_NOT_AFTER_LL_ANCHOR")
                    elif broken_structure_extreme_price is None:
                        _transition_reject("BROKEN_EXTREME_PRICE_MISSING")
                    elif new_high.price >= broken_structure_extreme_price:
                        _transition_reject("BEARISH_CORRECTION_NOT_LH_VS_BROKEN_HH")
                    else:
                        transition_correction_level_id = new_high.level_id
                        if active_transition is not None:
                            active_transition["selected_correction_level_id"] = new_high.level_id
                        trend = TrendState.BEARISH
                        protected_level_id = new_high.level_id
                        trend_extreme_level_id = anchor.level_id
                        events.append(
                            MarketEvent(
                                kind=MarketEventKind.BEARISH_STRUCTURE_CONFIRMED,
                                candle_index=i,
                                event_time=candle.close_time,
                                price=anchor.price,
                                level_id=new_high.level_id,
                                level_price=new_high.price,
                                note=(
                                    "Post-BOS bearish structure formed: a causally confirmed BOS-leg-or-later LL below the broken bullish HL "
                                    "was followed by a LH below the broken bullish key HH. The LH becomes protected; "
                                    "CONF remains a later update and is not required for structure existence."
                                ),
                            )
                        )
                        pending_conf_trend = TrendState.BEARISH
                        pending_conf_anchor_level_id = anchor.level_id
                        pending_conf_correction_level_id = new_high.level_id
                        _finish_transition(
                            resolved_index=i,
                            resolved_time=candle.close_time,
                            resolved_trend=TrendState.BEARISH,
                            resolution_mode="EXPECTED_OPPOSITE_FAST_PATH",
                            selected_anchor_level_id=anchor.level_id,
                            selected_correction_level_id=new_high.level_id,
                        )
                        expected_new_trend = None
                        transition_anchor_level_id = None
                        transition_correction_level_id = None
                        broken_structure_protected_price = None
                        broken_structure_extreme_price = None
                        transition_resolved_this_candle = True

            elif expected_new_trend == TrendState.BULLISH:
                if new_high is not None:
                    if new_high.swing_index < last_bos_index or new_high.confirmed_index <= last_bos_index:
                        _transition_reject("BULLISH_ANCHOR_NOT_CAUSALLY_POST_BOS")
                    elif broken_structure_protected_price is None:
                        _transition_reject("BROKEN_PROTECTED_PRICE_MISSING")
                    elif new_high.price <= broken_structure_protected_price:
                        _transition_reject("BULLISH_ANCHOR_NOT_HH_VS_BROKEN_LH")
                    elif transition_correction_level_id is None:
                        current_anchor = get_level(transition_anchor_level_id)
                        if current_anchor is None or new_high.price > current_anchor.price:
                            transition_anchor_level_id = new_high.level_id
                            if active_transition is not None:
                                active_transition["selected_anchor_level_id"] = new_high.level_id

                anchor = get_level(transition_anchor_level_id)
                if new_low is not None and anchor is not None:
                    if new_low.swing_index <= anchor.swing_index:
                        _transition_reject("BULLISH_CORRECTION_NOT_AFTER_HH_ANCHOR")
                    elif broken_structure_extreme_price is None:
                        _transition_reject("BROKEN_EXTREME_PRICE_MISSING")
                    elif new_low.price <= broken_structure_extreme_price:
                        _transition_reject("BULLISH_CORRECTION_NOT_HL_VS_BROKEN_LL")
                    else:
                        transition_correction_level_id = new_low.level_id
                        if active_transition is not None:
                            active_transition["selected_correction_level_id"] = new_low.level_id
                        trend = TrendState.BULLISH
                        protected_level_id = new_low.level_id
                        trend_extreme_level_id = anchor.level_id
                        events.append(
                            MarketEvent(
                                kind=MarketEventKind.BULLISH_STRUCTURE_CONFIRMED,
                                candle_index=i,
                                event_time=candle.close_time,
                                price=anchor.price,
                                level_id=new_low.level_id,
                                level_price=new_low.price,
                                note=(
                                    "Post-BOS bullish structure formed: a causally confirmed BOS-leg-or-later HH above the broken bearish LH "
                                    "was followed by a HL above the broken bearish key LL. The HL becomes protected; "
                                    "CONF remains a later update and is not required for structure existence."
                                ),
                            )
                        )
                        pending_conf_trend = TrendState.BULLISH
                        pending_conf_anchor_level_id = anchor.level_id
                        pending_conf_correction_level_id = new_low.level_id
                        _finish_transition(
                            resolved_index=i,
                            resolved_time=candle.close_time,
                            resolved_trend=TrendState.BULLISH,
                            resolution_mode="EXPECTED_OPPOSITE_FAST_PATH",
                            selected_anchor_level_id=anchor.level_id,
                            selected_correction_level_id=new_low.level_id,
                        )
                        expected_new_trend = None
                        transition_anchor_level_id = None
                        transition_correction_level_id = None
                        broken_structure_protected_price = None
                        broken_structure_extreme_price = None
                        transition_resolved_this_candle = True

        # 6b) Generic post-BOS structure fallback. This is deliberately evaluated only if
        # the source-expected fast path did not resolve on this candle. It uses two
        # post-BOS same-side swings plus the post-BOS correction sequence, so an old
        # pre-BOS trend cannot be resurrected by stale points.
        if (
            trend == TrendState.BROKEN
            and last_bos_index is not None
            and not dual_swing
            and not transition_resolved_this_candle
        ):
            bullish_local = _post_bos_bullish_structure(
                levels, bos_index=last_bos_index, new_high=new_high
            )
            bearish_local = _post_bos_bearish_structure(
                levels, bos_index=last_bos_index, new_low=new_low
            )

            if analysis_mode == StructureAnalysisMode.SOURCE_CONSERVATIVE:
                if bullish_local is not None and expected_new_trend != TrendState.BULLISH:
                    _transition_reject("SAME_DIRECTION_RECOVERY_DISABLED_BY_SOURCE_CONSERVATIVE")
                    bullish_local = None
                if bearish_local is not None and expected_new_trend != TrendState.BEARISH:
                    _transition_reject("SAME_DIRECTION_RECOVERY_DISABLED_BY_SOURCE_CONSERVATIVE")
                    bearish_local = None

            if bullish_local is not None and bearish_local is not None:
                # This should be unreachable without a dual swing, but keep the ambiguity
                # explicit instead of selecting a direction silently.
                _transition_reject("AMBIGUOUS_POST_BOS_BULLISH_AND_BEARISH_STRUCTURE")
            elif bullish_local is not None:
                protected_hl, key_hh = bullish_local
                expected_before_resolution = expected_new_trend
                trend = TrendState.BULLISH
                protected_level_id = protected_hl.level_id
                trend_extreme_level_id = key_hh.level_id
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BULLISH_STRUCTURE_CONFIRMED,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=key_hh.price,
                        level_id=protected_hl.level_id,
                        level_price=protected_hl.price,
                        note=(
                            "Post-BOS local bullish HH+HL structure established using only causally confirmed post-BOS swings. "
                            "This fallback prevents an indefinite software BROKEN state when the source-expected opposite transition "
                            "does not complete; same-direction recovery is TECHNICAL_NORMALIZATION."
                        ),
                    )
                )
                mode = (
                    "EXPECTED_OPPOSITE_LOCAL_STRUCTURE"
                    if expected_before_resolution == TrendState.BULLISH
                    else "SAME_DIRECTION_POST_BOS_RECOVERY"
                )
                _finish_transition(
                    resolved_index=i,
                    resolved_time=candle.close_time,
                    resolved_trend=TrendState.BULLISH,
                    resolution_mode=mode,
                    selected_anchor_level_id=key_hh.level_id,
                    selected_correction_level_id=protected_hl.level_id,
                )
                expected_new_trend = None
                transition_anchor_level_id = None
                transition_correction_level_id = None
                broken_structure_protected_price = None
                broken_structure_extreme_price = None
                if mode == "EXPECTED_OPPOSITE_LOCAL_STRUCTURE":
                    pending_conf_trend = TrendState.BULLISH
                    pending_conf_anchor_level_id = key_hh.level_id
                    pending_conf_correction_level_id = protected_hl.level_id
                else:
                    # Same-direction recovery is a technical lifecycle normalization rather
                    # than the source-expected reversal, so do not silently relabel its next
                    # update as source CONF.
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None
                transition_resolved_this_candle = True
            elif bearish_local is not None:
                protected_lh, key_ll = bearish_local
                expected_before_resolution = expected_new_trend
                trend = TrendState.BEARISH
                protected_level_id = protected_lh.level_id
                trend_extreme_level_id = key_ll.level_id
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BEARISH_STRUCTURE_CONFIRMED,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=key_ll.price,
                        level_id=protected_lh.level_id,
                        level_price=protected_lh.price,
                        note=(
                            "Post-BOS local bearish LL+LH structure established using only causally confirmed post-BOS swings. "
                            "This fallback prevents an indefinite software BROKEN state when the source-expected opposite transition "
                            "does not complete; same-direction recovery is TECHNICAL_NORMALIZATION."
                        ),
                    )
                )
                mode = (
                    "EXPECTED_OPPOSITE_LOCAL_STRUCTURE"
                    if expected_before_resolution == TrendState.BEARISH
                    else "SAME_DIRECTION_POST_BOS_RECOVERY"
                )
                _finish_transition(
                    resolved_index=i,
                    resolved_time=candle.close_time,
                    resolved_trend=TrendState.BEARISH,
                    resolution_mode=mode,
                    selected_anchor_level_id=key_ll.level_id,
                    selected_correction_level_id=protected_lh.level_id,
                )
                expected_new_trend = None
                transition_anchor_level_id = None
                transition_correction_level_id = None
                broken_structure_protected_price = None
                broken_structure_extreme_price = None
                if mode == "EXPECTED_OPPOSITE_LOCAL_STRUCTURE":
                    pending_conf_trend = TrendState.BEARISH
                    pending_conf_anchor_level_id = key_ll.level_id
                    pending_conf_correction_level_id = protected_lh.level_id
                else:
                    pending_conf_trend = None
                    pending_conf_anchor_level_id = None
                    pending_conf_correction_level_id = None
                transition_resolved_this_candle = True

        # 7) Before any BOS, or while an existing trend is intact, HH/HL or LL/LH can
        # establish/update that same-direction structure. A BROKEN state is reserved only
        # for the causal interval between BOS and formation of the opposite LL+LH / HH+HL.
        if new_high is not None and not dual_swing and not transition_resolved_this_candle:
            bullish_structure = None
            if trend == TrendState.UNKNOWN:
                bullish_structure = _bullish_structure_ending_at_high(levels, new_high=new_high)
            elif trend == TrendState.BULLISH:
                bullish_structure = _bullish_live_update(
                    levels,
                    new_high=new_high,
                    protected_hl=get_level(protected_level_id),
                    key_hh=get_level(trend_extreme_level_id),
                )
            if bullish_structure is not None:
                candidate_low, key_high = bullish_structure
                trend = TrendState.BULLISH
                protected_level_id = candidate_low.level_id
                trend_extreme_level_id = key_high.level_id
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BULLISH_STRUCTURE_CONFIRMED,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=key_high.price,
                        level_id=candidate_low.level_id,
                        level_price=candidate_low.price,
                        note=(
                            "Interleaved bullish structure update confirmed; the new key HH exceeds the live key HH "
                            "and the intervening protected HL remains above the live protected HL."
                        ),
                    )
                )

        if new_low is not None and not dual_swing and not transition_resolved_this_candle:
            bearish_structure = None
            if trend == TrendState.UNKNOWN:
                bearish_structure = _bearish_structure_ending_at_low(levels, new_low=new_low)
            elif trend == TrendState.BEARISH:
                bearish_structure = _bearish_live_update(
                    levels,
                    new_low=new_low,
                    protected_lh=get_level(protected_level_id),
                    key_ll=get_level(trend_extreme_level_id),
                )
            if bearish_structure is not None:
                candidate_high, key_low = bearish_structure
                trend = TrendState.BEARISH
                protected_level_id = candidate_high.level_id
                trend_extreme_level_id = key_low.level_id
                events.append(
                    MarketEvent(
                        kind=MarketEventKind.BEARISH_STRUCTURE_CONFIRMED,
                        candle_index=i,
                        event_time=candle.close_time,
                        price=key_low.price,
                        level_id=candidate_high.level_id,
                        level_price=candidate_high.price,
                        note=(
                            "Interleaved bearish structure update confirmed; the new key LL is below the live key LL "
                            "and the intervening protected LH remains below the live protected LH."
                        ),
                    )
                )

        structural_kinds = {
            MarketEventKind.BULLISH_STRUCTURE_CONFIRMED, MarketEventKind.BEARISH_STRUCTURE_CONFIRMED,
            MarketEventKind.BULLISH_STRUCTURE_BROKEN_BOS, MarketEventKind.BEARISH_STRUCTURE_BROKEN_BOS,
            MarketEventKind.BULLISH_CONF_CONFIRMED, MarketEventKind.BEARISH_CONF_CONFIRMED,
        }
        for j in range(first_event_this_candle, len(events)):
            if events[j].kind in structural_kinds:
                events[j] = replace(events[j], recovery_transition_ids=recovery_transition_ids)
        trend_trace.append(trend)

    if active_transition is not None:
        if not active_transition["rejection_reasons"]:
            _transition_reject("END_OF_DATA_BEFORE_POST_BOS_STRUCTURE_RESOLUTION")
        _finish_transition(
            resolved_index=None,
            resolved_time=None,
            resolved_trend=None,
            resolution_mode="UNRESOLVED_END_OF_DATA",
            selected_anchor_level_id=transition_anchor_level_id,
            selected_correction_level_id=transition_correction_level_id,
        )

    ob_readiness = OrderBlockReadiness(
        enabled=False,
        status="BLOCKED_PENDING_CONTEXT",
        blocking_reasons=(
            "HTF POI engine is not implemented yet.",
            "The specialized OB source requires an aggressive impulse but does not define a numeric threshold; no threshold is invented here.",
            "IMB wording is source-ambiguous (quality emphasis vs warning not to ignore it) and has not yet been frozen as hard/soft validity.",
            "Structural-impulse and trend-alignment context are not yet complete enough for automatic OB validation.",
            "Phase 1.4.20 therefore still does not automatically label real-market candles as valid/tradeable Order Blocks.",
        ),
    )

    if timeframe_minutes is None:
        sfp_preference = "TIMEFRAME_UNKNOWN"
    elif timeframe_minutes >= 60:
        sfp_preference = "SOURCE_PREFERRED_H1_PLUS"
    else:
        sfp_preference = "SOURCE_VALID_BELOW_PREFERRED_H1"

    return MarketAnalysisReport(
        candle_count=len(candles),
        analysis_mode=analysis_mode,
        final_trend=trend,
        levels=tuple(levels),
        sweep_episodes=tuple(sweep_episodes),
        events=tuple(events),
        order_block_readiness=ob_readiness,
        structure_policy=(
            "HH/HL and LL/LH use confirmed 3-candle swings in chronological alternating order; once a live trend exists, "
            "new key HH/LL updates must exceed the current key extreme and the intervening HL/LH must remain beyond the current protected point. "
            "Bullish BOS breaks protected HL; bearish BOS breaks protected LH. Phase 1.4.12 prioritizes the source-expected opposite "
            "LL+LH / HH+HL transition after BOS, keeps CONF separate, and retains a strictly post-BOS local-structure fallback so the "
            "software BROKEN transition cannot remain locked merely because the expected fast-path normalization did not complete. "
            "Interleaved ordering, live-key update selection, same-direction post-BOS recovery, BOS-leg anchoring, and transition selection "
            "are TECHNICAL_NORMALIZATION; no timeout is invented."
        ),
        sfp_timeframe_preference=sfp_preference,
        sfp_policy=(
            "SOURCE: SFP may form on structural highs/lows of any timeframe; the material says H1 and "
            "above are the preferred timeframes for searching for SFP. A confirmed SFP formation is not "
            "an entry: after formation, move to a lower timeframe and wait for BOS before seeking entry. "
            "Base analysis emits structural-swing SFP; the Range layer may augment the report with "
            "source-supported range-boundary SFP while preserving provenance."
        ),
        trend_state_segments=_compress_trend_states(candles, trend_trace),
        structure_transition_diagnostics=tuple(transition_diagnostics),
        sfp_liquidity_scope="STRUCTURAL_SWING_ONLY_RANGE_BOUNDARY_PENDING",
    )
