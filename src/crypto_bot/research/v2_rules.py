"""Small offline predicates and seven-component scores; no labels accepted."""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from crypto_bot.research.v2_common import Row, canonical

FRICTION = [.30, .20, .15, .10, .075, .05]
NET_TARGET = [.5, .75, 1., 1.5, 2., 2.5, 3.]
GROSS_TARGET = [1., 1.5, 2., 2.5, 3.]
SCOPES = ['ALL', 'CORE_A', 'CORE_B', 'CORE_C', 'CORE_AB', 'CORE_ABC', 'CONFLUENCE_2',
          'BREAKER_RANGE_CONTEXT', 'BREAKER_SFP', 'BREAKER_RANGE_FAMILY']
LOGISTIC_FEATURES = ['core_breaker', 'strong_range_context', 'macro_flow_aligned',
                     'liquidity_swept_count', 'first_test', 'net_target_R', 'friction_R']
TREE_FEATURES = LOGISTIC_FEATURES + ['sweep_ATR', 'SL_ATR', 'gross_target_R', 'zone_age_bars',
                                    'structure_age_bars', 'displacement_ATR', 'PD_allowed', 'OTE']
SCORE_FEATURES = ['core_breaker', 'strong_range_context', 'macro_flow_aligned', 'multi_sweep',
                  'first_test', 'net_target_1', 'friction_015']
SCORE_PROFILES = {'equal': [1, 1, 1, 1, 1, 1, 1], 'source_hint': [2, 2, 2, 1, 1, 2, 2],
                  'cost_first': [1, 1, 1, 1, 1, 3, 3]}
EXTENSIONS = [
    ('macro_flow_aligned', '>=', 1), ('first_test', '>=', 1),
    ('liquidity_swept_count', '>=', 2), ('liquidity_swept_count', '>=', 3),
    ('zone_age_bars', '<=', 4), ('zone_age_bars', '<=', 8),
    ('structure_age_bars', '<=', 4), ('structure_age_bars', '<=', 8),
    ('PD_allowed', '>=', 1), ('OTE', '>=', 1), ('displacement_ATR', '>=', 1),
    ('sweep_ATR', '>=', .1), ('adverse_liquidity_count', '<=', 0), ('recent_range_context', '>=', 1),
    *[('gross_target_R', '<=', v) for v in [.5, .75, 1., 1.5, 2.]]]


def column(rows: list[Row], key: str) -> Any:
    return np.array([float(r[key]) if r.get(key) is not None else np.nan for r in rows])


def design(rows: list[Row], fields: list[str]) -> Any:
    assert set(fields) <= set(TREE_FEATURES), 'Feature allowlist rejects identity/time/outcome inputs'
    return np.column_stack([column(rows, f) for f in fields])


def scope_mask(rows: list[Row], scope: str) -> Any:
    a = column(rows, 'core_breaker') == 1
    b = column(rows, 'core_range') == 1
    c = column(rows, 'core_sfp') == 1
    return {'ALL': np.ones(len(rows), dtype=bool), 'CORE_A': a, 'CORE_B': b, 'CORE_C': c,
            'CORE_AB': a | b, 'CORE_ABC': a | b | c,
            'CONFLUENCE_2': column(rows, 'physical_family_count') >= 2,
            'BREAKER_RANGE_CONTEXT': a & (column(rows, 'recent_range_context') == 1),
            'BREAKER_SFP': column(rows, 'breaker_sfp_confluence') == 1,
            'BREAKER_RANGE_FAMILY': column(rows, 'breaker_range_confluence') == 1}[scope]


def condition_mask(rows: list[Row], condition: list[Any] | tuple[Any, ...]) -> Any:
    feature, op, value = condition
    x = column(rows, feature)
    return np.isfinite(x) & (x <= value if op == '<=' else x >= value)


def rule_id(rule: Row) -> str:
    return hashlib.sha256(canonical(rule).encode()).hexdigest()[:20]


def rule_mask(rows: list[Row], rule: Row) -> Any:
    mask = scope_mask(rows, rule['scope'])
    for condition in rule['conditions']:
        mask &= condition_mask(rows, condition)
    return mask


def score(rows: list[Row], profile: str) -> Any:
    x = np.column_stack([
        column(rows, 'core_breaker') == 1, column(rows, 'strong_range_context') == 1,
        column(rows, 'macro_flow_aligned') == 1, column(rows, 'liquidity_swept_count') >= 2,
        column(rows, 'first_test') == 1, column(rows, 'net_target_R') >= 1,
        column(rows, 'friction_R') <= .15])
    return x @ np.array(SCORE_PROFILES[profile])


def candidate_mask(rows: list[Row], rule: Row) -> Any:
    if rule['kind'] == 'RULE':
        return rule_mask(rows, rule)
    if rule['kind'] == 'SCORE':
        return score(rows, rule['profile']) >= rule['threshold']
    raise ValueError('Meta-filter requires frozen model evaluation')
