"""
extract_links action handler

從 HTML 抽取一個 list of values（例如 fileName list）。
支援 source=form：找所有符合 selector 的 form，抽取 field 的 attr。
"""
from __future__ import annotations
import time
from bs4 import BeautifulSoup


def handle(step: dict, state: dict, runtime) -> dict:
    start = time.time()

    html = runtime._resolve(step["from"], state)
    source   = step["source"]
    selector = step["selector"]
    field    = step.get("field")
    attr     = step.get("attr", "value")
    item_key = step["item_key"]

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

    duration = (time.time() - start) * 1000

    if not items:
        return {
            "status": "failed",
            "outputs": {},
            "meta": {},
            "metrics": {"duration_ms": duration},
            "error": {
                "code": "EXTRACT_LINKS_EMPTY",
                "message": f"no items found with selector='{selector}' field='{field}' attr='{attr}'",
                "retryable": False,
                "details": {"source": source},
            },
        }

    return {
        "status": "success",
        "outputs": {"items": items},
        "meta": {"item_count": len(items), "item_key": item_key},
        "metrics": {"duration_ms": duration},
        "error": None,
    }
