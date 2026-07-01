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

    # Holds the zone name while waiting for the player to pick an act
    pending_zone: list[str | None] = [None]

    def on_zone_changed(zone_name: str) -> None:
        steps = tracker.enter_zone(zone_name)
        if steps is not None:
            pending_zone[0] = None
            overlay.show_zone(zone_name, steps, tracker.current_act)
            return

        possible_acts = tracker.get_possible_acts(zone_name)
        if possible_acts:
            pending_zone[0] = zone_name
            overlay.show_act_selection(zone_name, possible_acts)
        else:
            pending_zone[0] = None
            overlay.hide_zone()

    def on_act_selected(act: int) -> None:
        tracker.set_act(act)
        zone = pending_zone[0]
        pending_zone[0] = None
        if zone:
            steps = tracker.resolve_current(zone)
            if steps:
                overlay.show_zone(zone, steps, tracker.current_act)
            else:
                overlay.hide_zone()

    overlay.act_selected.connect(on_act_selected)
    watcher = LogWatcher(log_path)
    watcher.zone_changed.connect(on_zone_changed)
    watcher.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
