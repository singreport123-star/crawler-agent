"""parse_table action handler — BeautifulSoup HTML table → rows."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from ..schemas import StepError, StepResult, StepMetrics


def _cell_text(cell) -> str:
    return cell.get_text(strip=True)


def handle(step: Dict[str, Any], resolved: Dict[str, Any]) -> StepResult:
    start = time.perf_counter()
    html = resolved["from"]
    soup = BeautifulSoup(html, "html.parser")

    table_spec = step.get("selectors", {}).get("table", {})
    query = table_spec.get("query", "table")
    table = soup.select_one(query)
    if table is None:
        raise StepError(
            code="SELECTOR_NOT_FOUND",
            message=f"table not found: {query}",
            retryable=True,
            details={"query": query},
        )

    column_mode = step.get("column_mode", "index")
    skip_keyword = step.get("skip_row_keyword")
    # add_columns already interpolated in `resolved`
    add_columns: Dict[str, str] = resolved.get("add_columns", {})

    trs = table.find_all("tr")
    if not trs:
        raise StepError(
            code="EMPTY_TABLE",
            message="table has no rows",
            retryable=True,
            details={"query": query},
        )

    # header detection
    header_cells = trs[0].find_all(["th", "td"])
    if column_mode == "header":
        headers = [_cell_text(c) for c in header_cells]
        body_trs = trs[1:]
    else:  # index mode
        headers = [str(i) for i in range(len(header_cells))]
        # if first row is <th>, treat as header and skip; else include it
        body_trs = trs[1:] if trs[0].find("th") else trs

    rows: List[Dict[str, Any]] = []
    for tr in body_trs:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        values = [_cell_text(c) for c in cells]
        joined = "".join(values)
        if skip_keyword and skip_keyword in joined:
            continue

        row: Dict[str, Any] = {}
        for i, val in enumerate(values):
            col = headers[i] if i < len(headers) else str(i)
            row[col] = val
        for col, val in add_columns.items():
            row[col] = val
        rows.append(row)

    duration = int((time.perf_counter() - start) * 1000)
    return StepResult(
        status="success",
        outputs={"rows": rows},
        meta={"row_count": len(rows), "column_mode": column_mode},
        metrics=StepMetrics(duration_ms=duration),
    )
