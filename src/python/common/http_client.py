"""Unified HTTP client with structured communication logging.

Wraps ``httpx`` to provide consistent, readable logging for all outbound
HTTP calls.  Output format (structured layered style):

    [Agent→CP] POST /binding/enroll | 200 | 142ms
      req:  {"wallet_id":"w_001","user_id":"u_demo"}
      resp: {"session_id":"s_abc","status":"PENDING_IDV"}

On error:
    [Agent→CP] POST /binding/enroll | ConnectError | 5002ms
      req:  {"wallet_id":"w_001"}
      resp: ConnectError: connection refused

Usage:
    from common.http_client import http_post, http_get

    resp = http_post("http://localhost:8082/binding/enroll", json=payload)
    resp = http_get("http://localhost:8081/products", logger_name="shopping-agent.http")
"""

from __future__ import annotations

import json as _json_mod
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

_DEFAULT_TIMEOUT: float = 10.0

# Log messages carry the FULL request/response body so the log file is complete.
# Terminal readability is handled by start.sh's tail_service, which truncates
# long lines for display only (the on-disk log keeps full data).
_MAX_BODY_LOG: int = 100000

# ---------------------------------------------------------------------------
# Service name mapping (port → official protocol role name per ARCHITECTURE.md)
# ---------------------------------------------------------------------------
_SERVICE_NAMES: dict[str, str] = {
    "8080": "Shopping Agent",
    "8081": "Merchant",
    "8082": "Credential Provider",
    "8083": "AlipayPlus",
    "8084": "AlipayPlus",
    "8085": "Acquirer",
    "8086": "MPP",
}

# Logger-name prefix → official protocol role name
_CALLER_NAMES: dict[str, str] = {
    "shopping-agent": "Shopping Agent",
    "agent": "Shopping Agent",
    "credential-provider": "Credential Provider",
    "cp": "Credential Provider",
    "merchant": "Merchant",
    "acquirer": "Acquirer",
    "mpp": "MPP",
    "alipayplus": "AlipayPlus",
    "network": "AlipayPlus",
}

# Service mount prefixes stripped so the logged path matches the official
# protocol interface name (e.g. /network/createAuthorization -> /createAuthorization).
_ROUTE_PREFIXES = ("/network", "/mpp", "/ats", "/cp", "/acquirer")


def _service_name_from_url(url: str) -> str:
    """Derive a short service name from the target URL port."""
    try:
        port = urlparse(url).port
        if port and str(port) in _SERVICE_NAMES:
            return _SERVICE_NAMES[str(port)]
    except Exception:
        pass
    # Fallback: host:port
    parsed = urlparse(url)
    return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname or url


def _caller_name(logger_name: str | None) -> str:
    """Derive caller display name from logger name."""
    if not logger_name:
        return "Client"
    for prefix, name in _CALLER_NAMES.items():
        if logger_name.startswith(prefix):
            return name
    # Fallback: first segment before dot
    return logger_name.split(".")[0].title()


def _truncate(text: str, max_len: int | None = None) -> str:
    """Truncate text to max_len chars (respects LOG_VERBOSE)."""
    limit = max_len if max_len is not None else _MAX_BODY_LOG
    text = text.strip()
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _format_body(body: Any) -> str:
    """Format request/response body for logging."""
    if body is None:
        return "(empty)"
    if isinstance(body, (dict, list)):
        try:
            return _truncate(_json_mod.dumps(body, ensure_ascii=False, separators=(",", ":")))
        except (TypeError, ValueError):
            return _truncate(str(body))
    if isinstance(body, str):
        return _truncate(body) or "(empty)"
    if isinstance(body, bytes):
        return _truncate(body.decode("utf-8", errors="replace")) or "(empty)"
    return _truncate(str(body))


def _path_from_url(url: str) -> str:
    """Extract path from URL, stripping service mount prefixes to match protocol interface names."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    # Strip known service route prefixes (e.g. /mpp/pay -> /pay)
    for prefix in _ROUTE_PREFIXES:
        if path.startswith(prefix + "/"):
            path = path[len(prefix):]
            break
    if parsed.query:
        path += f"?{parsed.query}"
    return path


def _get_logger(logger_name: str | None) -> logging.Logger:
    return logging.getLogger(logger_name or "http.client")


def _log_comm(
        lg: logging.Logger,
        caller: str,
        callee: str,
        method: str,
        path: str,
        status: str | int,
        elapsed_ms: float,
        req_body: str,
        resp_body: str,
) -> None:
    """Emit a structured 3-line communication log entry."""
    lg.info(
        "[%s→%s] %s %s | %s | %.0fms\n  req:  %s\n  resp: %s",
        caller, callee, method, path, status, elapsed_ms, req_body, resp_body,
    )


def _log_error(
        lg: logging.Logger,
        caller: str,
        callee: str,
        method: str,
        path: str,
        exc: Exception,
        elapsed_ms: float,
        req_body: str,
) -> None:
    """Emit a structured error log entry."""
    lg.error(
        "[%s→%s] %s %s | %s | %.0fms\n  req:  %s\n  resp: %s: %s",
        caller, callee, method, path, type(exc).__name__, elapsed_ms,
        req_body, type(exc).__name__, exc,
    )


def http_post(
        url: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        logger_name: str | None = None,
) -> httpx.Response:
    """Send an HTTP POST request with structured logging.

    Args:
        url: Target URL.
        json: JSON-serialisable body (dict/list).
        data: Form-encoded body (mutually exclusive with json).
        headers: Optional request headers.
        timeout: Request timeout in seconds (default: 10).
        logger_name: Logger name for log output (default: "http.client").

    Returns:
        The ``httpx.Response`` object.

    Raises:
        httpx.HTTPError: On network / timeout errors (logged before re-raise).
    """
    lg = _get_logger(logger_name)
    caller = _caller_name(logger_name)
    callee = _service_name_from_url(url)
    path = _path_from_url(url)
    req_body = _format_body(json if json is not None else data)

    start = time.perf_counter()
    try:
        resp = httpx.post(url, json=json, data=data, headers=headers, timeout=timeout)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log_error(lg, caller, callee, "POST", path, exc, elapsed_ms, req_body)
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    resp_body = _format_body(resp.text)
    _log_comm(lg, caller, callee, "POST", path, resp.status_code, elapsed_ms, req_body, resp_body)
    return resp


def http_get(
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        logger_name: str | None = None,
) -> httpx.Response:
    """Send an HTTP GET request with structured logging.

    Args:
        url: Target URL.
        params: Optional query parameters.
        headers: Optional request headers.
        timeout: Request timeout in seconds (default: 10).
        logger_name: Logger name for log output (default: "http.client").

    Returns:
        The ``httpx.Response`` object.

    Raises:
        httpx.HTTPError: On network / timeout errors (logged before re-raise).
    """
    lg = _get_logger(logger_name)
    caller = _caller_name(logger_name)
    callee = _service_name_from_url(url)
    path = _path_from_url(url)

    start = time.perf_counter()
    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=timeout)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _log_error(lg, caller, callee, "GET", path, exc, elapsed_ms, "(empty)")
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000
    resp_body = _format_body(resp.text)
    _log_comm(lg, caller, callee, "GET", path, resp.status_code, elapsed_ms, "(empty)", resp_body)
    return resp
