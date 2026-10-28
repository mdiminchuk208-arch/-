from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


TRADINGVIEW_QA_SCHEMA = "crypto-bot.tradingview-qa-plan.v1"
_ALLOWED_TOP_LEVEL = {"status", "symbol", "timeframe", "replay", "ohlcv", "screenshot"}
_ALLOWED_REPLAY_ACTIONS = {"start", "status", "stop"}


@dataclass(frozen=True)
class TradingViewQAStep:
    step_id: str
    command: tuple[str, ...]
    purpose: str

    def __post_init__(self) -> None:
        if not self.step_id.strip() or not self.purpose.strip():
            raise ValueError("QA step_id and purpose must be non-empty")
        if not self.command:
            raise ValueError("QA command must be non-empty")
        if self.command[0] not in _ALLOWED_TOP_LEVEL:
            raise ValueError(f"TradingView QA command is not allowed: {self.command[0]}")
        if self.command[0] == "replay":
            if len(self.command) < 2 or self.command[1] not in _ALLOWED_REPLAY_ACTIONS:
                raise ValueError("TradingView QA replay command is restricted to start/status/stop")
        if "trade" in self.command:
            raise ValueError("TradingView replay trade commands are forbidden in QA adapter")


@dataclass(frozen=True)
class TradingViewQAPlan:
    schema: str
    plan_id: str
    case_id: str
    chart_symbol: str
    replay_at: str
    timeframes: tuple[str, ...]
    steps: tuple[TradingViewQAStep, ...]
    qa_only: bool
    trade_entry_allowed: bool

    def __post_init__(self) -> None:
        if self.schema != TRADINGVIEW_QA_SCHEMA:
            raise ValueError(f"unsupported TradingView QA schema: {self.schema!r}")
        if not self.plan_id.strip() or not self.case_id.strip() or not self.chart_symbol.strip():
            raise ValueError("plan_id, case_id and chart_symbol must be non-empty")
        replay = datetime.fromisoformat(self.replay_at)
        if replay.tzinfo is None or replay.utcoffset() is None:
            raise ValueError("replay_at must be timezone-aware")
        if not self.timeframes or len(set(self.timeframes)) != len(self.timeframes):
            raise ValueError("timeframes must be non-empty and unique")
        if not self.qa_only:
            raise ValueError("TradingView adapter is QA-only")
        if self.trade_entry_allowed:
            raise ValueError("TradingView QA plan cannot enable trade entry")

    def to_dict(self) -> dict[str, Any]:
        return json.loads(
            json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        )


@dataclass(frozen=True)
class TradingViewQAStepResult:
    step_id: str
    command: tuple[str, ...]
    output: Any


@dataclass(frozen=True)
class TradingViewQAResult:
    plan_id: str
    completed_steps: tuple[TradingViewQAStepResult, ...]
    qa_only: bool
    trade_entry_allowed: bool


CLITransport = Callable[[tuple[str, ...], float], Any]


def _stable_plan_id(base: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(base, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_tradingview_qa_plan(
    *,
    case_id: str,
    chart_symbol: str,
    replay_at: datetime,
    timeframes: Sequence[str] = ("D", "240", "60", "15"),
) -> TradingViewQAPlan:
    """Build a deterministic visual-review plan without inferring ticker mapping.

    ``chart_symbol`` is explicit because TradingView ticker identifiers can differ
    from OKX REST instrument IDs. The QA layer must never silently map one market
    identity to another.
    """
    if replay_at.tzinfo is None or replay_at.utcoffset() is None:
        raise ValueError("replay_at must be timezone-aware")
    case_id = case_id.strip()
    chart_symbol = chart_symbol.strip()
    tf = tuple(str(item).strip() for item in timeframes)
    if not case_id or not chart_symbol:
        raise ValueError("case_id and chart_symbol must be non-empty")
    if not tf or any(not item for item in tf) or len(set(tf)) != len(tf):
        raise ValueError("timeframes must be non-empty and unique")

    replay_iso = replay_at.isoformat()
    steps: list[TradingViewQAStep] = [
        TradingViewQAStep("status", ("status",), "Verify local TradingView/CDP connection"),
        TradingViewQAStep("symbol", ("symbol", chart_symbol), "Select explicit chart market"),
    ]
    for index, timeframe in enumerate(tf):
        prefix = f"tf{index + 1}-{timeframe}"
        steps.extend(
            (
                TradingViewQAStep(
                    f"{prefix}-timeframe",
                    ("timeframe", timeframe),
                    f"Select {timeframe} chart timeframe",
                ),
                TradingViewQAStep(
                    f"{prefix}-replay",
                    ("replay", "start", replay_iso),
                    f"Move replay boundary to the causal review timestamp on {timeframe}",
                ),
                TradingViewQAStep(
                    f"{prefix}-ohlcv",
                    ("ohlcv", "--summary"),
                    f"Capture compact OHLCV context for {timeframe}",
                ),
                TradingViewQAStep(
                    f"{prefix}-screenshot",
                    ("screenshot", "-r", "chart"),
                    f"Capture chart screenshot for {timeframe}",
                ),
                TradingViewQAStep(
                    f"{prefix}-stop",
                    ("replay", "stop"),
                    f"Leave replay mode before changing the next timeframe",
                ),
            )
        )

    base = {
        "schema": TRADINGVIEW_QA_SCHEMA,
        "case_id": case_id,
        "chart_symbol": chart_symbol,
        "replay_at": replay_iso,
        "timeframes": tf,
        "steps": [asdict(item) for item in steps],
        "qa_only": True,
        "trade_entry_allowed": False,
    }
    return TradingViewQAPlan(
        plan_id=_stable_plan_id(base),
        steps=tuple(steps),
        **{key: value for key, value in base.items() if key != "steps"},
    )


def subprocess_tv_transport(
    command: tuple[str, ...],
    timeout_seconds: float,
    *,
    executable: str = "tv",
) -> Any:
    """Execute one local TradingView MCP CLI command and parse JSON output."""
    completed = subprocess.run(
        [executable, *command],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            f"TradingView CLI failed ({completed.returncode}) for {command!r}: {stderr[:1000]}"
        )
    raw = completed.stdout.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TradingView CLI did not return JSON") from exc


class TradingViewQARunner:
    """Explicit local-only runner for deterministic QA plans.

    This class is never imported by the production live runtime. The caller must
    opt in by constructing it and supplying a local CLI transport/executable.
    """

    def __init__(
        self,
        *,
        transport: CLITransport,
        timeout_seconds: float = 20.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def run(self, plan: TradingViewQAPlan) -> TradingViewQAResult:
        if not plan.qa_only or plan.trade_entry_allowed:
            raise ValueError("TradingView QA runner accepts fail-closed QA plans only")
        results: list[TradingViewQAStepResult] = []
        for step in plan.steps:
            # Re-validate in case a plan was deserialized/reconstructed outside
            # build_tradingview_qa_plan.
            step.__post_init__()
            output = self.transport(step.command, self.timeout_seconds)
            results.append(
                TradingViewQAStepResult(
                    step_id=step.step_id,
                    command=step.command,
                    output=output,
                )
            )
        return TradingViewQAResult(
            plan_id=plan.plan_id,
            completed_steps=tuple(results),
            qa_only=True,
            trade_entry_allowed=False,
        )
