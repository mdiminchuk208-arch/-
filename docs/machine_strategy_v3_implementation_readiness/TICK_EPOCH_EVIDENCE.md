# Historical price tick evidence

Verdict: NO_VERIFIED_HISTORICAL_TICK_EPOCHS for BTCUSDT/ETHUSDT, development
2023-01-01T00:00Z through 2025-12-05T23:30Z exclusive, and 2022 warmup.
TICK_EPOCHS.json represents these intervals with null tick/known/effective values
and UNVERIFIED status. `verified_core_epochs` is empty. Notice claims below are
leads, not executable epoch rows or proof of the complete interval.

## ETH official notice, independently archived

Original URL:
https://announcements.bybit.com/article/changes-to-tick-size-for-ethusdt-perpetual-contract-2023-01-06--bltb4b6d3ffa3c5206c/

Immutable capture URL:
https://arquivo.pt/wayback/20230205041038id_/https://announcements.bybit.com/article/changes-to-tick-size-for-ethusdt-perpetual-contract-2023-01-06--bltb4b6d3ffa3c5206c/

The title date is 2023-01-06. The page date field is 2023-01-06 07:03:06
(timezone not independently proven). The literal article body states effective
2023-01-17 08:00 UTC, ETHUSDT tick 0.05 -> 0.01. Archive/Memento capture is
2023-02-05T04:10:38Z; retrieval is separately retained in the receipt. Full
response SHA-256 is
43823daf528216e1cc4f55b511b1ea1e68d955820b95af95882fff292314c9a9.
The Arquivo CDX receipt and body retain capture identity, WARC location and
digest OS6VJXIWIPDBG5CT75XJ75QY4FAI24XG. Literal normalized article text SHA-256
is 7c7499498f767e5c58178a017987518979e588d9f98c7c4a398d21842ca74bcf.

The capture is after the stated effective time. It proves archived text existed
by capture, not a causally available publication before the effective change,
actual exchange application, the earlier setting's full lifetime or all subsequent
unchanged periods. No interval is promoted to verified on that basis.

## BTC official notice, current retrieval

https://announcements.bybit.com/en/article/changes-to-tick-size-for-usdt-usdc-perpetual-contracts-2023-02-08--blt80c14139bdd327bc/

Title date 2023-02-08; page date field 2023-02-07 11:02:47 (timezone not proven).
Body effective 2023-02-10 08:00 UTC, BTCUSDT tick 0.5 -> 0.1. Current full-response
SHA-256 c0787c9c5e51f355e7b87cd8cd053427d2c7b6be8193c8a7081e4fa079ce1153;
literal text SHA-256
b827508fd126ac8410c603e2476e0e3e8840b80028cb34985068c8fc055ff501.
The title/page/effective/retrieval fields remain separate. Arquivo exact-URL CDX
returned no records; that is not proof that no contemporaneous notice/capture or
later rule change exists. No complete epoch is proven by the current page.

## Search limits and required future evidence

execution_auditor.md records official archive/search attempts and retrieval limits.
Late Wayback captures do not prove historical known-at. Failed Common Crawl
requests do not prove archive absence. Related-navigation mentions are not article
body evidence for these symbols. Search silence cannot prove continuous unchanged
settings. Current instruments-info and candle decimal precision were not accepted
as historical epoch proof.

A later gate needs source and effective-application/continuity evidence with
immutable bytes/hashes, exact symbol/contract, complete nonoverlapping intervals,
and causally known publication times. The historical runner validates manifest
membership and hashes of both source/effective-proof files in addition to the
frozen pure-core epoch schema. No private API or exchange credentials are used.
