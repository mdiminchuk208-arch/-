# Compatibility v1 causality report

Independent role: `/root/okx_compatibility_no_lookahead_auditor`; verdict CAUSALITY_REVIEW_PASS. The reviewer authored no implementation and independently reran 30 tests.

Policy committed before implementation at 23f275cae85d1cab4d91cc07351ffdef2560d75d. Stage A e8733326e85b6082a33f11ec001066d33bc345bcded6acda26b54cd56ddeb9f0 and its entire transitive artifact map pass externally pinned verification; sources were not recollected. Protected v2/core/v3 contracts/runner/adapter bytes match the preregistration. New historical financial namespace is absent at review.

The new plan_pending and catalog run reuse the exact protected code objects. Only globals inject the counted metadata/model contract and an audit-only reservation callback; discovery executes protected discovery before adding logs. The cloned execution AST changes only metadata resolution, model evidence labels, and which prices are checked on synthetic order grids. Native observed OHLC is unrounded. Future GeometryIndex objects become visible only through protected completed-frame advancement. The exclusive UTC endpoint excludes new H1 decisions at end_exclusive.

A deterministic 60-day synthetic native fixture emits a candidate. At a 50-day cutoff, truncated-prefix, full-input and mutated-future inputs yield identical orders and audits, including target inventories and reservations. Confirmation and target known_at are <=decision. An injected prior physical reservation produces a recorded conflict with all ordered proposals and stable IDs/dispositions/reasons. This fixture samples one emitted candidate; it does not independently cover all branches. Wider decision logic remains hash protected.

All nine scenarios re-use one common pre-entry reference catalog, sibling selection and POI/physical reservation. Coarser grid failure or target identity change retains the candidate and forces STOP. Cost doubling cannot change admission or the observed path. Fixed reference U and positive floored contract sizing bind LONG/SHORT and BTC/ETH cash consistently. Funding signed rates and settlement-close proxy are used only after execution events; minimum cash is selected among coherent event-order witnesses. No future holding duration is a signal input.

Before READY, financial kernels reject missing/forged capabilities and arbitrary data under a toy fixture scope. Only nine registered tiny synthetic fixture names can be evaluated. A committed READY manifest, ancestor policy commit, exact namespace/artifact hashes, and campaign-control/code pins are required for historical evaluation. One-shot authority and externally pinned checkpoint hashes protect interruption resume. PAPER/LIVE=false; trade_entry_allowed=false.

Exact review pins and resolved findings are in CAUSALITY_REVIEW.json. Historical fee/mark/filter epochs, liquidity, queue/partial fills and actual venue timing remain unverified. This is a declared compatibility model, not a universal adverse bound or a production qualification.

Oct14 narrow followup: remote control-only updates advanced HEAD to f5fa7bf0. Exact two permitted campaign headers are checked; current control pins refreshed before READY; guard/source remain independently PASS. Frozen dates and policies were not changed.
