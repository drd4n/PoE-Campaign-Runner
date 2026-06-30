import re
from PyQt6.QtCore import QThread, pyqtSignal

_ZONE_RE = re.compile(r"You have entered (.+)\.")


class LogWatcher(QThread):
    zone_changed = pyqtSignal(str)

    def __init__(self, log_path: str):
        super().__init__()
        self._log_path = log_path
        self._running = True

    def run(self) -> None:
        with open(self._log_path, encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # start at end — ignore history
            while self._running:
                line = f.readline()
                if line:
                    m = _ZONE_RE.search(line)
                    if m:
                        self.zone_changed.emit(m.group(1))
                else:
                    self.msleep(2000)  # poll every 2s

    def stop(self) -> None:
        self._running = False
        self.wait()
