"""
extract_then_fetch capability transform

flow: ["extract_then_fetch"]
→ 注入 extract_links step + foreach step
"""
from __future__ import annotations


def apply(context: dict, list_step_id: str = "post_query") -> list[dict]:
    el       = context["extract_links"]
    dr       = context["detail_request"]
    parser   = context["response"]["parser"]
    post_process = context["response"].get("post_process", {})
    site_short   = context["site"].replace(".", "_").replace("/", "_")
    item_key     = el["item_key"]

    steps = []

    # Step: extract_links
    steps.append({
        "id": "extract_links",
        "type": "extract_links",
        "consumes": [f"steps.{list_step_id}.outputs.html"],
        "produces": ["steps.extract_links.outputs.items"],
        "from": f"{{{{steps.{list_step_id}.outputs.html}}}}",
        "item_key": item_key,
        "source": el["source"],
        "selector": el["selector"],
        "field": el.get("field"),
        "attr": el.get("attr", "value"),
    })

    # detail POST payload
    detail_payload = {}
    for pf in dr.get("payload", []):
        field = pf["field"]
        val   = pf["value"]
        if val["type"] == "constant":
            detail_payload[field] = val["value"]
        elif val["type"] == "loop":
            detail_payload[field] = f"{{{{loop.{val['key']}}}}}"

    # add_columns
    add_columns = {}
    for input_name in context["inputs"]:
        label = _input_label(input_name)
        add_columns[label] = f"{{{{input.{input_name}}}}}"
    add_columns["檔案名稱"] = f"{{{{loop.{item_key}}}}}"

    # parse_detail step
    parse_step: dict = {
        "id": "parse_detail",
        "type": "parse_table",
        "consumes": ["steps.post_detail.outputs.html"],
        "produces": ["steps.parse_detail.outputs.rows"],
        "from": "{{steps.post_detail.outputs.html}}",
        "selectors": {
            "table": {"type": "css", "query": parser["selector"]}
        },
        "column_mode": parser.get("column_mode", "index"),
        "add_columns": add_columns,
    }
    if post_process.get("skip_row_keyword"):
        parse_step["skip_row_keyword"] = post_process["skip_row_keyword"]

    # save path per item
    input_keys = list(context["inputs"].keys())
    path_parts = "_".join(f"{{{{input.{k}}}}}" for k in input_keys)
    filename   = f"data/{site_short}_{path_parts}_{{{{loop.{item_key}}}}}.csv"

    # foreach step
    steps.append({
        "id": "foreach_detail",
        "type": "foreach",
        "consumes": ["steps.extract_links.outputs.items"],
        "produces": ["steps.foreach_detail.outputs.all_rows"],
        "iterate_over": "{{steps.extract_links.outputs.items}}",
        "item_key": item_key,
        "steps": [
            {
                "id": "post_detail",
                "type": "http_request",
                "session": "default",
                "consumes": [],
                "produces": ["steps.post_detail.outputs.html"],
                "request": {
                    "method": dr["method"],
                    "url": dr["url"],
                    "payload": detail_payload,
                },
            },
            parse_step,
            {
                "id": "save_detail",
                "type": "save_csv",
                "consumes": ["steps.parse_detail.outputs.rows"],
                "produces": [],
                "from": "{{steps.parse_detail.outputs.rows}}",
                "path": filename,
                "encoding": "utf-8-sig",
            },
        ],
    })

    return steps


def _input_label(input_name: str) -> str:
    mapping = {
        "date":        "日期",
        "stock":       "股票代號",
        "issuer_code": "發行公司代號",
    }
    return mapping.get(input_name, input_name)
