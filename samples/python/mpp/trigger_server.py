"""MPP service entry point.

Usage:
    python trigger_server.py [port]
    python trigger_server.py 8899

Default port: 8899, mounted at /mpp to match network.py MPP_BASE_URL.
"""
from __future__ import annotations

import pathlib
import sys

_project_root = pathlib.Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
for _p in (_src_python, _samples_python):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"

    from mpp.app import app
    from fastapi import FastAPI
    import uvicorn

    # Mount under /mpp so all endpoints are at /mpp/* matching network.py MPP_BASE_URL.
    root_app = FastAPI()
    root_app.mount("/mpp", app)

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("mpp")
    logger.info("mpp service started on http://%s:%d (prefix: /mpp)", host, port)

    uvicorn.run(root_app, host=host, port=port, log_level="warning", log_config=uvicorn_log_config())


if __name__ == "__main__":
    main()
