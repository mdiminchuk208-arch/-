from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict

from crypto_bot.integration.delivery import HttpDeliveryConfig, deliver_pending
from crypto_bot.integration.outbox import SQLiteEngineOutbox


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deliver durable Crypto Bot engine events to an explicitly configured backend endpoint. "
            "This transport does not create signals or grant trade execution permission."
        )
    )
    parser.add_argument("--outbox", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--bearer-token-env", default="CRYPTO_BOT_BACKEND_TOKEN")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--allow-http-localhost", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive")

    token = os.getenv(args.bearer_token_env) if args.bearer_token_env else None
    try:
        config = HttpDeliveryConfig(
            endpoint=args.endpoint,
            timeout_seconds=args.timeout_seconds,
            bearer_token=token,
            allow_plain_http_localhost=args.allow_http_localhost,
        )
        outbox = SQLiteEngineOutbox(args.outbox)
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    while True:
        results = deliver_pending(
            outbox,
            config=config,
            limit=args.batch_size,
        )
        payload = {
            "ok": all(item.delivered for item in results),
            "attempted": len(results),
            "delivered": sum(1 for item in results if item.delivered),
            "results": [asdict(item) for item in results],
            "trade_entry_allowed": False,
        }
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False), flush=True)

        if args.once:
            return 0 if payload["ok"] else 2
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
