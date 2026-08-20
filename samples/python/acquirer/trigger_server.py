"""Acquirer service entry point for external integration.

Usage:
    python trigger_server.py <port>
    python trigger_server.py 8085
    python trigger_server.py --help

Starts the Acquirer HTTP service with CGCP token recognition and A+ network routing.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# Ensure project paths are available for imports.
# Remove the script's own directory from sys.path first — Python auto-adds it,
# which shadows the 'acquirer' package under samples/python/acquirer/.
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
        description="Start the Acquirer service (CGCP token recognition + A+ network routing).",
    )
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=8085,
        help="Port number to listen on (default: 8085)",
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
    parser.add_argument(
        "--aplus-network-url",
        default="http://localhost:8083",
        help="A+ payment network base URL (default: http://localhost:8083)",
    )

    args = parser.parse_args()

    # Import the acquirer module and get its FastAPI ``app``
    from acquirer.acquirer import app
    from acquirer.config import ALIPAYPLUS_NETWORK_BASE_URL

    # Override A+ network URL if provided
    if args.aplus_network_url:
        import acquirer.config as _cfg
        _cfg.ALIPAYPLUS_NETWORK_BASE_URL = args.aplus_network_url

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("acquirer")
    logger.info("acquirer service started on http://%s:%d", args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
