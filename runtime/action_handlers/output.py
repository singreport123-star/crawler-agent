"""save_csv action handler — writes rows to CSV via stdlib csv."""

from __future__ import annotations

import csv
import os
import time
from typing import Any, Dict, List

from ..schemas import StepError, StepResult, StepMetrics


def handle(step: Dict[str, Any], resolved: Dict[str, Any]) -> StepResult:
    start = time.perf_counter()
    rows: List[Dict[str, Any]] = resolved["from"]
    path = resolved["path"]
    encoding = step.get("encoding", "utf-8-sig")

    if not isinstance(rows, list):
        raise StepError(
            code="INVALID_INPUT",
            message="save_csv expects a list of rows",
            retryable=False,
            details={"type": type(rows).__name__},
        )

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if not rows:
        # still create an empty file so the contract (a CSV exists) holds
        open(path, "w", encoding=encoding).close()
        duration = int((time.perf_counter() - start) * 1000)
        return StepResult(
            status="success",
            outputs={},
            meta={"path": path, "row_count": 0},
            metrics=StepMetrics(duration_ms=duration),
        )

    # union of keys preserving first-seen order
    fieldnames: List[str] = []
    for row in rows:
        for k in row.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    try:
        with open(path, "w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except OSError as e:
        raise StepError(
            code="IO_ERROR",
            message=str(e),
            retryable=False,
            details={"path": path},
        )

    duration = int((time.perf_counter() - start) * 1000)
    return StepResult(
        status="success",
        outputs={},
        meta={"path": path, "row_count": len(rows)},
        metrics=StepMetrics(duration_ms=duration),
    )
