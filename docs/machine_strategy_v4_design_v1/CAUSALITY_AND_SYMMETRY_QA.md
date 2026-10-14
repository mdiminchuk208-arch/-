# v4 design QA scope

QA uses synthetic Decimal fixtures and a test-only contract reference interpreter. It does not discover historical formations, import the historical adapter, build a historical catalog, simulate real historical cases or compute financial performance. Design PASS is not implementation readiness.

Coverage: all five setup families and mirrored lattice handling, same-direction CONF selection/opposite-event timing, CLEAN/CORRECTIVE/INVALID versus missing-evidence WAIT, future-event mutation and prefix stability, raw and inward FTA before reservation, target equality, parent formation-based half-open deadline, prospective CLOSE/POI retirement, pending versus filled-position exits, modeled outside-POI contact, exact doubled-cost payoff equality and both directions, Q cancellation versus fixed U, all nine scenarios, source/policy separation and preserved ambiguities, telemetry emission-only isolation, pin tampering/missing/path rejection and external manifest mismatch.

No completed TF may become known before its end; current-bar CLOSE/POI events cannot cancel a fill earlier in that bar. No future funding, holding time or outcomes are admission fields. Full production prefix/future-mutation/replay on adapter/runner belongs to a later implementation-readiness gate and remains unrun here. All pinned inherited source/code inputs and parent audit hashes are preserved.

See QA_RECEIPT.json and qa/ for executed commands and byte hashes. An initial test fixture used the word native where the normative label says raw structural POI; that string assertion was corrected without changing the contract. Final synthetic payoff equality fixtures use exact finite Decimal arithmetic without an epsilon.
