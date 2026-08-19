"""HTTP request/response logging middleware for FastAPI services.

Logs every HTTP call with method, path, request body (truncated) and
response status + body (truncated), plus elapsed time.

Streaming responses (SSE) are logged at entry only — the response body
is passed through without buffering to preserve streaming behaviour.

Usage:
    from common.middleware import HttpLoggingMiddleware

    app = FastAPI()
    app.add_middleware(HttpLoggingMiddleware)

Customisation:
    app.add_middleware(
        HttpLoggingMiddleware,
        max_body=4000,                       # truncate body longer than this (default 100_000)
        skip_paths={"/health", "/docs"},      # suppress logging for these paths
        logger_name="my-service.http",        # logger name
    )
"""

from __future__ import annotations

import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

# Default paths that produce too much noise to log
_DEFAULT_SKIP_PATHS: frozenset[str] = frozenset({
    "/health", "/docs", "/openapi.json", "/redoc",
})


class HttpLoggingMiddleware(BaseHTTPMiddleware):
    """Starlette / FastAPI middleware that logs HTTP request and response."""

    def __init__(
            self,
            app: Any,
            *,
            max_body: int = 100_000,
            skip_paths: set[str] | frozenset[str] | None = None,
            logger_name: str = "http",
    ) -> None:
        super().__init__(app)
        self._max_body = max_body
        self._skip_paths = skip_paths if skip_paths is not None else _DEFAULT_SKIP_PATHS
        self._logger = logging.getLogger(logger_name)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        path = request.url.path

        # Skip noisy health / docs endpoints
        if path in self._skip_paths:
            return await call_next(request)

        # Read request body (must be cached so downstream can read again)
        body_bytes = await request.body()
        body_text = self._truncate(body_bytes.decode("utf-8", errors="replace"))

        self._logger.debug(
            ">>> %s %s  body=%s", method, path, body_text or "(empty)"
        )

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Detect SSE — BaseHTTPMiddleware wraps StreamingResponse into a regular
        # Response, so isinstance alone is insufficient; also check content-type.
        content_type = (response.headers.get("content-type") or "").lower()
        is_sse = "text/event-stream" in content_type

        # True StreamingResponse (not consumed by BaseHTTPMiddleware) — pass through
        if isinstance(response, StreamingResponse):
            self._logger.debug(
                "<<< %s %s  status=%s  %.1fms  body=(streaming)",
                method, path, response.status_code, elapsed_ms,
            )
            return response

        # Read response body for logging
        resp_body = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                resp_body += chunk.encode("utf-8")
            else:
                resp_body += chunk

        # SSE body is multi-line and noisy; suppress full content
        if is_sse:
            resp_text = "(streaming)"
        else:
            resp_text = self._truncate(resp_body.decode("utf-8", errors="replace"))
        self._logger.debug(
            "<<< %s %s  status=%s  %.1fms  body=%s",
            method, path, response.status_code, elapsed_ms,
            resp_text or "(empty)",
            )

        # Rebuild response so the client can still read it
        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    def _truncate(self, text: str) -> str:
        """Truncate body text to max_body chars."""
        text = text.strip()
        if len(text) > self._max_body:
            return text[: self._max_body] + f"... (+{len(text) - self._max_body} chars)"
        return text
