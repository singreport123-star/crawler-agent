"""extract_html action handler — BeautifulSoup selector extraction."""

from __future__ import annotations

import time
from typing import Any, Dict

from bs4 import BeautifulSoup

from ..schemas import StepError, StepResult, StepMetrics


def _select_one(soup: BeautifulSoup, spec: Dict[str, Any], key: str) -> str:
    sel_type = spec.get("type", "css")
    if sel_type != "css":
        raise StepError(
            code="UNSUPPORTED_SELECTOR",
            message=f"selector type not supported: {sel_type}",
            retryable=False,
            details={"selector": key, "type": sel_type},
        )

    el = soup.select_one(spec["query"])
    if el is None:
        raise StepError(
            code="SELECTOR_NOT_FOUND",
            message=f"selector matched nothing: {spec['query']}",
            retryable=True,
            details={"selector": key, "query": spec["query"]},
        )

    attr = spec.get("attr")
    if attr:
        value = el.get(attr)
        if value is None:
            raise StepError(
                code="ATTR_NOT_FOUND",
                message=f"attr '{attr}' missing on element",
                retryable=True,
                details={"selector": key, "attr": attr},
            )
        return value
    return el.get_text(strip=True)


def handle(step: Dict[str, Any], resolved: Dict[str, Any]) -> StepResult:
    start = time.perf_counter()
    html = resolved["from"]
    soup = BeautifulSoup(html, "html.parser")

    outputs: Dict[str, Any] = {}
    for key, spec in step.get("selectors", {}).items():
        outputs[key] = _select_one(soup, spec, key)

    duration = int((time.perf_counter() - start) * 1000)
    return StepResult(
        status="success",
        outputs=outputs,
        meta={"extracted_keys": list(outputs.keys())},
        metrics=StepMetrics(duration_ms=duration),
    )
