"""http_request action handler — requests + persistent session."""

from __future__ import annotations

import time
from typing import Any, Dict

import requests

from ..schemas import StepError, StepResult, StepMetrics

# session registry keyed by the step's "session" field
_SESSIONS: Dict[str, requests.Session] = {}

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _get_session(name: str) -> requests.Session:
    if name not in _SESSIONS:
        s = requests.Session()
        s.headers.update(_DEFAULT_HEADERS)
        _SESSIONS[name] = s
    return _SESSIONS[name]


def handle(step: Dict[str, Any], resolved: Dict[str, Any]) -> StepResult:
    """Execute an http_request step.

    `step`     : raw step dict from execution_plan (immutable)
    `resolved` : step dict whose {{...}} placeholders are already interpolated
    """
    start = time.perf_counter()
    session_name = step.get("session", "default")
    session = _get_session(session_name)

    request = resolved["request"]
    method = request.get("method", "GET").upper()
    url = request["url"]
    payload = request.get("payload")

    try:
        if method == "GET":
            resp = session.get(url, params=payload, timeout=30)
        elif method == "POST":
            resp = session.post(url, data=payload, timeout=30)
        else:
            raise StepError(
                code="UNSUPPORTED_METHOD",
                message=f"HTTP method not supported: {method}",
                retryable=False,
                details={"method": method},
            )
        resp.raise_for_status()
    except StepError:
        raise
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        raise StepError(
            code="HTTP_ERROR",
            message=f"HTTP {status} from {url}",
            retryable=status is None or status >= 500,
            details={"status": status, "url": url},
        )
    except requests.RequestException as e:
        raise StepError(
            code="NETWORK_ERROR",
            message=str(e),
            retryable=True,
            details={"url": url},
        )

    resp.encoding = resp.apparent_encoding or resp.encoding
    duration = int((time.perf_counter() - start) * 1000)

    return StepResult(
        status="success",
        outputs={"html": resp.text},
        meta={"status_code": resp.status_code, "final_url": resp.url},
        metrics=StepMetrics(duration_ms=duration),
    )
