"""
html_table capability transform

context.json capabilities.response = ["html_table"]
→ 注入 parse_result + save_output steps
"""
from __future__ import annotations


def apply(context: dict, post_step_id: str = "post_query") -> list[dict]:
    parser = context["response"]["parser"]
    post_process = context["response"].get("post_process", {})
    site_short = context["site"].replace(".", "_").replace("/", "_")

    # add_columns：date 先，其他後
    add_columns = {}
    input_items = list(context["inputs"].items())
    date_inputs  = [(k, v) for k, v in input_items if k == "date"]
    other_inputs = [(k, v) for k, v in input_items if k != "date"]
    for input_name, _ in date_inputs + other_inputs:
        label = _input_label(input_name)
        add_columns[label] = f"{{{{input.{input_name}}}}}"

    # Step: parse_result
    parse_step: dict = {
        "id": "parse_result",
        "type": "parse_table",
        "consumes": [f"steps.{post_step_id}.outputs.html"],
        "produces": ["steps.parse_result.outputs.rows"],
        "from": f"{{{{steps.{post_step_id}.outputs.html}}}}",
        "selectors": {
            "table": {
                "type": "css",
                "query": parser["selector"],
            }
        },
        "column_mode": parser.get("column_mode", "index"),
        "add_columns": add_columns,
    }
    if post_process.get("skip_row_keyword"):
        parse_step["skip_row_keyword"] = post_process["skip_row_keyword"]

    # Step: save_output — 檔名用所有 input 的值
    input_keys = list(context["inputs"].keys())
    path_parts = "_".join(f"{{{{input.{k}}}}}" for k in input_keys)
    filename = f"data/{site_short}_{path_parts}.csv"

    steps = [parse_step, {
        "id": "save_output",
        "type": "save_csv",
        "consumes": ["steps.parse_result.outputs.rows"],
        "produces": [],
        "from": "{{steps.parse_result.outputs.rows}}",
        "path": filename,
        "encoding": "utf-8-sig",
    }]

    return steps


def _input_label(input_name: str) -> str:
    mapping = {
        "date":      "日期",
        "stock":     "股票代號",
        "file_name": "檔案名稱",
    }
    return mapping.get(input_name, input_name)
