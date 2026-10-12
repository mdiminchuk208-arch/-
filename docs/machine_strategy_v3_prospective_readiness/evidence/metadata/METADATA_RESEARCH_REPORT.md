# Prospective Bybit metadata capture, 2026-10-12 UTC

**Verdict: STOP for opening a BTCUSDT or ETHUSDT prospective tick epoch.**

The public Bybit V5 `instruments-info` request with `category=linear` and each
exact symbol returned HTTP 403. The 96-byte response says the CloudFront
distribution blocks access from this country. Its SHA-256 is
`7ef856c945703d5772f1b1f2a8c65913247c9b0769302b10facfe14fa1e2083c`
for both requests. Neither response contains a result list, exact contract
identity, `priceFilter`, or `tickSize`. The request and retrieval times are in
the individual receipt files. A current tick value or executable price grid
cannot be established from these responses.

The official announcement index was accessible (HTTP 200), as were four dated
tick-change notice pages. A fifth notice URL returned 301; its official
same-host canonical URL was independently requested and returned 200. The
2023-01-06 ETHUSDT and 2023-02-07 BTCUSDT notices contain the respective
symbol and issuer publication fields, but both precede this retrieval by years.
They are historical notice leads, not evidence that the advertised rules are
active now or that no intervening change occurred. The 2025-02-11 and
2025-05-21 pages contain no literal BTCUSDT or ETHUSDT symbol in their raw
responses. This limited check does not prove those notices are irrelevant to
all contract families or establish complete notice coverage. The announcement
index is a bounded discovery checkpoint, not a complete notice-history proof.

`CAPTURE_INVENTORY.json` records the eight bounded requests and their outcomes.
Every `.body` file contains the raw response bytes; its paired `.receipt.json`
records the requested HTTPS URL, public unauthenticated GET, request header
allowlist, request and retrieval UTC times, status, response header allowlist,
SHA-256, byte length and any transport/truncation error. Redirects were never
followed automatically. Body paths in receipts are relative to `docs/`.
Inventory generation re-read all eight bodies and verified hashes, lengths and
request-before-retrieval ordering. No private API, credential, order or strategy
state was accessed.

The collector used the inherited proxy and TLS trust. The managed environment
reported desired unrestricted HTTP policy with enforcement state `unknown`;
the actual 403 response is the relevant API observation. A later authorized
capture can open an epoch no earlier than its own verified known-at boundary,
after checking `retCode=0`, a singleton matching `LinearPerpetual`/USDT
instrument record, `priceFilter.tickSize`, and relevant effective notices.
Repeated equal snapshots would still leave intervening changes unproved.
Failed receipts and older notices cannot be backdated into a current epoch.
