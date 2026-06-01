"""
planner/planner.py

site_summary + 目標描述 → Gemini Flash → context.json
"""
from __future__ import annotations
import json
import os
import sys

from google import genai
from google.genai import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from contracts.context_schema import ContextSchema
from planner.extractor import fetch_and_extract

MODEL = "gemini-2.5-flash"  # 或是改為 "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are a web scraping analyst. Given a website summary (forms, tables, CSRF patterns),
output a JSON object describing the site's scraping contract.

RULES:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Follow the schema exactly.
- Do not add fields not in the schema.
- capabilities.auth must be one of: ["csrf_token"] or []
- capabilities.response must be one of: ["html_table"] or []
- request.content_type must be exactly: "application/x-www-form-urlencoded" or "application/json" or "multipart/form-data"
- request.method must be: "GET" or "POST"
- response.parser.type must be: "html_table"
- response.parser.format must be: "html"
- response.data_shape must be: "table_rows"
- source.type must be one of: "selector", "constant", "cookie", "meta"
- inject_to.type must be one of: "form_field", "header"
""".strip()

CONTEXT_SCHEMA_EXAMPLE = """
{
  "schema_version": "1.0",
  "site": "www.example.com",
  "entry_url": "https://www.example.com/query",
  "auth": {
    "type": "csrf_token",
    "token": {
      "source": { "type": "selector", "selector": "input[name=CSRF_TOKEN]" },
      "inject_to": { "type": "form_field", "name": "CSRF_TOKEN" }
    },
    "bindings": [
      {
        "source": { "type": "constant", "value": "/query" },
        "inject_to": { "type": "form_field", "name": "CSRF_URI" }
      }
    ]
  },
  "request": {
    "method": "POST",
    "content_type": "application/x-www-form-urlencoded"
  },
  "inputs": {
    "stock": { "type": "string", "required": true, "field": "stockNo" },
    "date":  { "type": "string", "required": true, "field": "scaDate" }
  },
  "extra_fields": [
    { "field": "method",  "value": { "type": "constant", "value": "submit" } },
    { "field": "firDate", "value": { "type": "selector", "selector": "input[name=firDate]" } }
  ],
  "response": {
    "parser": {
      "type": "html_table",
      "format": "html",
      "selector": "table.result",
      "column_mode": "index"
    },
    "data_shape": "table_rows",
    "post_process": { "skip_row_keyword": "合計" }
  },
  "capabilities": {
    "auth": ["csrf_token"],
    "response": ["html_table"]
  }
}
""".strip()


def build_prompt(site_summary: dict, intent: str) -> str:
    return f"""
Website summary:
{json.dumps(site_summary, ensure_ascii=False, indent=2)}

User intent: {intent}

Output a context.json following this exact schema structure:
{CONTEXT_SCHEMA_EXAMPLE}

Fill in real values from the website summary above.
Output ONLY the JSON object, nothing else.
""".strip()


def call_gemini(prompt: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return response.text


def parse_gemini_output(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


def validate_context(data: dict) -> ContextSchema:
    return ContextSchema(**data)


def run_planner(
    url: str,
    intent: str,
    output_path: str,
    api_key: str | None = None,
) -> dict:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY not set")

    print(f"[planner] fetching {url} ...")
    site_summary = fetch_and_extract(url)
    print(f"[planner] extracted: {len(site_summary['forms'])} forms, "
          f"{len(site_summary['tables'])} tables, "
          f"{len(site_summary['csrf_patterns'])} csrf patterns")

    prompt = build_prompt(site_summary, intent)

    print(f"[planner] calling Gemini ({MODEL}) ...")
    raw = call_gemini(prompt, key)

    print("[planner] parsing output ...")
    data = parse_gemini_output(raw)

    print("[planner] validating schema ...")
    validate_context(data)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[planner] context.json written → {output_path}")
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Planner: URL → context.json")
    parser.add_argument("--url",    required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--output", default="context/generated_context.json")
    args = parser.parse_args()

    run_planner(url=args.url, intent=args.intent, output_path=args.output)
