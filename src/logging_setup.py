"""Configures logging to a rotating file so a --noconsole build (which has no
stdout to print to) is still debuggable - check logs/app.log next to the exe.
"""
import logging
import logging.handlers
import sys

from paths import LOGS_DIR


def setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "app.log"

    handlers = [
        logging.handlers.RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
    ]
    if sys.stdout is not None:  # absent under PyInstaller's --noconsole
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
