"""Action handler registry. Maps step.type → handler.handle()."""

from . import extract, http, output, parse

HANDLERS = {
    "http_request": http.handle,
    "extract_html": extract.handle,
    "parse_table": parse.handle,
    "save_csv": output.handle,
}

__all__ = ["HANDLERS"]
