from . import csrf_token, html_table

TRANSFORMS = {
    "csrf_token": csrf_token,
    "html_table": html_table,
}

__all__ = ["TRANSFORMS"]
