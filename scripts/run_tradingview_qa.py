from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from crypto_bot.qa.tradingview import (
    TradingViewQARunner,
    build_tradingview_qa_plan,
    subprocess_tv_transport,
)


def _json_native(value: Any) -> Any:
    return json.loads(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    )


def _write_json(payload: dict[str, Any], output: str | None) -> None:
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if output is None:
        print(text, end="")
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(json.dumps({"written": str(path), "trade_entry_allowed": False}), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or explicitly execute a local TradingView visual QA plan. "
            "This tool is QA-only and cannot place replay or real trades."
        )
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument(
        "--chart-symbol",
        required=True,
        help="Explicit TradingView ticker, e.g. OKX:BTCUSDT.P. No silent mapping is performed.",
    )
    parser.add_argument(
        "--replay-at",
        required=True,
        help="Timezone-aware ISO-8601 causal review boundary.",
    )
    parser.add_argument("--timeframes", nargs="+", default=["D", "240", "60", "15"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--tv-executable", default="tv")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    try:
        replay_at = datetime.fromisoformat(args.replay_at)
        plan = build_tradingview_qa_plan(
            case_id=args.case_id,
            chart_symbol=args.chart_symbol,
            replay_at=replay_at,
            timeframes=tuple(args.timeframes),
        )
    except (ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if not args.execute:
        payload = {
            "mode": "PLAN_ONLY",
            "plan": plan.to_dict(),
            "trade_entry_allowed": False,
        }
        _write_json(payload, args.output)
        return 0

    transport = partial(subprocess_tv_transport, executable=args.tv_executable)
    try:
        result = TradingViewQARunner(
            transport=transport,
            timeout_seconds=args.timeout_seconds,
        ).run(plan)
    except (RuntimeError, OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "plan_id": plan.plan_id,
                    "error": str(exc),
                    "trade_entry_allowed": False,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    payload = {
        "mode": "EXECUTED_LOCAL_QA",
        "plan": plan.to_dict(),
        "result": _json_native(asdict(result)),
        "trade_entry_allowed": False,
    }
    _write_json(payload, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
