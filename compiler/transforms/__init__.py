from . import csrf_token, html_table

TRANSFORMS = {
    "csrf_token": csrf_token,
    "html_table": html_table,
}

__all__ = ["TRANSFORMS"]

from . import no_auth
TRANSFORMS["no_auth"] = no_auth
