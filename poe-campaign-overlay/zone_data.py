import json
from pathlib import Path

ZONES_FILE = Path(__file__).parent / "zones.json"
ACT6_TRIGGER = "Lioneye's Watch"  # only advances to act 6 when current_act == 5


def _load() -> dict:
    with open(ZONES_FILE, encoding="utf-8") as f:
        return json.load(f)


class ZoneTracker:
    def __init__(self):
        data = _load()
        self._milestones: dict[str, int] = data["milestones"]
        self._zones: dict[str, dict] = data["zones"]
        self.current_act: int = 0

    def enter_zone(self, zone_name: str) -> list[str] | None:
        """Update act tracking and return steps for this zone, or None if unknown."""
        self._update_act(zone_name)
        return self._resolve_steps(zone_name)

    def _update_act(self, zone_name: str) -> None:
        # Lioneye's Watch is both the Act 1 town and the Act 6 start zone.
        # Only advance to Act 6 if we've already completed Act 5.
        if zone_name == ACT6_TRIGGER and self.current_act == 5:
            self.current_act = 6
            return

        new_act = self._milestones.get(zone_name)
        if new_act is not None and new_act > self.current_act:
            self.current_act = new_act

    def _resolve_steps(self, zone_name: str) -> list[str] | None:
        zone = self._zones.get(zone_name)
        if not zone:
            return None

        # Try exact act match first
        entry = zone.get(str(self.current_act))

        # Fallback: zone only exists in one act (no ambiguity)
        if entry is None and len(zone) == 1:
            entry = next(iter(zone.values()))

        if entry is None:
            return None

        return entry.get("steps", [])
