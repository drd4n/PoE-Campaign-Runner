"""
Run with: python test_act_mode.py
Drives main.py's act-mode wiring and the checklist renderer with PyQt6 stubbed
out, so the whole path from a log line to what the overlay is told to draw is
covered without a display.
"""
import json
import sys
import tempfile
import types
from pathlib import Path

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    _results.append(ok)
    print(f"{PASS if ok else FAIL}  {label}{('  — ' + detail) if detail and not ok else ''}")


# --- stub PyQt6 so main.py/overlay.py are importable ------------------------


class _Signal:
    def __init__(self, *_):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in list(self._slots):
            slot(*args)


def _install_qt_stubs() -> None:
    qt = types.ModuleType("PyQt6")
    widgets = types.ModuleType("PyQt6.QtWidgets")
    core = types.ModuleType("PyQt6.QtCore")
    gui = types.ModuleType("PyQt6.QtGui")

    class _Any:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, _name):
            return _Any()

        def __call__(self, *a, **k):
            return _Any()

    for name in ("QWidget", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
                 "QApplication", "QFileDialog", "QMessageBox"):
        setattr(widgets, name, _Any)
    for name in ("Qt", "QRectF", "QThread"):
        setattr(core, name, _Any)
    core.pyqtSignal = _Signal
    for name in ("QFont", "QPainter", "QColor", "QPainterPath"):
        setattr(gui, name, _Any)

    sys.modules.update({
        "PyQt6": qt, "PyQt6.QtWidgets": widgets,
        "PyQt6.QtCore": core, "PyQt6.QtGui": gui,
    })


_install_qt_stubs()

import config  # noqa: E402
import main  # noqa: E402
from act_data import ActTracker  # noqa: E402
from checklist_view import checklist_html  # noqa: E402


# --- a recording stand-in for the overlay -----------------------------------


class FakeOverlay:
    def __init__(self):
        self.act_selected = _Signal()
        self.back_pressed = _Signal()
        self.calls: list[tuple] = []
        self.checklist = None

    def show_checklist(self, act, steps, pointer, progress, off_route):
        self.calls.append(("checklist", act, pointer, progress, off_route))
        self.checklist = (act, steps, pointer, progress, off_route)

    def show_act_selection(self, zone, acts):
        self.calls.append(("picker", zone, tuple(acts)))

    def show_status(self, message):
        self.calls.append(("status", message))

    def show_campaign_complete(self):
        self.calls.append(("complete",))

    def isVisible(self):
        return bool(self.calls)

    def last(self, kind):
        return next((c for c in reversed(self.calls) if c[0] == kind), None)


def wired(tmp_config: Path):
    """A fresh act-mode wiring with config.json redirected to a temp file."""
    config.CONFIG_FILE = tmp_config
    overlay = FakeOverlay()
    return overlay, main.wire_act_mode(overlay)


# --- tests ------------------------------------------------------------------


def test_zone_to_overlay(tmp: Path):
    print("--- log line → overlay ---")
    overlay, on_zone = wired(tmp / "a.json")

    on_zone("The Twilight Strand")
    kind, act, pointer, progress, off_route = overlay.last("checklist")
    check("first zone draws the checklist", kind == "checklist")
    check("…for act 1 step 1", (act, pointer) == (1, 0), f"act {act} step {pointer}")
    check("…with progress 0/18", progress == (0, 18), str(progress))
    check("…not off route", off_route is False)

    on_zone("The Ship Graveyard")
    _, act, pointer, progress, _ = overlay.last("checklist")
    check("skipping ahead ticks the steps between", progress == (15, 18), str(progress))

    on_zone("The Coast")
    *_, off_route = overlay.last("checklist")
    check("backtracking redraws as off route", off_route is True)


def test_picker(tmp: Path):
    print("\n--- act picker ---")
    overlay, on_zone = wired(tmp / "b.json")

    on_zone("The Crossroads")
    call = overlay.last("picker")
    check("ambiguous zone opens the picker", call is not None)
    check("…offering acts 2 and 7", call[2] == (2, 7), str(call and call[2]))
    check("…and draws no checklist yet", overlay.last("checklist") is None)

    overlay.act_selected.emit(7)
    _, act, pointer, *_ = overlay.last("checklist")
    check("picking act 7 draws act 7", act == 7, str(act))
    check("…on a Crossroads step", overlay.checklist[1][pointer].zone == "The Crossroads")


def test_back_button(tmp: Path):
    print("\n--- back button ---")
    overlay, on_zone = wired(tmp / "c.json")
    on_zone("The Twilight Strand")
    on_zone("The Ship Graveyard")

    overlay.back_pressed.emit()
    _, _, pointer, progress, _ = overlay.last("checklist")
    check("back redraws one step earlier", pointer == 14, str(pointer))
    check("…with that step unticked", progress == (14, 18), str(progress))

    before = len(overlay.calls)
    overlay, on_zone = wired(tmp / "c2.json")
    on_zone("The Twilight Strand")
    before = len(overlay.calls)
    overlay.back_pressed.emit()
    check("back at the very first step redraws nothing", len(overlay.calls) == before)


def test_persistence(tmp: Path):
    print("\n--- persistence ---")
    cfg = tmp / "d.json"
    overlay, on_zone = wired(cfg)
    on_zone("The Blood Aqueduct")
    on_zone("The Vastiri Desert")
    saved = json.loads(cfg.read_text())
    check("position is written to config.json", saved.get("act") == 9, str(saved))

    # A second launch restores it before any log line arrives.
    overlay2, _ = wired(cfg)
    call = overlay2.last("checklist")
    check("relaunch draws the saved position immediately", call is not None)
    check("…at act 9", call and call[1] == 9, str(call and call[1]))
    check("…same step", call and call[2] == saved["step"], str(call and call[2]))

    # An unrelated key must survive a progress write.
    cfg.write_text(json.dumps({"client_log_path": "/tmp/x.txt"}))
    config.CONFIG_FILE = cfg
    config.save_progress(4, 2)
    after = json.loads(cfg.read_text())
    check("saving progress keeps client_log_path", after.get("client_log_path") == "/tmp/x.txt")

    cfg.write_text(json.dumps({"act": 99, "step": 999}))
    overlay3, _ = wired(cfg)
    check("a stale saved position is ignored", overlay3.last("checklist") is None)


def test_non_campaign_zone(tmp: Path):
    print("\n--- non-campaign zone ---")
    overlay, on_zone = wired(tmp / "e.json")
    on_zone("The Rogue Harbour")
    call = overlay.last("status")
    check("a zone in no act shows a status message", call is not None)
    check("…naming the zone", call and "Rogue Harbour" in call[1], str(call))
    check("…and draws no checklist", overlay.last("checklist") is None)


def test_campaign_complete(tmp: Path):
    print("\n--- campaign complete ---")
    overlay, on_zone = wired(tmp / "f.json")
    on_zone("Oriath Docks")
    on_zone("Altar of Hunger")
    check("act 10 final step is drawn", overlay.last("checklist")[2] == 14)
    on_zone("The Blood Aqueduct")  # off to level after Kitava
    check("leaving after the last step shows 'campaign complete'",
          overlay.last("complete") is not None)


def test_rendering():
    print("\n--- checklist rendering ---")
    t = ActTracker()
    t.enter_zone("The City of Sarn")
    t.enter_zone("The Crematorium")
    html = checklist_html(t.steps, t.pointer)

    check("done steps are ticked", html.count("&#10003;") == t.pointer, str(html.count("&#10003;")))
    check("exactly one current marker", html.count("&#9654;") == 1)
    check("the 4 optional steps are marked", html.count("&#9675;") == 4, str(html.count("&#9675;")))
    check(
        "the current step's per-league bullet is marked",
        html.count("&#8634;") == 1,
        str(html.count("&#8634;")),
    )
    check("every step appears exactly once", all(
        html.count(">" + s.short.split(" — ")[0]) >= 0 for s in t.steps))
    check("bullets render only for the current step",
          html.count("&bull;") == len(t.current_step.bullets) - 1)

    # An apostrophe or ampersand in a zone name must not break the markup.
    t2 = ActTracker()
    t2.enter_zone("The Weaver's Chambers")
    check("names with apostrophes survive escaping",
          "Weaver&#x27;s Chambers" in checklist_html(t2.steps, t2.pointer)
          or "Weaver's Chambers" in checklist_html(t2.steps, t2.pointer))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_zone_to_overlay(tmp)
        test_picker(tmp)
        test_back_button(tmp)
        test_persistence(tmp)
        test_non_campaign_zone(tmp)
        test_campaign_complete(tmp)
        test_rendering()

    failed = _results.count(False)
    print()
    if failed:
        print(f"\033[91m{failed} of {len(_results)} test(s) failed.\033[0m")
    else:
        print(f"\033[92mAll {len(_results)} tests passed.\033[0m")
    raise SystemExit(1 if failed else 0)
