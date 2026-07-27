import sys
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from act_data import ActTracker
from config import find_client_log, load_progress, save_client_log_path, save_progress
from zone_data import ZoneTracker
from log_watcher import LogWatcher, read_last_zone
from logutil import LOG_FILE, get_logger
from overlay import OverlayWindow

log = get_logger()


def parse_mode(argv: list[str]) -> str:
    """Act mode is what the player sees; --mode=map keeps the older per-zone
    view reachable for testing."""
    for arg in argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]
            if mode in ("act", "map"):
                return mode
            log.warning("Unknown --mode=%s — falling back to act mode.", mode)
    return "act"


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

    overlay = OverlayWindow()
    log.info("Overlay window created.")

    mode = parse_mode(sys.argv)
    log.info("Guidance mode: %s", mode)
    on_zone_changed = (
        wire_act_mode(overlay) if mode == "act" else wire_map_mode(overlay)
    )

    # Show immediately so the player has visual confirmation the overlay is live,
    # then try to pick up whatever zone they're already standing in.
    if not overlay.isVisible():
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


def wire_act_mode(overlay: OverlayWindow):
    """Act checklist: the log moves a pointer through the current act."""
    tracker = ActTracker()

    # Holds the zone name while waiting for the player to pick an act
    pending_zone: list[str | None] = [None]

    def render() -> None:
        if tracker.finished:
            log.info("Campaign complete — act 10 finished.")
            overlay.show_campaign_complete()
            return
        overlay.show_checklist(
            tracker.current_act,
            tracker.steps,
            tracker.pointer,
            tracker.progress(),
            tracker.off_route,
        )
        save_progress(tracker.current_act, tracker.pointer)

    saved = load_progress()
    if saved and tracker.restore(*saved):
        log.info("Restored saved position: act %d, step %d.", *saved)
        render()
    elif saved:
        log.warning("Saved position %s no longer fits acts.json — ignoring.", saved)

    def on_zone_changed(zone_name: str) -> None:
        update = tracker.enter_zone(zone_name)

        if update.kind == "ambiguous":
            pending_zone[0] = zone_name
            log.info("Zone '%s' spans acts %s — asking.", zone_name, list(update.acts))
            overlay.show_act_selection(zone_name, list(update.acts))
            return

        pending_zone[0] = None
        if update.kind == "unknown" and not tracker.current_act:
            log.info("Zone '%s' is not part of the campaign — waiting.", zone_name)
            overlay.show_status(f"{zone_name}\nZone into the campaign to begin.")
            return

        log.info(
            "Zone '%s' → act %d step %d (%s%s).",
            zone_name,
            tracker.current_act,
            tracker.pointer + 1,
            update.kind,
            ", off route" if tracker.off_route else "",
        )
        render()

    def on_act_selected(act: int) -> None:
        log.info("Player selected Act %d.", act)
        tracker.set_act(act, pending_zone[0])
        pending_zone[0] = None
        render()

    def on_back() -> None:
        if tracker.back():
            log.info("Back → act %d step %d.", tracker.current_act, tracker.pointer + 1)
            render()

    overlay.act_selected.connect(on_act_selected)
    overlay.back_pressed.connect(on_back)
    return on_zone_changed


def wire_map_mode(overlay: OverlayWindow):
    """The original per-zone view, kept reachable via --mode=map."""
    tracker = ZoneTracker()

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
    return on_zone_changed


if __name__ == "__main__":
    main()
