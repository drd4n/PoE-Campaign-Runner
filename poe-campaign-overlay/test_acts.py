"""
Run with: python test_acts.py
No PyQt6 needed. Tests ActTracker logic only.
"""
from act_data import ActTracker

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

_results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    _results.append(ok)
    print(f"{PASS if ok else FAIL}  {label}{('  — ' + detail) if detail and not ok else ''}")


def fresh() -> ActTracker:
    return ActTracker()


# --- data sanity ------------------------------------------------------------


def test_data():
    print("--- acts.json ---")
    t = fresh()
    check("all 10 acts present", sorted(t._acts) == list(range(1, 11)))
    check("211 steps loaded", sum(len(v) for v in t._acts.values()) == 211)
    check(
        "every step has a zone, short and at least one bullet",
        all(s.zone and s.short and s.bullets for v in t._acts.values() for s in v),
    )
    check(
        "each act starts on its own entry zone",
        all(v[0].zone for v in t._acts.values()),
    )
    starts = {a: v[0].zone for a, v in t._acts.items()}
    check(
        "act 2 starts at Southern Forest",
        starts[2] == "The Southern Forest",
        str(starts[2]),
    )
    check("act 6 starts at Lioneye's Watch", starts[6] == "Lioneye's Watch", str(starts[6]))


# --- cold start -------------------------------------------------------------


def test_cold_start():
    print("\n--- cold start ---")
    t = fresh()
    u = t.enter_zone("The Docks")
    check("unique zone sets its act", u.kind == "moved" and t.current_act == 3, u.kind)
    check("…and points at that zone's step", t.current_step.zone == "The Docks")

    t = fresh()
    u = t.enter_zone("The Crossroads")
    check("multi-act zone asks the player", u.kind == "ambiguous", u.kind)
    check("…offering acts 2 and 7", u.acts == (2, 7), str(u.acts))
    t.set_act(7, "The Crossroads")
    check("picking act 7 lands on a Crossroads step", t.current_step.zone == "The Crossroads")
    check("…in act 7", t.current_act == 7)

    t = fresh()
    u = t.enter_zone("The Rogue Harbour")
    check("zone in no act is unknown", u.kind == "unknown", u.kind)
    check("…and leaves the act unset", t.current_act == 0)


# --- forward-only tracking --------------------------------------------------


def test_forward_only():
    print("\n--- forward-only tracking ---")
    t = fresh()
    t.enter_zone("The Twilight Strand")
    check("act 1 picked up from Twilight Strand", t.current_act == 1 and t.pointer == 0)

    t.enter_zone("Lioneye's Watch")
    check("town is step 2", t.pointer == 1)

    t.enter_zone("The Coast")
    check("Coast is step 3", t.pointer == 2)

    # Step 3's own instructions send you to Tidal Island and back.
    u = t.enter_zone("The Tidal Island")
    check("zone named inside the step holds the pointer", u.kind == "held" and t.pointer == 2)
    check("…and is not flagged off-route", t.off_route is False)
    check("…and does not jump to act 6", t.current_act == 1)

    u = t.enter_zone("The Coast")
    check("returning to Coast advances to the second Coast step", t.pointer == 3, str(t.pointer))

    t.enter_zone("The Submerged Passage")
    check("Submerged Passage is step 5", t.pointer == 4)
    t.enter_zone("The Flooded Depths")
    check("Flooded Depths is step 6", t.pointer == 5)
    t.enter_zone("Lioneye's Watch")
    check("town again is step 7, not step 2", t.pointer == 6, str(t.pointer))
    t.enter_zone("The Submerged Passage")
    check("Submerged Passage again is step 8, not step 5", t.pointer == 7, str(t.pointer))

    # Skipping ahead ticks off everything in between.
    t.enter_zone("The Ship Graveyard")
    check("jumping ahead skips intervening steps", t.pointer == 15, str(t.pointer))
    done, total = t.progress()
    check("progress counts the skipped steps as done", (done, total) == (15, 18), f"{done}/{total}")


# --- act transitions --------------------------------------------------------


def test_transitions():
    print("\n--- act transitions ---")
    t = fresh()
    t.enter_zone("The Twilight Strand")
    u = t.enter_zone("The Southern Forest")
    check("Southern Forest moves act 1 → 2", u.kind == "moved" and t.current_act == 2, u.kind)
    check("…landing on act 2 step 1", t.pointer == 0)
    check("…without asking, despite also being an act 6 zone", u.acts == ())

    # Lioneye's Watch is act 1's town and act 6's opening zone.
    t = fresh()
    t.enter_zone("The Slave Pens")
    check("Slave Pens sets act 5", t.current_act == 5)
    u = t.enter_zone("Lioneye's Watch")
    check("Lioneye's Watch after act 5 goes to act 6", t.current_act == 6, str(t.current_act))
    check("…on step 1", t.pointer == 0 and u.kind == "moved")

    # …but the same zone mid-act-1 must not leap to act 6.
    t = fresh()
    t.enter_zone("The Twilight Strand")
    t.enter_zone("Lioneye's Watch")
    check("Lioneye's Watch in act 1 stays in act 1", t.current_act == 1, str(t.current_act))

    # A zone that only exists mid-way through another act must not switch acts.
    t = fresh()
    t.enter_zone("The Twilight Strand")
    u = t.enter_zone("The Karui Fortress")  # act 6, step 8
    check("mid-act zone of another act does not switch", t.current_act == 1, str(t.current_act))
    check("…and reports off-route", u.kind == "held" and t.off_route is True)


# --- off-route --------------------------------------------------------------


def test_off_route():
    print("\n--- off-route ---")
    t = fresh()
    t.enter_zone("The Twilight Strand")
    t.enter_zone("The Ship Graveyard")
    before = t.pointer
    u = t.enter_zone("The Coast")
    check("backtracking holds the pointer", u.kind == "held" and t.pointer == before)
    check("…and flags off-route", t.off_route is True)

    t.enter_zone("The Cavern of Wrath")
    check("moving forward again clears off-route", t.off_route is False and t.pointer == 16)


# --- back button ------------------------------------------------------------


def test_back():
    print("\n--- back button ---")
    t = fresh()
    t.enter_zone("The Twilight Strand")
    t.enter_zone("The Ship Graveyard")
    check("back moves one step", t.back() is True and t.pointer == 14, str(t.pointer))
    done, _ = t.progress()
    check("…and unticks that step", done == 14, str(done))

    t.enter_zone("The Ship Graveyard")
    check("auto-tracking re-advances after a back press", t.pointer == 15, str(t.pointer))

    t = fresh()
    t.enter_zone("The Twilight Strand")
    t.enter_zone("The Southern Forest")
    check("back at act 2 step 1 rolls into act 1", t.back() is True and t.current_act == 1)
    check("…at act 1's last step", t.pointer == 17, str(t.pointer))

    t = fresh()
    t.enter_zone("The Twilight Strand")
    check("back at act 1 step 1 does nothing", t.back() is False and t.pointer == 0)

    t = fresh()
    t.enter_zone("The Ship Graveyard")
    t.off_route = True
    t.back()
    check("back clears off-route", t.off_route is False)


# --- optional and per-league ------------------------------------------------


def test_flags():
    print("\n--- optional / per-league ---")
    t = fresh()
    act3 = t._acts[3]
    optional = [i for i, s in enumerate(act3) if s.optional]
    check("act 3 has the 4 Siosa steps marked optional", len(optional) == 4, str(optional))
    check(
        "…sitting directly after the Imperial Gardens step",
        act3[optional[0] - 1].zone == "The Imperial Gardens",
        act3[optional[0] - 1].zone,
    )
    check(
        "optional steps are excluded from the denominator",
        sum(1 for s in act3 if not s.optional) == 23,
    )

    per_league = [s for v in t._acts.values() for s in v if s.per_league]
    check("14 steps carry per-league bullets", len(per_league) == 14, str(len(per_league)))
    trial = t._acts[1][10]
    check("act 1 Lower Prison trial is per-league", trial.per_league == {0}, str(trial.per_league))

    # Skipping the optional detour still tracks correctly.
    t.enter_zone("The City of Sarn")
    t.enter_zone("The Imperial Gardens")
    t.enter_zone("The Sceptre of God")
    check("skipping the Siosa detour lands on Sceptre of God", t.current_step.zone == "The Sceptre of God")
    # …and taking it works too.
    t = fresh()
    t.enter_zone("The City of Sarn")
    t.enter_zone("The Imperial Gardens")
    t.enter_zone("The Library")
    check("taking the detour tracks into The Library", t.current_step.zone == "The Library")
    check("…without leaving act 3", t.current_act == 3)


# --- persistence ------------------------------------------------------------


def test_restore():
    print("\n--- persistence ---")
    t = fresh()
    t.enter_zone("The Blood Aqueduct")
    t.enter_zone("The Vastiri Desert")
    act, step = t.current_act, t.pointer

    t2 = fresh()
    check("restore reapplies a saved position", t2.restore(act, step) is True)
    check("…act matches", t2.current_act == act)
    check("…step matches", t2.pointer == step)
    check("restore rejects an out-of-range step", fresh().restore(9, 999) is False)
    check("restore rejects an unknown act", fresh().restore(99, 0) is False)

    # A saved position is corrected forward by the next zone line.
    t2.enter_zone("The Quarry")
    check("saved position still tracks forward", t2.current_step.zone == "The Quarry")


# --- full campaign walk -----------------------------------------------------

CAMPAIGN = [
    ("The Twilight Strand", 1), ("Lioneye's Watch", 1), ("The Coast", 1),
    ("The Mud Flats", 1), ("The Submerged Passage", 1), ("The Ledge", 1),
    ("The Climb", 1), ("The Lower Prison", 1), ("The Warden's Chambers", 1),
    ("The Ship Graveyard", 1), ("The Cavern of Wrath", 1), ("Merveil's Lair", 1),
    ("The Southern Forest", 2), ("The Old Fields", 2), ("The Crossroads", 2),
    ("The Chamber of Sins Level 2", 2), ("The Broken Bridge", 2),
    ("The Crypt Level 2", 2), ("The Western Forest", 2), ("The Wetlands", 2),
    ("Pyramid Apex", 2),
    ("The City of Sarn", 3), ("The Crematorium", 3), ("The Marketplace", 3),
    ("The Docks", 3), ("The Ebony Barracks", 3), ("The Imperial Gardens", 3),
    ("The Upper Sceptre of God", 3),
    ("The Aqueduct", 4), ("The Dried Lake", 4), ("The Crystal Veins", 4),
    ("Kaom's Stronghold", 4), ("The Grand Arena", 4), ("The Harvest", 4),
    ("The Ascent", 4),
    ("The Slave Pens", 5), ("Oriath Square", 5), ("Sanctum of Innocence", 5),
    ("The Ruined Square", 5), ("Cathedral Apex", 5),
    ("Lioneye's Watch", 6), ("The Coast", 6), ("The Mud Flats", 6),
    ("The Ridge", 6), ("Prisoner's Gate", 6), ("The Wetlands", 6),
    ("The Beacon", 6), ("The Brine King's Reef", 6),
    ("The Bridge Encampment", 7), ("The Crossroads", 7), ("The Crypt Level 1", 7),
    ("The Den", 7), ("The Dread Thicket", 7), ("The Causeway", 7),
    ("The Temple of Decay Level 2", 7),
    ("The Sarn Ramparts", 8), ("The Toxic Conduits", 8), ("The Bath House", 8),
    ("The Lunaris Concourse", 8), ("The Quay", 8), ("The Imperial Fields", 8),
    ("The Harbour Bridge", 8),
    ("The Blood Aqueduct", 9), ("The Vastiri Desert", 9), ("The Foothills", 9),
    ("The Tunnel", 9), ("The Quarry", 9), ("The Rotting Core", 9),
    ("Oriath Docks", 10), ("The Ravaged Square", 10), ("The Desecrated Chambers", 10),
    ("The Canals", 10), ("Altar of Hunger", 10),
]


def test_completion():
    print("\n--- campaign completion ---")
    t = fresh()
    t.enter_zone("Oriath Docks")
    t.enter_zone("Altar of Hunger")
    check("on the final step, not yet finished", t.finished is False)

    # The final step tells you to return to Oriath Docks for the skill point.
    t.enter_zone("Oriath Docks")
    check("a zone the final step names doesn't end it", t.finished is False)

    t.enter_zone("The Blood Aqueduct")
    check("leaving for act 9 to level ends the campaign", t.finished is True)
    check("…and does not rewind to act 9", t.current_act == 10, str(t.current_act))

    t.enter_zone("The Twilight Strand")
    check("further zones stay finished", t.finished is True and t.current_act == 10)

    t.back()
    check("back resumes tracking", t.finished is False)
    check("…on the final step it left", t.pointer == 14, str(t.pointer))


def test_campaign():
    print("\n--- full campaign walk (acts 1 → 10) ---")
    t = fresh()
    bad = []
    for zone, expected_act in CAMPAIGN:
        u = t.enter_zone(zone)
        if u.kind == "ambiguous":
            t.set_act(expected_act, zone)
        if t.current_act != expected_act:
            bad.append(f"{zone}: act {t.current_act}, expected {expected_act}")
    check(f"all {len(CAMPAIGN)} zones land in the right act", not bad, "; ".join(bad[:3]))
    check("finishes on Altar of Hunger in act 10", t.current_step.zone == "Altar of Hunger")
    done, total = t.progress()
    check("act 10 progress reads 14/15", (done, total) == (14, 15), f"{done}/{total}")


if __name__ == "__main__":
    test_data()
    test_cold_start()
    test_forward_only()
    test_transitions()
    test_off_route()
    test_back()
    test_flags()
    test_restore()
    test_completion()
    test_campaign()

    failed = _results.count(False)
    print()
    if failed:
        print(f"\033[91m{failed} of {len(_results)} test(s) failed.\033[0m")
    else:
        print(f"\033[92mAll {len(_results)} tests passed.\033[0m")
    raise SystemExit(1 if failed else 0)
