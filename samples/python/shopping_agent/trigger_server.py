"""Shopping Agent service entry point for external integration.

Exposes HTTP endpoints to trigger the Shopping Agent flow and check its status.
The agent calls Credential Provider and Merchant services over HTTP.

Usage:
    python trigger_server.py [port]
    python trigger_server.py 8080
"""
from __future__ import annotations

import os
import pathlib
import sys
from datetime import datetime, timezone

# Ensure project paths are available for imports
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
_this_dir = str(pathlib.Path(__file__).resolve().parent)
for p in (_src_python, _samples_python, _this_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from common.log_config import setup_logging

logger = setup_logging("shopping-agent")


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------
_agent_state: dict = {
    "status": "idle",  # idle / running / completed / failed
    "started_at": None,
    "completed_at": None,
    "error": None,
    "step_count": 0,
}


def _build_app():
    """Build the FastAPI application for the Shopping Agent."""
    from fastapi import FastAPI

    app = FastAPI(
        title="Shopping Agent Service",
        description="Agentic Mandate Protocol Shopping Agent.",
        version="1.0.0",
    )

    from common.middleware import HttpLoggingMiddleware
    app.add_middleware(HttpLoggingMiddleware, logger_name="shopping-agent.http")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "shopping-agent", "agent": _agent_state}

    @app.post("/run")
    def run_agent() -> dict:
        """Trigger the Shopping Agent to execute the full AMP protocol flow."""
        if _agent_state["status"] == "running":
            return {"success": False, "error": "Agent is already running."}

        _agent_state["status"] = "running"
        _agent_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _agent_state["error"] = None

        try:
            from events import EventBus
            from evidence_logger import ExecutionLogger

            # Resolve service URLs from environment or defaults
            cp_port = os.environ.get("CREDENTIALS_PROVIDER_PORT", "8082")
            merchant_port = os.environ.get("MERCHANT_PORT", "8081")
            cp_url = f"http://localhost:{cp_port}"
            merchant_url = f"http://localhost:{merchant_port}"

            log_dir = os.environ.get(
                "LOGS_DIR",
                str(pathlib.Path(__file__).resolve().parent.parent
                    / "scenarios" / "human_not_present" / ".logs"),
            )
            pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)

            event_bus = EventBus()
            exec_logger = ExecutionLogger(log_dir=log_dir)

            from agent import ShoppingAgent

            agent = ShoppingAgent(
                merchant_url=merchant_url + "/merchant",
                cp_url=cp_url,
                event_bus=event_bus,
                logger=exec_logger,
            )
            agent.run(auto=True)

            _agent_state["status"] = "completed"
            _agent_state["step_count"] = agent._runtime.step_count
            _agent_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": True, "steps": agent._runtime.step_count}

        except Exception as exc:
            logger.exception("Agent run failed: %s", exc)
            _agent_state["status"] = "failed"
            _agent_state["error"] = str(exc)
            _agent_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": False, "error": str(exc)}

    @app.get("/status")
    def agent_status() -> dict:
        """Return the current agent execution status."""
        return {"success": True, "data": _agent_state}

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Start the Shopping Agent service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="Port number to listen on (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    app = _build_app()

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("shopping-agent")
    logger.info("shopping-agent service started on http://%s:%d", args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
