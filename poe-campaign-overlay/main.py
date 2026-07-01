import sys
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from config import find_client_log, save_client_log_path
from zone_data import ZoneTracker
from log_watcher import LogWatcher, read_last_zone
from logutil import LOG_FILE, get_logger
from overlay import OverlayWindow

log = get_logger()


def pick_log_file(app: QApplication) -> str | None:
    path, _ = QFileDialog.getOpenFileName(
        None,
        "Locate Path of Exile Client.txt",
        str(app.applicationDirPath()),
        "Log files (*.txt);;All files (*)",
    )
    return path or None


def main() -> None:
    log.info("=" * 48)
    log.info("PoE Campaign Overlay starting up")
    log.info("Log file: %s", LOG_FILE)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    log_path = find_client_log()

    if not log_path:
        log.info("Opening file picker for manual Client.txt selection.")
        QMessageBox.information(
            None,
            "PoE Campaign Overlay",
            "Could not find Client.txt automatically.\nPlease locate it manually.",
        )
        log_path = pick_log_file(app)

    if not log_path:
        log.warning("No Client.txt selected — exiting.")
        sys.exit(0)

    save_client_log_path(log_path)

    tracker = ZoneTracker()
    overlay = OverlayWindow()
    log.info("Overlay window created.")

    # Holds the zone name while waiting for the player to pick an act
    pending_zone: list[str | None] = [None]

    def on_zone_changed(zone_name: str) -> None:
        steps = tracker.enter_zone(zone_name)
        if steps is not None:
            pending_zone[0] = None
            log.info("Showing guide for '%s' (Act %d).", zone_name, tracker.current_act)
            overlay.show_zone(zone_name, steps, tracker.current_act)
            return

        possible_acts = tracker.get_possible_acts(zone_name)
        if possible_acts:
            pending_zone[0] = zone_name
            log.info("Zone '%s' is ambiguous — asking for act %s.", zone_name, possible_acts)
            overlay.show_act_selection(zone_name, possible_acts)
        else:
            pending_zone[0] = None
            log.info("Zone '%s' not in zone data — showing 'no data'.", zone_name)
            overlay.show_no_data(zone_name)

    def on_act_selected(act: int) -> None:
        log.info("Player selected Act %d.", act)
        tracker.set_act(act)
        zone = pending_zone[0]
        pending_zone[0] = None
        if zone:
            steps = tracker.resolve_current(zone)
            if steps:
                overlay.show_zone(zone, steps, tracker.current_act)
            else:
                log.info("No data for '%s' in Act %d — showing 'no data'.", zone, act)
                overlay.show_no_data(zone)

    overlay.act_selected.connect(on_act_selected)

    # Show immediately so the player has visual confirmation the overlay is live,
    # then try to pick up whatever zone they're already standing in.
    overlay.show_status("Watching Client.txt…\nZone in to begin.")
    log.info("Overlay shown (top-right). Waiting for zone changes.")

    last_zone = read_last_zone(log_path)
    if last_zone:
        log.info("Cold start — current zone: %s", last_zone)
        on_zone_changed(last_zone)
    else:
        log.info("Cold start — no prior zone found in log; waiting for first zone change.")

    watcher = LogWatcher(log_path)
    watcher.zone_changed.connect(on_zone_changed)
    watcher.start()

    log.info("Startup complete — entering event loop.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
