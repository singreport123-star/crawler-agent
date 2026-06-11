"""
extract_links action handler

從 HTML 抽取一個 list of values（例如 fileName list）。
支援 source=form：找所有符合 selector 的 form，抽取 field 的 attr。
"""
from __future__ import annotations
import time
from bs4 import BeautifulSoup

from ..schemas import StepError, StepResult, StepMetrics


def handle(step: dict, resolved: dict) -> StepResult:
    start = time.perf_counter()

    # 直接使用 runtime 已經幫忙解析好變數的 resolved 字典
    html = resolved["from"]
    source   = resolved["source"]
    selector = resolved["selector"]
    field    = resolved.get("field")
    attr     = resolved.get("attr", "value")
    item_key = resolved["item_key"]

    soup = BeautifulSoup(html, "html.parser")
    items = []

    if source == "form":
        for form in soup.select(selector):
            if field:
                inp = form.select_one(field)
                if inp and inp.get(attr):
                    items.append(inp.get(attr))
            else:
                val = form.get(attr)
                if val:
                    items.append(val)

    elif source == "anchor":
        for a in soup.select(selector):
            val = a.get(attr) or a.text.strip()
            if val:
                items.append(val)

    elif source == "attribute":
        for el in soup.select(selector):
            val = el.get(attr)
            if val:
                items.append(val)

    duration = int((time.perf_counter() - start) * 1000)

    if not items:
        # 改用拋出 StepError，符合新版 runtime.py 的錯誤處理機制
        raise StepError(
            code="EXTRACT_LINKS_EMPTY",
            message=f"no items found with selector='{selector}' field='{field}' attr='{attr}'",
            retryable=False,
            details={"source": source},
        )

    # 回傳 StepResult 物件
    return StepResult(
        status="success",
        outputs={"items": items},
        meta={"item_count": len(items), "item_key": item_key},
        metrics=StepMetrics(duration_ms=duration)
    )
