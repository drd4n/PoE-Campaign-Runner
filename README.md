# PoE Campaign Runner

A lightweight, always-on-top overlay for Path of Exile 1 that shows zone objectives and waypoint hints as you move through the campaign. It reads your `Client.txt` log in real time — no game files are modified.

![Acts 1–10 supported]

---

## Features

- Tracks your progress through Acts 1–10 automatically
- Shows objectives and directional hints per zone (e.g. "Waypoint — left of entrance", "Boss — top of zone")
- Handles duplicate zone names across acts (Lioneye's Watch, Crossroads, etc.) with an in-overlay act picker
- Transparent, frameless, click-through — the overlay never steals focus or blocks gameplay
- Auto-discovers `Client.txt` on Steam/Wine/Windows; falls back to a manual file picker

---

## Requirements

- Python 3.10+
- PyQt6

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
cd poe-campaign-overlay
python3 main.py
```

On first launch, if `Client.txt` is not found automatically, a file picker will open. The path is saved to `config.json` so subsequent launches skip this step.

To simulate zone transitions for testing (no game needed):

```bash
# Terminal 1
python3 main.py          # point the file picker at /tmp/poe_test_client.txt

# Terminal 2
python3 simulate.py      # writes one zone every 3 seconds
```

---

## How It Works

### 1. Entry point — `main.py: main()`

`python3 main.py` calls `main()`. A `QApplication` is created first — Qt requires this before any window can exist.

### 2. Find the log file — `config.py: find_client_log()`

Searches common installation paths (Steam, Wine, Windows) for `Client.txt`. If found, the path is returned immediately. If not, a `QMessageBox` prompts the player to locate it manually via a `QFileDialog` file picker.

Once confirmed, `save_client_log_path()` writes the path to `config.json` so the next launch skips the search.

### 3. Build the tracker — `zone_data.py: ZoneTracker.__init__()`

Loads `zones.json` into two dictionaries:

- `_milestones` — maps zone name → act number (e.g. `"Southern Forest" → 2`). Used to auto-advance the act counter as you progress.
- `_zones` — maps zone name → act → `{ steps: [...] }`. The full guide data for all 10 acts.

`current_act` starts at `0` (unknown until the first recognisable zone is seen).

### 4. Build the overlay — `overlay.py: OverlayWindow.__init__()`

Two sub-calls:

**`_build_window()`** sets Qt window flags:
- `FramelessWindowHint` — no title bar or border
- `WindowStaysOnTopHint` — always above the game window
- `Tool` — hidden from the taskbar
- `WA_TranslucentBackground` — window background is transparent
- `WindowTransparentForInput` — mouse clicks pass through to the game

**`_build_ui()`** builds the label hierarchy (act label → zone label → steps label) and a hidden `_button_container` with an `QHBoxLayout` reserved for act-selection buttons when a zone is ambiguous.

### 5. Start watching the log — `log_watcher.py: LogWatcher.run()`

`watcher.start()` launches `LogWatcher` on a background `QThread`. `run()` opens `Client.txt`, seeks immediately to the end (`f.seek(0, 2)`) to ignore history, then loops:

```
readline() → got a line?
  yes → run regex → match? → emit zone_changed(name)
  no  → sleep 2s → try again
```

The regex `r"You have entered (.+)\."` matches only the exact PoE zone-entry format. Chat messages, trade whispers, death messages, and engine warnings are all ignored.

### 6. Qt event loop — `app.exec()`

The main thread blocks here, processing Qt events. The log watcher runs in the background thread. When it emits `zone_changed`, Qt delivers it safely to the main thread — no manual locking needed.

### 7. Zone entered — `main.py: on_zone_changed(zone_name)`

Every zone transition arrives here. It calls `tracker.enter_zone(zone_name)`, which runs two steps in sequence:

**`_update_act(zone_name)`** — updates `current_act`:
- Special case: `"Lioneye's Watch"` with `current_act == 5` → advance to act 6. This is the only zone that exists in two acts with different steps.
- Normal case: check `_milestones`. If the zone is listed and its act is higher than the current one, advance.
- No match: `current_act` stays unchanged.

**`_resolve_steps(zone_name)`** — looks up the steps:
- Try `_zones[zone_name][str(current_act)]` — exact act match.
- If no match and the zone has only one act entry, use that (unambiguous zone).
- If still no match (zone has multiple act entries and the act is unknown), return `None`.

### 8a. Steps found → `overlay.py: show_zone()`

`show_zone(zone_name, steps, act)`:
1. Hides the button container, shows the steps label
2. Calls `_set_interactive(False)` — restores `WindowTransparentForInput = True` (click-through)
3. Updates the act / zone / steps labels
4. `adjustSize()` — resizes the window to fit the content
5. `_snap_top_right()` — repositions to the top-right corner of the primary screen
6. `show()` — makes the overlay visible

### 8b. Ambiguous zone → `overlay.py: show_act_selection()`

When `enter_zone` returns `None`, `on_zone_changed` calls `tracker.get_possible_acts(zone_name)` to get the list of acts this zone has data for (e.g. `[1, 6]` for Lioneye's Watch).

The zone name is stored in `pending_zone`. Then `show_act_selection(zone_name, [1, 6])`:
1. Hides the steps label, shows the button container
2. Builds one `QPushButton("Act N")` per possible act; each button emits `overlay.act_selected(N)` when clicked
3. Calls `_set_interactive(True)` — sets `WindowTransparentForInput = False` so the player can click the buttons
4. `adjustSize()` + `_snap_top_right()` + `show()`

### 9. Player picks an act → `main.py: on_act_selected(act)`

Fired when the player clicks an act button:
1. `tracker.set_act(act)` — sets `current_act` directly
2. Retrieves `pending_zone` (the zone that triggered the picker)
3. `tracker.resolve_current(zone_name)` — resolves steps using the now-known act, without re-running `_update_act`
4. `overlay.show_zone()` displays the steps

From this point `current_act` is set. All subsequent zones resolve automatically via milestones or the single-act fallback, without requiring player input again.

### Flow diagram

```
main()
 ├─ find_client_log()            → path to Client.txt
 ├─ ZoneTracker()                → loads zones.json into memory
 ├─ OverlayWindow()              → frameless, transparent, always-on-top window
 ├─ LogWatcher.start()           → background thread tailing Client.txt
 └─ app.exec()                   → event loop

  [background thread]
  LogWatcher.run()
   └─ readline() + regex → emit zone_changed(name)

  [main thread, on signal]
  on_zone_changed(name)
   ├─ ZoneTracker.enter_zone()
   │   ├─ _update_act()          → advance current_act via milestones
   │   └─ _resolve_steps()       → look up steps for current act
   │
   ├─ steps found      → overlay.show_zone()          (click-through)
   ├─ ambiguous zone   → overlay.show_act_selection() (interactive)
   └─ unknown zone     → overlay.hide_zone()

  [player clicks act button]
  on_act_selected(act)
   ├─ tracker.set_act(act)
   └─ overlay.show_zone(tracker.resolve_current(zone))
```

---

## Project Structure

```
poe-campaign-overlay/
├── main.py           # Entry point — wires all components together
├── config.py         # Finds and saves the Client.txt path
├── log_watcher.py    # Background thread that tails Client.txt
├── zone_data.py      # ZoneTracker — act logic and step lookup
├── overlay.py        # PyQt6 overlay window
├── zones.json        # All zone steps and act milestones for Acts 1–10
├── simulate.py       # Test helper — writes fake log lines to /tmp
├── test_zones.py     # Headless tests for ZoneTracker logic
└── requirements.txt
```

---

## Running Tests

```bash
cd poe-campaign-overlay
python3 test_zones.py
```

No PyQt6 usage — tests run headlessly and cover the full campaign path plus act-selection disambiguation.
