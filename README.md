# PoE Campaign Runner

A lightweight, always-on-top overlay for Path of Exile 1 that shows a checklist for the act you're in and tracks your position through it as you play. It reads your `Client.txt` log in real time — no game files are modified.

![Acts 1–10 supported]

---

## Features

- Shows the **whole act as a checklist** — done steps ticked, the step you're on expanded into bullets, everything ahead listed
- Follows you automatically: each zone change moves the pointer forward through the act
- Asks which act you're in every time you enter a town whose name is shared by two acts (Lioneye's Watch 1/6, Sarn Encampment 3/8, Highgate 4/9)
- Marks once-per-league content (`⟲` Trials, Tidal Island) and optional detours (`○` Siosa's skill gems)
- `◀ Back` and `Next ▶` buttons nudge the pointer a step either way when tracking drifts
- Remembers where you were — progress survives a restart
- Transparent, frameless, click-through — only the two step buttons take clicks
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
python3 main.py             # act checklist (default)
python3 main.py --mode=map  # older per-zone view
```

On first launch, if `Client.txt` is not found automatically, a file picker will open. The path is saved to `config.json` so subsequent launches skip this step, along with your act and step so the checklist comes back where you left it.

### What the overlay shows

```
Act 2                                [10/24]
  ✓ Southern Forest — town, Old Fields
  ✓ Old Fields — Den, Great White Beast
  …
  ✓ Fellshrine Ruins — Crypt Level 1
▶ Crypt Level 1 — Trial, Crypt Level 2
     ⟲ Solve Trial
     • Go to The Crypt Level 2
    Crypt Level 2 — Golden Hand, skill pt
    Town — go to Riverways
    …
[ ◀ Back ]  [ Next ▶ ]
```

`✓` done · `▶` current step, expanded · `⟲` once per league · `○` optional detour

If you wander off the route the header reads `Act 2 · off route` and the pointer stays put until you rejoin.

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

### 3. Build the tracker — `act_data.py: ActTracker.__init__()`

Loads `acts.json` — 211 steps across 10 acts, each `{ zone, short, steps[] }` plus optional `per_league` / `optional` flags — and builds a zone → `(act, index)` index from it. Act mode never reads `zones.json`.

`current_act` starts at `0` and `pointer` at `0`; a saved position from `config.json` is restored over them if there is one.

### 4. Build the overlay — `overlay.py: OverlayWindow.__init__()`

Two sub-calls:

**`_build_window()`** sets Qt window flags:
- `FramelessWindowHint` — no title bar or border
- `WindowStaysOnTopHint` — always above the game window
- `Tool` — hidden from the taskbar
- `WA_TranslucentBackground` — window background is transparent
- `WindowTransparentForInput` — mouse clicks pass through to the game

**`_build_ui()`** builds the label hierarchy (header row with act + progress → zone label → steps label) and a hidden `_button_container` with a `QHBoxLayout` reserved for act-selection buttons when a zone is ambiguous.

`StepButtons` is a **second, separate window** holding `◀ Back` and `Next ▶`. The checklist panel keeps `WindowTransparentForInput`, so the only pixels that swallow clicks from the game are the buttons themselves. It re-docks under the panel's bottom-left corner on every move and resize.

The panel itself snaps to the **top-left** of the primary screen (`_snap_top_left()`), a `_MARGIN` in from each edge.

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

### 7. Zone entered — `act_data.py: ActTracker.enter_zone(zone)`

Every zone transition arrives here and can only move the pointer **forward**, which is what makes repeated zones work — "Town" appears five times in Act 2, "Coast" twice in a row in Act 1.

1. **Scan forward** from the pointer for the next step in this act with that zone. Found → jump there, ticking everything passed. Re-entering the zone the pointer already sits on means you left and came back, so the scan starts one step later.
2. **Zone is behind us** (backtracking) → hold the pointer, flag `off_route`.
3. **Zone belongs to another act** → switch, but only if it *starts* that act. Without that guard, walking into Act 1's Tidal Island would yank you to Act 6, where Tidal Island is step 4. At cold start there's no act to protect, so any position is accepted.
4. **Several acts qualify** (Crossroads → 2 and 7) → `Update("ambiguous")`, and the overlay asks. When the next act is among the candidates it wins automatically.
5. **Zone in no act** → `Update("unknown")`; the overlay shows a waiting message.

Between 1 and 2 there's a fallback: plenty of zones are named only inside a step's instructions rather than heading one of their own — Act 1's Mud Flats and Tidal Island both live inside Coast steps. If no step *zone* matches, the tracker scans forward for a step whose bullets name the zone and moves there, so walking the route as written never reads as off-route.

### 8. Draw — `main.py: render()`

`overlay.show_checklist(act, steps, pointer, progress, off_route)` renders via `checklist_view.checklist_html()` — done steps ticked, current step expanded, upcoming steps collapsed — then `config.save_progress()` writes act and pointer to `config.json`.

`progress()` counts mandatory steps only, so the optional Siosa detour doesn't inflate the denominator.

### 9. Corrections — the act picker, `◀ Back` and `Next ▶`

**Shared-name towns always ask.** `acts.json` carries a `towns` map, and the three towns whose name is reused by another act — Lioneye's Watch (1/6), The Sarn Encampment (3/8), Highgate (4/9) — return `Update("ambiguous")` on every entry, before any inference runs. Towns with a name of their own (Forest Encampment, Overseer's Tower…) never ask, and shared-name *non*-town zones (Coast, Crossroads, Crypt Level 1) still resolve silently mid-act.

The zone is stored in `pending_zone` and the answer goes to `choose_act(act, zone)`. Answering with the act you're already in resolves like an ordinary zone entry, so the fourth town trip of Act 3 stays the fourth instead of snapping back to the first; only a real switch resets to that act's first matching step.

`◀ Back` calls `tracker.back()` — pointer −1, unticking that step, rolling into the previous act's last step at a boundary.

`Next ▶` calls `tracker.forward()` — pointer +1, rolling into the next act past the last step. It exists because six places in the campaign run two steps in a row in the same zone (Act 2's Western Forest, Act 6's Prisoner's Gate, Act 10's Ravaged Square…): with no zone change between them, nothing in the log says the first one is done.

Auto-tracking resumes from wherever either button leaves you.

### 10. End of the campaign

Reaching Act 10's last step isn't the end — you still have to kill Kitava. Leaving that step for a zone it doesn't mention sets a sticky `completed` flag and the overlay shows "campaign complete", so heading back to the Blood Aqueduct to level doesn't rewind the tracker to Act 9. `◀ Back` resumes tracking.

### Flow diagram

```
main()
 ├─ find_client_log()            → path to Client.txt
 ├─ parse_mode(sys.argv)         → "act" (default) or "map"
 ├─ OverlayWindow()              → frameless, transparent, always-on-top window
 ├─ wire_act_mode(overlay)       → ActTracker + restored progress
 ├─ LogWatcher.start()           → background thread tailing Client.txt
 └─ app.exec()                   → event loop

  [background thread]
  LogWatcher.run()
   └─ readline() + regex → emit zone_changed(name)

  [main thread, on signal]
  on_zone_changed(name)
   └─ ActTracker.enter_zone()
       ├─ "moved"/"held" → render()  → show_checklist() + save_progress()
       ├─ "ambiguous"    → overlay.show_act_selection()  (interactive)
       └─ "unknown"      → overlay.show_status()

  [player clicks]
  act button  → tracker.choose_act(act, pending_zone) → render()
  ◀ Back      → tracker.back()                     → render()
  Next ▶      → tracker.forward()                  → render()
```

### Map mode — `--mode=map`

The original per-zone view is untouched behind the flag: `ZoneTracker` reads `zones.json` (`_milestones` zone → act, `_zones` zone → act → steps), advances the act on milestone zones, and `show_zone()` prints the steps for the zone you're standing in. `enter_zone()` returning `None` for a zone that exists in several acts is what triggers the act picker there.

---

## Project Structure

```
poe-campaign-overlay/
├── main.py             # Entry point — mode selection and wiring
├── config.py           # Client.txt path and saved progress
├── log_watcher.py      # Background thread that tails Client.txt
├── act_data.py         # ActTracker — the act checklist and position pointer
├── acts.json           # 211 steps + town map, Acts 1–10     (act mode)
├── checklist_view.py   # Checklist rendering — pure strings, no Qt
├── overlay.py          # PyQt6 overlay window + step button window
├── zone_data.py        # ZoneTracker — per-zone lookup        (map mode)
├── zones.json          # Zone steps and act milestones        (map mode)
├── simulate.py         # Test helper — writes fake log lines to /tmp
├── test_acts.py        # Headless tests for ActTracker logic
├── test_act_mode.py    # Headless tests for the wiring and rendering
├── test_zones.py       # Headless tests for ZoneTracker logic
└── requirements.txt
```

---

## Running Tests

```bash
cd poe-campaign-overlay
python3 test_acts.py       # ActTracker: 93 checks
python3 test_act_mode.py   # log line → overlay wiring + rendering: 43 checks
python3 test_zones.py      # ZoneTracker (map mode)
```

All three run headlessly — no display needed. `test_act_mode.py` stubs PyQt6 so `main.py`'s wiring is covered without Qt installed; between them they walk the full campaign, both duplicate-zone cases, act switching, off-route holds, both step buttons, persistence and completion.

---

## Data & Credits

`acts.json` is adapted from the [PoE Wiki *Acts quick guide*](https://www.poewiki.net/wiki/Guide:Acts_quick_guide), used under **CC BY-NC-SA 3.0**. It was converted once (source URL, revision and licence are recorded in the file's `_source` header) and is hand-maintained from there — there is no re-fetch step.

`zones.json` predates it and remains the map-mode data source.
