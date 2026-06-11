from .http import handle as http_handle
from .extract import handle as extract_handle
from .parse import handle as parse_handle
from .output import handle as output_handle
from .foreach import handle as foreach_handle
from .extract_links import handle as extract_links_handle

HANDLERS = {
    "http_request":  http_handle,
    "extract_html":  extract_handle,
    "parse_table":   parse_handle,
    "save_csv":      output_handle,
    "foreach":       foreach_handle,
    "extract_links": extract_links_handle,
}
