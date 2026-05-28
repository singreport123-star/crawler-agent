"""Execution VM.

Reads an immutable execution_plan.json, builds runtime_state.json, and
executes steps in order. The plan is NEVER mutated. All dynamic state
(step results, retries, errors) lives in runtime_state.

Variable interpolation handled here (runtime scope only):
    {{input.xxx}}
    {{steps.<id>.outputs.<key>}}
    {{loop.xxx}}        (reserved, Phase 2)

Compile-time vars ({{selectors.xxx}}, {{endpoints.xxx}}) are assumed
already resolved by the Compiler and must not appear at runtime.

Retry is a runtime POLICY read from config.json — it is not in the plan.
"""

from __future__ import annotations

import copy
import json
import os
import re
import time
from typing import Any, Dict, List

from .action_handlers import HANDLERS
from .schemas import ErrorContract, StepError, StepResult

_VAR_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class Runtime:
    def __init__(self, plan: Dict[str, Any], inputs: Dict[str, Any],
                 config: Dict[str, Any], state_path: str):
        # deep copy so the in-memory plan can never be mutated by handlers
        self._plan = copy.deepcopy(plan)
        self.inputs = inputs
        self.config = config
        self.state_path = state_path

        self.state: Dict[str, Any] = {
            "plan_hash": self._plan.get("plan_hash"),
            "site": self._plan.get("site"),
            "inputs": inputs,
            "steps": {},
            "status": "running",
            "error": None,
        }
        self._flush_state()

    # ---------- state ----------
    def _flush_state(self) -> None:
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ---------- interpolation ----------
    def _lookup(self, expr: str) -> Any:
        parts = expr.split(".")
        root = parts[0]

        if root == "input":
            cur: Any = self.inputs
            for p in parts[1:]:
                cur = cur[p]
            return cur

        if root == "steps":
            # steps.<id>.outputs.<key>
            step_id = parts[1]
            cur = self.state["steps"][step_id]
            for p in parts[2:]:
                cur = cur[p]
            return cur

        if root == "loop":
            raise StepError(
                code="UNSUPPORTED_SCOPE",
                message="loop scope not available in Milestone 1",
                retryable=False,
                details={"expr": expr},
            )

        if root in ("selectors", "endpoints"):
            raise StepError(
                code="UNRESOLVED_COMPILE_VAR",
                message=f"compile-time var leaked into runtime: {expr}",
                retryable=False,
                details={"expr": expr},
            )

        raise StepError(
            code="UNKNOWN_SCOPE",
            message=f"unknown variable scope: {root}",
            retryable=False,
            details={"expr": expr},
        )

    def _interpolate(self, value: Any) -> Any:
        if isinstance(value, str):
            m = _VAR_PATTERN.fullmatch(value.strip())
            if m:
                # whole-string is a single var → preserve native type
                return self._lookup(m.group(1))
            # embedded vars → stringify
            return _VAR_PATTERN.sub(
                lambda mm: str(self._lookup(mm.group(1))), value
            )
        if isinstance(value, dict):
            return {k: self._interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._interpolate(v) for v in value]
        return value

    # ---------- execution ----------
    def _run_step_once(self, step: Dict[str, Any]) -> StepResult:
        handler = HANDLERS.get(step["type"])
        if handler is None:
            raise StepError(
                code="UNKNOWN_ACTION",
                message=f"no handler for type: {step['type']}",
                retryable=False,
                details={"type": step["type"]},
            )
        resolved = self._interpolate(step)
        return handler(step, resolved)

    def _run_step(self, step: Dict[str, Any]) -> StepResult:
        policy = self.config.get("retry", {})
        max_attempts = int(policy.get("max_attempts", 1))
        backoff_ms = int(policy.get("backoff_ms", 0))
        retry_codes = policy.get("retry_on_codes")  # None => any retryable

        attempt = 0
        last_error: ErrorContract | None = None
        while attempt < max_attempts:
            attempt += 1
            try:
                result = self._run_step_once(step)
                result.meta["attempts"] = attempt
                return result
            except StepError as e:
                last_error = e.error
                allowed = e.error.retryable and (
                    retry_codes is None or e.error.code in retry_codes
                )
                if attempt < max_attempts and allowed:
                    if backoff_ms:
                        time.sleep(backoff_ms / 1000.0)
                    continue
                break
            except Exception as e:  # noqa: BLE001 — wrap unexpected errors
                last_error = ErrorContract(
                    code="UNHANDLED_EXCEPTION",
                    message=str(e),
                    retryable=False,
                    details={"exception": type(e).__name__},
                )
                break

        return StepResult(
            status="failed",
            outputs={},
            meta={"attempts": attempt},
            error=last_error,
        )

    def run(self) -> bool:
        for step in self._plan["steps"]:
            step_id = step["id"]
            result = self._run_step(step)
            self.state["steps"][step_id] = result.model_dump()
            self._flush_state()

            if not result.is_success():
                self.state["status"] = "failed"
                self.state["error"] = result.error.model_dump() if result.error else None
                self.state["failed_step"] = step_id
                self._flush_state()
                return False

        self.state["status"] = "success"
        self._flush_state()
        return True
