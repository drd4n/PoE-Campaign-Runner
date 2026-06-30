"""
Simulates PoE zone transitions by appending fake Client.txt lines.
Run this WHILE main.py is running to test the full stack.

Usage:
  Terminal 1:  python main.py
               (when file picker opens, point it at /tmp/poe_test_client.txt)

  Terminal 2:  python simulate.py
"""
import time
from pathlib import Path

LOG_FILE = Path("/tmp/poe_test_client.txt")

ZONES = [
    "Twilight Strand",
    "Lioneye's Watch",
    "The Coast",
    "Tidal Island",
    "Mud Flats",
    "Submerged Passage",
    "The Ledge",
    "Lower Prison",
    "Warden's Chambers",
    "Ship Graveyard",
    "Cavern of Wrath",
    "Merveil's Lair",
    "Southern Forest",
    "Crossroads",
    "Chamber of Sins Level 1",
    "Broken Bridge",
    "Western Forest",
    "Pyramid Apex",
    "City of Sarn",
    "Crematorium",
    "Sewers",
    "Aqueduct",
    "Crystal Veins",
    "Harvest",
    "Slave Pens",
    "Cathedral Apex",
    "Lioneye's Watch",   # Act 6 — overlay should show Act 6 steps
    "The Coast",         # Act 6 — different steps from Act 1
    "Brine King's Reef",
    "The Bridge Encampment",
    "Causeway",
    "Sarn Ramparts",
    "Harbour Bridge",
    "Blood Aqueduct",
    "Vastiri Desert",
    "Rotting Core",
    "Oriath Docks",
    "Altar of Hunger",
    # Unknown zone — overlay should hide
    "Aspirants' Plaza",
]

DELAY = 3  # seconds between zones


def main():
    LOG_FILE.write_text("")
    print(f"Writing fake log to {LOG_FILE}")
    print(f"Point main.py at this file when the file picker opens.\n")
    print(f"Sending one zone every {DELAY}s. Press Ctrl+C to stop.\n")

    import datetime

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for zone in ZONES:
            ts = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            line = f"{ts} 1234567890 ba9 [INFO Client 4210] : You have entered {zone}.\n"
            f.write(line)
            f.flush()
            print(f"→ {zone}")
            time.sleep(DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
