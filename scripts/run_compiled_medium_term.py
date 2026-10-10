"""Equivalent medium research compiler: lazy target snapshots, spent-path skip.

Source engine/policy are immutable. This explicitly registered implementation
reduces work whose result cannot affect an already retained physical idea.
"""
from __future__ import annotations

import math
from dataclasses import asdict
from pathlib import Path

import run_medium_term_research as runner

from crypto_bot.strategy.source_medium_term import MediumTermEngine
from crypto_bot.strategy.source_pdf_native import sign


class CompiledMediumTermEngine(MediumTermEngine):
    def _conservative(self, context, now):
        # _emit already prohibits all retained physical IDs. Native watches and
        # main lifecycle stay active; only useless refinement rescans disappear.
        if context.physical_id in self._retained:
            return
        return super()._conservative(context, now)

    def _targets(self, direction, entry, now, range_zone=None):
        s = sign(direction)
        candidates = []
        for tf in (240, 1440):
            owner = self.series[tf]
            for z in owner.zones:
                if z.direction == direction or z.kind == 'RANGE_POI' or not z.fresh(now):
                    continue
                price = z.low if s == 1 else z.high
                if s * (price-entry) > 0:
                    candidates.append({'price': price, 'tf': tf, 'kind': z.kind,
                                       'known_at': z.known_at, 'source': z})
            for p in owner.pools.values():
                if (p.classification == 'EXTERNAL' and p.side == ('high' if s == 1 else 'low')
                        and p.known_at <= now and s*(p.price-entry) > 0):
                    candidates.append({'price': p.price, 'tf': tf, 'kind': 'EXTERNAL_LIQUIDITY',
                                       'known_at': p.known_at, 'source': p})
        if range_zone is not None:
            boundary = math.nextafter(range_zone.high if s == 1 else range_zone.low,
                                      range_zone.low if s == 1 else range_zone.high)
            if s*(boundary-entry) > 0:
                candidates.append({'price': boundary, 'tf': range_zone.confluence.get('native_pattern_tf', 240),
                                   'kind': 'SOURCE_RANGE_BOUNDARY', 'known_at': range_zone.known_at,
                                   'source': range_zone})
        unique = []
        for c in sorted(candidates, key=lambda x: (s*x['price'], -x['tf'], x['kind'])):
            if not unique or c['price'] != unique[-1]['price']:
                unique.append(c)
        # No state advances between eligibility/sorting and these three copies.
        return [{**c, 'source': asdict(c['source'])} for c in unique[:3]]


def main():
    original_fingerprint = runner.fingerprint

    def registered_fingerprint(cohort, symbols, policy):
        lock = original_fingerprint(cohort, symbols, policy)
        path = Path(__file__).resolve()
        doc = runner.REPO / 'MEDIUM_TERM_COMPILATION_PROTOCOL.md'
        lock['code_and_data_hashes'][str(path.relative_to(runner.REPO))] = runner.digest(path)
        lock['code_and_data_hashes'][str(doc.relative_to(runner.REPO))] = runner.digest(doc)
        lock['equivalent_compiler'] = 'LAZY_THREE_TARGET_SNAPSHOTS_AND_SKIP_RETAINED_REFINEMENT'
        return lock

    # Explicit model injection before registration and worker construction;
    # compiler source/protocol are dependencies in every new manifest.
    runner.MediumTermEngine = CompiledMediumTermEngine
    runner.fingerprint = registered_fingerprint
    runner.main()


if __name__ == '__main__':
    main()
