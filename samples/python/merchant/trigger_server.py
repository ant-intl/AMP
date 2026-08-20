"""Merchant service entry point for external integration.

Usage:
    python trigger_server.py
    python trigger_server.py 8081
    python trigger_server.py --help

Starts the Merchant HTTP service (FastAPI + Uvicorn) with product catalog,
checkout, and payment processing via acquirer.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

# Ensure project paths are available for imports.
# Remove the script's own directory from sys.path first — Python auto-adds it,
# which shadows the 'merchant' package under samples/python/merchant/.
_script_dir = str(pathlib.Path(__file__).resolve().parent)
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
for p in (_src_python, _samples_python):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the Merchant service (product catalog + checkout + payment).",
    )
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=int(os.environ.get("MERCHANT_PORT", "8081")),
        help="Port number to listen on (default: MERCHANT_PORT env or 8081)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--acquirer-url",
        default=None,
        help="Acquirer service base URL (default: from ACQUIRER_URL env or http://localhost:8085)",
    )

    args = parser.parse_args()

    # Override acquirer URL if provided via CLI
    if args.acquirer_url:
        os.environ["ACQUIRER_URL"] = args.acquirer_url

    # Import the merchant server FastAPI app
    from merchant.server import app

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("merchant")
    logger.info("merchant service started on http://%s:%d", args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
