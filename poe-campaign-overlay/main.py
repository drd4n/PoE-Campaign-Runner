import sys
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from config import find_client_log, save_client_log_path
from zone_data import ZoneTracker
from log_watcher import LogWatcher
from overlay import OverlayWindow


def pick_log_file(app: QApplication) -> str | None:
    path, _ = QFileDialog.getOpenFileName(
        None,
        "Locate Path of Exile Client.txt",
        str(app.applicationDirPath()),
        "Log files (*.txt);;All files (*)",
    )
    return path or None


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    log_path = find_client_log()

    if not log_path:
        QMessageBox.information(
            None,
            "PoE Campaign Overlay",
            "Could not find Client.txt automatically.\nPlease locate it manually.",
        )
        log_path = pick_log_file(app)

    if not log_path:
        sys.exit(0)

    save_client_log_path(log_path)

    tracker = ZoneTracker()
    overlay = OverlayWindow()

    watcher = LogWatcher(log_path)

    def on_zone_changed(zone_name: str) -> None:
        steps = tracker.enter_zone(zone_name)
        if steps:
            overlay.show_zone(zone_name, steps, tracker.current_act)
        else:
            overlay.hide_zone()

    watcher.zone_changed.connect(on_zone_changed)
    watcher.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
