"""Act-based guidance: a per-act checklist with a forward-only position pointer.

Where ZoneTracker answers "what do I do in this zone?", ActTracker answers
"where am I in this act?" — the whole act is on screen and zone changes only
move a pointer through it.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ACTS_FILE = Path(__file__).parent / "acts.json"


def _normalize(name: str) -> str:
    """Strip a leading 'The ' so log names and data keys match regardless of
    the prefix inconsistency (same rule as zone_data)."""
    return name[4:] if name.startswith("The ") else name


@dataclass(frozen=True)
class Step:
    zone: str
    short: str
    bullets: tuple[str, ...]
    per_league: frozenset = field(default_factory=frozenset)
    optional: bool = False

    @property
    def key(self) -> str:
        return _normalize(self.zone)


@dataclass(frozen=True)
class Update:
    """What a zone entry did to the pointer.

    moved     — pointer is on a new step
    held      — pointer unchanged (zone is behind us, or part of the current step)
    ambiguous — the zone belongs to several acts; ask the player which
    unknown   — the zone appears in no act at all
    """

    kind: str
    acts: tuple[int, ...] = ()


class ActTracker:
    def __init__(self, acts_file: Path = ACTS_FILE):
        data = json.loads(Path(acts_file).read_text(encoding="utf-8"))
        self._acts: dict[int, list[Step]] = {}
        for act, body in data["acts"].items():
            self._acts[int(act)] = [
                Step(
                    zone=s["zone"],
                    short=s["short"],
                    bullets=tuple(s["steps"]),
                    per_league=frozenset(s.get("per_league", ())),
                    optional=s.get("optional", False),
                )
                for s in body["steps"]
            ]

        self._by_zone: dict[str, list[tuple[int, int]]] = {}
        for act, steps in self._acts.items():
            for i, step in enumerate(steps):
                self._by_zone.setdefault(step.key, []).append((act, i))

        self.current_act: int = 0
        self.pointer: int = 0
        self.off_route: bool = False
        self.completed: bool = False
        self._last_zone: str | None = None

    # --- state ------------------------------------------------------------

    @property
    def steps(self) -> list[Step]:
        return self._acts.get(self.current_act, [])

    @property
    def current_step(self) -> Step | None:
        steps = self.steps
        return steps[self.pointer] if 0 <= self.pointer < len(steps) else None

    @property
    def finished(self) -> bool:
        """Kitava is dead and the player has moved on. Sticky: leaving the
        final step for a zone it doesn't mention ends the campaign, and only
        the back button resumes tracking."""
        return self.completed

    def _on_final_step(self) -> bool:
        return (
            self.current_act == max(self._acts)
            and self.pointer == len(self.steps) - 1
        )

    def progress(self) -> tuple[int, int]:
        """(done, total) counting mandatory steps only — optional detours don't
        inflate the denominator."""
        steps = self.steps
        total = sum(1 for s in steps if not s.optional)
        done = sum(1 for s in steps[: self.pointer] if not s.optional)
        return done, total

    def restore(self, act: int, step: int) -> bool:
        """Reapply a saved position. Returns False if it doesn't fit the data."""
        if act not in self._acts or not 0 <= step < len(self._acts[act]):
            return False
        self.current_act = act
        self.pointer = step
        self.off_route = False
        self._last_zone = None
        return True

    def possible_acts(self, zone_name: str) -> list[int]:
        return sorted({a for a, _ in self._by_zone.get(_normalize(zone_name), [])})

    # --- movement ---------------------------------------------------------

    def enter_zone(self, zone_name: str) -> Update:
        key = _normalize(zone_name)
        try:
            if self.completed:
                return Update("held")
            if self._on_final_step() and not self._belongs_to_current_step(key):
                # Kitava is down and the player has left for maps or levelling.
                self.completed = True
                return Update("held")
            if self.current_act:
                return self._advance_within_act(key)
            return self._pick_act(key, require_act_start=False)
        finally:
            self._last_zone = key

    def _belongs_to_current_step(self, key: str) -> bool:
        step = self.current_step
        return step is not None and (step.key == key or any(key in b for b in step.bullets))

    def _advance_within_act(self, key: str) -> Update:
        idx = self._scan_forward(key)
        if idx is None:
            # Plenty of zones are only named inside a step's instructions rather
            # than heading one of their own — Act 1's Mud Flats and Tidal Island
            # both live inside Coast steps. Follow the text to the step that
            # sends you there.
            idx = self._scan_forward_bullets(key)
        if idx is not None:
            moved = idx != self.pointer
            self.pointer = idx
            self.off_route = False
            return Update("moved" if moved else "held")

        if any(s.key == key for s in self.steps):
            # Backtracking to a zone we've already passed.
            self.off_route = True
            return Update("held")

        # Not this act's zone at all — a genuine act transition looks like this.
        switched = self._pick_act(key, require_act_start=True)
        if switched.kind != "held":
            return switched

        self.off_route = True
        return Update("held")

    def _scan_forward(self, key: str) -> int | None:
        """First step at or after the pointer whose zone matches.

        Re-entering the zone the pointer already sits on means the player left
        and came back, so that step is done — start looking at the next one.
        This is what separates consecutive same-zone steps (Act 1 visits The
        Coast twice in a row).
        """
        start = self.pointer
        step = self.current_step
        if step is not None and step.key == key and self._last_zone not in (None, key):
            start = self.pointer + 1
        for i in range(start, len(self.steps)):
            if self.steps[i].key == key:
                return i
        return None

    def _scan_forward_bullets(self, key: str) -> int | None:
        """First step at or after the pointer whose instructions name this zone."""
        pattern = re.compile(rf"\b{re.escape(key)}\b")
        for i in range(self.pointer, len(self.steps)):
            if any(pattern.search(b) for b in self.steps[i].bullets):
                return i
        return None

    def _pick_act(self, key: str, require_act_start: bool) -> Update:
        """Choose an act for a zone we can't place in the current one.

        Mid-campaign we only switch on a zone that *starts* another act,
        otherwise a zone visited inside a step (Act 6's Tidal Island while
        we're in Act 1) would yank the player into the wrong act. At cold
        start there is no act to protect, so any position is fair game.
        """
        matches = [
            (act, i)
            for act, i in self._by_zone.get(key, [])
            if act != self.current_act and (i == 0 or not require_act_start)
        ]
        if not matches:
            return Update("held" if self.current_act else "unknown")

        candidates = sorted({act for act, _ in matches})
        if self.current_act + 1 in candidates:
            chosen = self.current_act + 1
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            return Update("ambiguous", tuple(candidates))

        self._enter_act(chosen, key)
        return Update("moved")

    def set_act(self, act: int, zone_name: str | None = None) -> None:
        """Called after the player picks an act from the overlay."""
        self._enter_act(act, _normalize(zone_name) if zone_name else None)

    def _enter_act(self, act: int, key: str | None) -> None:
        self.current_act = act
        self.pointer = 0
        self.off_route = False
        if key:
            for i, step in enumerate(self._acts[act]):
                if step.key == key:
                    self.pointer = i
                    break

    def forward(self) -> bool:
        """Step the pointer on one, rolling into the next act past the last step.

        Needed where two steps in a row share a zone (Act 2's Western Forest,
        Act 6's Prisoner's Gate): with no zone change between them, nothing in
        the log says the first one is done.
        """
        self.off_route = False
        self._last_zone = None
        if self.completed or not self.current_act:
            return False
        if self.pointer < len(self.steps) - 1:
            self.pointer += 1
            return True
        if self.current_act < max(self._acts):
            self.current_act += 1
            self.pointer = 0
            return True
        self.completed = True  # past the last step of Act 10
        return True

    def back(self) -> bool:
        """Step the pointer back one, rolling into the previous act at step 1."""
        self.off_route = False
        self._last_zone = None
        if self.completed:
            # Resume tracking where the campaign left off.
            self.completed = False
            return True
        if self.pointer > 0:
            self.pointer -= 1
            return True
        if self.current_act > min(self._acts):
            self.current_act -= 1
            self.pointer = len(self.steps) - 1
            return True
        return False
