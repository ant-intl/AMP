"""AlipayPlus service entry point for external integration.

Usage:
    python trigger_server.py <service_name> <port>
    python trigger_server.py mandate 8084
    python trigger_server.py --help

Supported services:
    - mandate : AlipayPlus Mandate & Verifiable Intent API
    - network : AlipayPlus Network service (placeholder)
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import sys

# Ensure project paths are available for imports
_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
for p in (_src_python, _samples_python):
    if p not in sys.path:
        sys.path.insert(0, p)

# Service registry: name -> module path (relative to this directory)
_SERVICES = {
    "mandate": "alipayplus.mandate",
    "network": "alipayplus.network",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start an AlipayPlus service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "service",
        choices=sorted(_SERVICES.keys()),
        help="Service name to start",
    )
    parser.add_argument(
        "port",
        type=int,
        help="Port number to listen on",
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

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging(f"alipayplus.{args.service}")

    # Import the target module and get its FastAPI ``app``
    module_path = _SERVICES[args.service]
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        logger.error("Cannot import service '%s': %s", args.service, exc)
        sys.exit(1)

    app = getattr(mod, "app", None)
    if app is None:
        logger.error("Module '%s' has no 'app' attribute", module_path)
        sys.exit(1)
    logger.info("alipayplus-%s service started on http://%s:%d", args.service, args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
