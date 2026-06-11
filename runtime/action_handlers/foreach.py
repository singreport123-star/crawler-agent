"""
foreach action handler

iterate_over 裡每個 item 跑 inner steps，結果各自存 CSV。
"""
from __future__ import annotations
import time


def handle(step: dict, state: dict, runtime) -> dict:
    start = time.time()

    items_ref   = step["iterate_over"]
    item_key    = step["item_key"]
    inner_steps = step["steps"]

    items = runtime._resolve(items_ref, state)
    if not isinstance(items, list):
        return {
            "status": "failed",
            "outputs": {},
            "meta": {},
            "metrics": {"duration_ms": (time.time() - start) * 1000},
            "error": {
                "code": "FOREACH_INVALID_INPUT",
                "message": f"iterate_over must resolve to list, got {type(items).__name__}",
                "retryable": False,
                "details": {},
            },
        }

    all_rows = []
    failed_items = []

    for item in items:
        state["loop"] = {item_key: item}

        for inner_step in inner_steps:
            result = runtime._run_step(inner_step, state)
            state["steps"][inner_step["id"]] = result

            if result["status"] == "failed":
                print(f"[foreach] '{inner_step['id']}' failed for {item_key}={item}: "
                      f"{result.get('error', {}).get('message')}")
                failed_items.append(item)
                break

            if inner_step["type"] == "parse_table":
                all_rows.extend(result["outputs"].get("rows", []))

    state.pop("loop", None)

    duration = (time.time() - start) * 1000
    return {
        "status": "success",
        "outputs": {"all_rows": all_rows},
        "meta": {
            "item_count": len(items),
            "row_count": len(all_rows),
            "failed_items": failed_items,
        },
        "metrics": {"duration_ms": duration},
        "error": None,
    }
