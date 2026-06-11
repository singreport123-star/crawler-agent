from . import csrf_token, html_table, no_auth, extract_then_fetch

TRANSFORMS = {
    "csrf_token":        csrf_token,
    "html_table":        html_table,
    "no_auth":           no_auth,
    "extract_then_fetch": extract_then_fetch,
}

__all__ = ["TRANSFORMS"]
