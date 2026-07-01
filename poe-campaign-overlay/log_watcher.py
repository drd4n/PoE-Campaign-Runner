import re
from PyQt6.QtCore import QThread, pyqtSignal

from logutil import get_logger

log = get_logger()

_ZONE_RE = re.compile(r"You have entered (.+)\.")


def read_last_zone(log_path: str) -> str | None:
    """Scan the existing log for the most recent zone entry.

    Used on startup so the overlay reflects the zone the player is already in,
    instead of staying blank until the next zone transition.
    """
    last = None
    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = _ZONE_RE.search(line)
                if m:
                    last = m.group(1)
    except OSError as e:
        log.error("Could not read log for cold start: %s", e)
        return None
    return last


class LogWatcher(QThread):
    zone_changed = pyqtSignal(str)

    def __init__(self, log_path: str):
        super().__init__()
        self._log_path = log_path
        self._running = True

    def run(self) -> None:
        log.info("Watching for zone changes in: %s", self._log_path)
        with open(self._log_path, encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # start at end — ignore history
            while self._running:
                line = f.readline()
                if line:
                    m = _ZONE_RE.search(line)
                    if m:
                        log.info("Zone entered: %s", m.group(1))
                        self.zone_changed.emit(m.group(1))
                else:
                    self.msleep(2000)  # poll every 2s
        log.info("Log watcher stopped.")

    def stop(self) -> None:
        self._running = False
        self.wait()
