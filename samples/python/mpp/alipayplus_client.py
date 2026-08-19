"""AlipayPlus HTTP client for MPP outbound calls."""

from __future__ import annotations

import logging
from typing import Any

from common.http_client import http_post

logger = logging.getLogger(__name__)


class AlipayPlusClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def notify_idv_result(self, payload: dict[str, Any]) -> None:
        """POST /network/notifyAuthorization. Failures are non-fatal."""
        try:
            resp = http_post(
                f"{self._base_url}/network/notifyAuthorization",
                json=payload,
                timeout=5.0,
                logger_name="mpp.http-client",
            )
            logger.info(
                "[MPP] → AP notify: session=%s, http=%s",
                payload.get("sessionId"),
                resp.status_code,
            )
        except Exception as exc:
            logger.warning("[MPP] notify AP failed (non-fatal): %s", exc)
