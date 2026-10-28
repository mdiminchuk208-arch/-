from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from crypto_bot.runtime.health_store import check_runtime_health_file


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the durable health receipt of the fail-closed live diagnostic service."
    )
    parser.add_argument("--health-file", required=True)
    parser.add_argument("--max-age-seconds", type=float, default=120.0)
    args = parser.parse_args()

    if args.max_age_seconds <= 0:
        parser.error("--max-age-seconds must be positive")

    result = check_runtime_health_file(
        args.health_file,
        now=datetime.now(timezone.utc),
        max_age_seconds=args.max_age_seconds,
    )
    payload = _jsonable(asdict(result))
    payload["health_file"] = args.health_file
    payload["trade_entry_allowed"] = False
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False), flush=True)
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
