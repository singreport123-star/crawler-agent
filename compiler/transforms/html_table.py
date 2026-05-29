"""
html_table capability transform

context.json capabilities.response = ["html_table"]
→ 注入 parse_result + save_output steps
"""
from __future__ import annotations


def apply(context: dict, post_step_id: str = "post_query") -> list[dict]:
    """
    回傳 parse_result + save_output steps。
    post_step_id: 產出 html 的上一個 step id
    """
    parser = context["response"]["parser"]
    post_process = context["response"].get("post_process", {})
    site_short = context["site"].replace(".", "_").replace("/", "_")

    steps = []

    # add_columns 順序對齊手寫版：date 先，stock 後
    add_columns = {}
    input_items = list(context["inputs"].items())
    # 先找 date 類型，再找其他
    date_inputs = [(k, v) for k, v in input_items if k == "date"]
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

    steps.append(parse_step)

    # Step: save_output
    # 檔名用 inputs 順序：第一個 input 為主 key，第二個為 date
    input_keys = list(context["inputs"].keys())
    path_parts = "_".join(f"{{{{input.{k}}}}}" for k in input_keys)
    filename = f"data/集保_{path_parts}.csv"

    steps.append({
        "id": "save_output",
        "type": "save_csv",
        "consumes": ["steps.parse_result.outputs.rows"],
        "produces": [],
        "from": "{{steps.parse_result.outputs.rows}}",
        "path": filename,
        "encoding": "utf-8-sig",
    })

    return steps


def _input_label(input_name: str) -> str:
    """input name → 中文欄位標籤（對應 execution_plan 裡的 add_columns）"""
    mapping = {
        "date":  "日期",
        "stock": "股票代號",
    }
    return mapping.get(input_name, input_name)
