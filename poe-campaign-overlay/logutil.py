import logging
import sys
from pathlib import Path

# Written fresh on every launch so it always reflects the current session.
LOG_FILE = Path(__file__).parent / "overlay.log"


def get_logger() -> logging.Logger:
    """Return the shared app logger, writing to stdout and overlay.log.

    The file handler means diagnostics survive even when the app is launched
    without a console (e.g. double-clicked / pythonw), so you can always open
    overlay.log to see whether the program is running correctly.
    """
    logger = logging.getLogger("poe_overlay")
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError as e:  # read-only dir, etc. — console logging still works
        logger.warning("Could not open log file %s: %s", LOG_FILE, e)

    return logger
