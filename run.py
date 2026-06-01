#!/usr/bin/env python3
"""Entry point — 支援 TDCC 和 MOPS（及未來任何 plan）

用法：
  # TDCC（預設）
  python run.py --stock 2330 --date 20260522

  # MOPS
  python run.py --plan plans/mops_execution_plan_compiled.json \
                --file_name 000930_1150422_114156.pdf
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict

from runtime import Runtime

ROOT       = os.path.dirname(os.path.abspath(__file__))
PLAN_PATH  = os.path.join(ROOT, "plans", "tdcc_execution_plan.json")
CONFIG_PATH = os.path.join(ROOT, "config.json")
STATE_PATH  = os.path.join(ROOT, "logs", "runtime_state.json")


def compute_plan_hash(plan: Dict[str, Any]) -> str:
    clone = {k: v for k, v in plan.items() if k != "plan_hash"}
    blob = json.dumps(clone, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_inputs(plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """
    plan.inputs 的 key 對應 CLI args。
    例如 plan.inputs = {"stock": ..., "date": ...}
    → inputs = {"stock": args.stock, "date": args.date}
    """
    inputs: Dict[str, Any] = {}
    for name in plan.get("inputs", {}):
        val = getattr(args, name, None)
        if val is None:
            print(f"[run] missing required input: --{name}", file=sys.stderr)
            sys.exit(2)
        inputs[name] = val
    return inputs


def main() -> int:
    # 先 parse --plan，再動態加其他 args
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--plan", default=PLAN_PATH)
    pre_args, _ = pre.parse_known_args()

    plan_path = pre_args.plan
    plan    = load_json(plan_path)
    config  = load_json(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else {}

    # 正式 parser：根據 plan.inputs 動態加 CLI args
    parser = argparse.ArgumentParser(description="Crawler Agent")
    parser.add_argument("--plan", default=PLAN_PATH, help="execution plan path")
    for name, spec in plan.get("inputs", {}).items():
        cli_flag = spec.get("cli", f"--{name}")
        parser.add_argument(cli_flag, dest=name, required=False,
                            help=f"input: {name}")
    args = parser.parse_args()

    # plan_hash 驗證
    expected = compute_plan_hash(plan)
    if plan.get("plan_hash") in (None, "", "待實作時計算"):
        plan["plan_hash"] = expected
    elif plan["plan_hash"] != expected:
        print(f"[plan_hash mismatch] expected={expected} got={plan['plan_hash']}",
              file=sys.stderr)
        return 2
    print(f"plan_hash = {plan['plan_hash']}")

    inputs = build_inputs(plan, args)

    rt = Runtime(plan=plan, inputs=inputs, config=config, state_path=STATE_PATH)
    ok = rt.run()

    if ok:
        save_step = rt.state["steps"].get("save_output", {})
        path = save_step.get("meta", {}).get("path", "?")
        rows = save_step.get("meta", {}).get("row_count", "?")
        print(f"OK — wrote {rows} rows to {path}")
        return 0

    err = rt.state.get("error") or {}
    print(f"FAILED at step '{rt.state.get('failed_step')}' "
          f"[{err.get('code')}] {err.get('message')}", file=sys.stderr)
    print(f"see {STATE_PATH} for full runtime state", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
