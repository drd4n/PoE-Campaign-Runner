"""
Run with: python test_zones.py
No PyQt6 needed. Tests ZoneTracker logic only.
"""
from zone_data import ZoneTracker

CAMPAIGN_PATH = [
    # Act 1
    ("Twilight Strand",         1, True),
    ("Lioneye's Watch",         1, True),
    ("The Coast",               1, True),
    ("Tidal Island",            1, True),
    ("Mud Flats",               1, True),
    ("Submerged Passage",       1, True),
    ("The Ledge",               1, True),
    ("Lower Prison",            1, True),
    ("Warden's Chambers",       1, True),
    ("Ship Graveyard",          1, True),
    ("Cavern of Wrath",         1, True),
    ("Merveil's Lair",          1, True),
    # Act 2
    ("Southern Forest",         2, True),
    ("Crossroads",              2, True),
    ("Chamber of Sins Level 1", 2, True),
    ("Broken Bridge",           2, True),
    ("Western Forest",          2, True),
    ("Wetlands",                2, True),
    ("Pyramid Apex",            2, True),
    # Act 3
    ("City of Sarn",            3, True),
    ("Crematorium",             3, True),
    ("Sewers",                  3, True),
    ("Marketplace",             3, True),
    ("Battlefront",             3, True),
    ("Docks",                   3, True),
    ("Solaris Temple Level 2",  3, True),
    ("Ebony Barracks",          3, True),
    ("Upper Sceptre of God",    3, True),
    # Act 4
    ("Aqueduct",                4, True),
    ("Crystal Veins",           4, True),
    ("Grand Arena",             4, True),
    ("Harvest",                 4, True),
    # Act 5
    ("Slave Pens",              5, True),
    ("Oriath Square",           5, True),
    ("Sanctum of Innocence",    5, True),
    ("Cathedral Apex",          5, True),
    # Act 6 — Lioneye's Watch MUST go to act 6, not stay at 1
    ("Lioneye's Watch",         6, True),
    ("The Coast",               6, True),   # same name, different act
    ("Prisoner's Gate",         6, True),   # different steps from act 1
    ("Brine King's Reef",       6, True),
    # Act 7
    ("The Bridge Encampment",   7, True),
    ("Crossroads",              7, True),   # same name, different steps
    ("Causeway",                7, True),
    ("Temple of Decay Level 2", 7, True),
    # Act 8
    ("Sarn Ramparts",           8, True),
    ("Bath House",              8, True),
    ("Lunaris Temple Level 2",  8, True),
    ("Harbour Bridge",          8, True),
    # Act 9
    ("Blood Aqueduct",          9, True),
    ("Vastiri Desert",          9, True),
    ("Quarry",                  9, True),
    ("Rotting Core",            9, True),
    # Act 10
    ("Oriath Docks",           10, True),
    ("Altar of Hunger",        10, True),
    # Unknown zones — should return None (overlay hides)
    ("Aspirants' Plaza",        10, False),
    ("Azurite Mine",            10, False),
    ("The Rogue Harbour",       10, False),
]

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def run():
    tracker = ZoneTracker()
    failures = 0

    for zone_name, expected_act, expect_steps in CAMPAIGN_PATH:
        steps = tracker.enter_zone(zone_name)

        act_ok = tracker.current_act == expected_act
        steps_ok = (steps is not None) == expect_steps

        status = PASS if (act_ok and steps_ok) else FAIL
        if not (act_ok and steps_ok):
            failures += 1

        act_info = f"act={tracker.current_act} (expected {expected_act})"
        steps_info = f"steps={'yes' if steps else 'none'} (expected {'yes' if expect_steps else 'none'})"
        print(f"{status}  {zone_name:<35} {act_info}  {steps_info}")

        if steps and expect_steps:
            for s in steps:
                print(f"       • {s}")

    print()
    if failures:
        print(f"\033[91m{failures} test(s) failed.\033[0m")
    else:
        print(f"\033[92mAll tests passed.\033[0m")


if __name__ == "__main__":
    run()
