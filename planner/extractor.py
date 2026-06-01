"""
planner/extractor.py

GET 網頁 → 抽取關鍵結構 → site_summary dict
目的：精簡 HTML，減少 Gemini token 消耗，提高輸出穩定性
"""
from __future__ import annotations
import requests
from bs4 import BeautifulSoup


def fetch_and_extract(url: str, session: requests.Session | None = None) -> dict:
    """
    GET url → 回傳 site_summary dict

    site_summary 結構：
    {
      "url": str,
      "forms": [...],
      "tables": [...],
      "csrf_patterns": [...],
    }
    """
    sess = session or requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; crawler-agent/1.0)"
    })
    resp = sess.get(url, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    return {
        "url": url,
        "forms": _extract_forms(soup),
        "tables": _extract_tables(soup),
        "csrf_patterns": _detect_csrf(soup),
    }


def _extract_forms(soup: BeautifulSoup) -> list[dict]:
    forms = []
    for form in soup.find_all("form"):
        action = form.get("action", "")
        method = form.get("method", "get").upper()

        fields = []
        for inp in form.find_all("input"):
            fields.append({
                "name":  inp.get("name", ""),
                "type":  inp.get("type", "text"),
                "value": inp.get("value", ""),
            })
        for sel in form.find_all("select"):
            options = [o.get("value", o.text.strip()) for o in sel.find_all("option")]
            fields.append({
                "name":    sel.get("name", ""),
                "type":    "select",
                "options": options[:10],
            })

        if fields:
            forms.append({
                "action": action,
                "method": method,
                "fields": fields,
            })
    return forms


def _extract_tables(soup: BeautifulSoup) -> list[dict]:
    tables = []
    for i, tbl in enumerate(soup.find_all("table")):
        selector = f"table.{'.'.join(tbl.get('class', []))}" if tbl.get("class") else f"table:nth-of-type({i+1})"

        headers = []
        header_row = tbl.find("tr")
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all(["th", "td"])]

        rows = tbl.find_all("tr")
        sample_row = []
        if len(rows) > 1:
            sample_row = [td.text.strip() for td in rows[1].find_all("td")]

        tables.append({
            "selector": selector,
            "classes": " ".join(tbl.get("class", [])),
            "headers": headers[:10],
            "sample_row": sample_row[:10],
            "row_count_approx": len(rows),
        })
    return tables


def _detect_csrf(soup: BeautifulSoup) -> list[dict]:
    patterns = []

    for inp in soup.find_all("input", type="hidden"):
        name = inp.get("name", "").lower()
        if any(kw in name for kw in ["token", "csrf", "sync", "_token"]):
            patterns.append({
                "type": "hidden_input",
                "name": inp.get("name"),
                "selector": f"input[name={inp.get('name')}]",
                "has_value": bool(inp.get("value")),
            })

    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower()
        if "csrf" in name or "token" in name:
            patterns.append({
                "type": "meta",
                "name": meta.get("name"),
                "selector": f"meta[name={meta.get('name')}]",
            })

    return patterns
