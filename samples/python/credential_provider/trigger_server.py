"""Credential Provider service entry point.

Bundles the real MPP service (mpp/app.py) in-process via sub-app mount.
ATS (network.py) runs as a separate process and is called via HTTP.

Usage:
    python trigger_server.py [port]
    python trigger_server.py 8082
"""

import logging
import os
import pathlib
import sys

# Ensure project paths are available for imports
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
_this_dir = str(pathlib.Path(__file__).resolve().parent)
for p in (_src_python, _samples_python, _this_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


def _build_app():
    """Build the FastAPI application.

    Reuses the CP app factory (app.build_app) for all CP endpoints, then
    mounts MPP as a sub-app so network.py can reach it via HTTP.
    ATS (network) runs as a separate process and is called via HTTP.
    """
    from app import build_app
    from mpp.app import app as mpp_app

    app = build_app()

    # Mount MPP sub-app so network.py can reach it via HTTP
    app.mount("/mpp", mpp_app)

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Start the Credential Provider service (bundled with MPP).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=int(os.environ.get("CREDENTIALS_PROVIDER_PORT", "8082")),
        help="Port number to listen on (default: from CREDENTIALS_PROVIDER_PORT or 8082)",
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

    logger = setup_logging("credential-provider")
    logger.info("credential-provider service started on http://%s:%d", args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
