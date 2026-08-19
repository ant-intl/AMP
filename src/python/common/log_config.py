"""Unified logging configuration for AMP services.

Provides consistent log formatting across all modules:
- Python stdlib logging: ``setup_logging(name)`` for application-level loggers
- Uvicorn access/default logs: ``uvicorn_log_config()`` for HTTP server output

Log format: ``%(asctime)s [%(levelname)s] %(name)s - %(message)s``
Uvicorn access: ``%(asctime)s %(client_addr)s - "%(request_line)s" %(status_code)s``

Usage:
    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("my-service")
    uvicorn.run(app, log_config=uvicorn_log_config())
"""

from __future__ import annotations

import copy
import logging
import sys
import warnings

# Suppress upstream deprecation warnings that add noise to service output
warnings.filterwarnings(
    "ignore",
    message=r".*httpx.*starlette\.testclient.*",
    category=DeprecationWarning,
)

# Silence noisy third-party loggers (our http_client provides structured output)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Unified log format for all AMP services.
# Note: service identity is provided by start.sh's [service-name] tail prefix,
# so %(name)s is omitted to avoid redundancy in terminal output.
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATEFMT = "%H:%M:%S"

# Uvicorn-specific formats
_UVICORN_ACCESS_FMT = '%(asctime)s %(client_addr)s - "%(request_line)s" %(status_code)s'
_UVICORN_DEFAULT_FMT = "%(asctime)s [%(levelname)s] %(message)s"


_UVICORN_LOGGER_RENAME = {
    "uvicorn.error": "uvicorn.server",
    "uvicorn.access": "uvicorn.server.http",
}


class _UvicornLoggerRenameFilter(logging.Filter):
    """Rename uvicorn logger names in log output for clarity."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.name = _UVICORN_LOGGER_RENAME.get(record.name, record.name)
        return True


def setup_logging(
        name: str,
        level: int = logging.INFO,
        stream: bool = True,
        log_file: str | None = None,
) -> logging.Logger:
    """Configure root logging and return a named logger.

    Safe to call multiple times — only configures handlers on first call.

    Args:
        name: Logger name (typically the module or service name).
        level: Logging level (default: INFO).
        stream: Whether to add a StreamHandler for stdout.
        log_file: Optional file path for a FileHandler.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

        if stream:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            root.addHandler(sh)

        if log_file:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            root.addHandler(fh)

    return logging.getLogger(name)


def uvicorn_log_config() -> dict:
    """Return a uvicorn-compatible log config dict with timestamped formatters.

    Pass to ``uvicorn.run(..., log_config=...)`` so that both the access log
    and the default server log include timestamps.

    Also ensures application loggers (e.g. from ``http_client`` or ``middleware``)
    propagate correctly to stdout by:
      - Attaching a StreamHandler to the uvicorn "default" logger
      - Setting root logger to INFO with propagate enabled
    """
    import uvicorn.config

    cfg = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)
    cfg["formatters"]["access"]["fmt"] = _UVICORN_ACCESS_FMT
    cfg["formatters"]["default"]["fmt"] = _UVICORN_DEFAULT_FMT
    cfg["formatters"]["default"]["datefmt"] = LOG_DATEFMT
    cfg["formatters"]["access"]["datefmt"] = LOG_DATEFMT

    # Apply logger rename filter to uvicorn loggers
    _rename_filter = _UvicornLoggerRenameFilter()
    for logger_name in ("uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).addFilter(_rename_filter)

    # Suppress uvicorn lifecycle/access noise (our http_client covers communication logs)
    cfg.setdefault("loggers", {})
    cfg["loggers"]["uvicorn.error"] = {"level": "WARNING", "propagate": True}
    cfg["loggers"]["uvicorn.access"] = {"level": "WARNING", "propagate": True}
    cfg["loggers"]["httpx"] = {"level": "WARNING", "propagate": True}

    # Ensure application loggers propagate to uvicorn's handlers
    cfg.setdefault("root", {})["level"] = "INFO"
    cfg["root"]["handlers"] = ["default"]

    return cfg
