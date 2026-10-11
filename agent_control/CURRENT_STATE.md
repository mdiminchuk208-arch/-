# Current State

Frozen workflow head before v3 research:
`ba65e91c2b1675f48e80ac785bb3adf89d17bb0b`

Development results:
- v2: 223 CLOSED, WR 52.9148%, PF 0.68294, expectancy -0.21520R, Net -47.9898R, MaxDD 78.9546R.
- v2.1: 83 CLOSED, WR 45.7831%, PF 0.83755, expectancy -0.13665R, Net -11.3418R, MaxDD 29.0633R.
- v2.2: 39 CLOSED, WR 33.3333%, PF 0.89625, expectancy -0.14008R, Net -5.4633R, MaxDD 23.6498R.

Important diagnostic from frozen v2 breakdown:
- LONG: 118 CLOSED, PF ~1.4625, expectancy ~+0.2294R, Net ~+27.073R.
- SHORT: 105 CLOSED, PF ~0.1913, expectancy ~-0.7149R, Net ~-75.063R.

This asymmetry is diagnostic only and must not be converted directly into a production rule without causal analysis and a new pre-outcome specification.

Execution caveats:
- historical exact tick epochs not proven;
- modeled normalized-R costs;
- funding unavailable/excluded;
- no independent forward/OOS validation;
- no paper session.

Production candidate: NONE.
PAPER_TRADING_READY=false.
REAL_TRADING_READY=false.
trade_entry_allowed=false.