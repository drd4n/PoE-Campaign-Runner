import json
from pathlib import Path

ZONES_FILE = Path(__file__).parent / "zones.json"
ACT6_TRIGGER = "Lioneye's Watch"  # only advances to act 6 when current_act == 5


def _load() -> dict:
    with open(ZONES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _normalize(name: str) -> str:
    """Strip a leading 'The ' so log names and data keys match regardless of
    the prefix inconsistency (e.g. game emits 'The Imperial Gardens', data
    stores 'Imperial Gardens')."""
    return name[4:] if name.startswith("The ") else name


class ZoneTracker:
    def __init__(self):
        data = _load()
        self._milestones: dict[str, int] = data["milestones"]
        self._zones: dict[str, dict] = data["zones"]
        # Prefix-tolerant lookup tables (see _normalize).
        self._milestones_norm = {_normalize(k): v for k, v in self._milestones.items()}
        self._zones_norm = {_normalize(k): v for k, v in self._zones.items()}
        self.current_act: int = 0

    def _zone_entry(self, zone_name: str) -> dict | None:
        entry = self._zones.get(zone_name)
        if entry is None:
            entry = self._zones_norm.get(_normalize(zone_name))
        return entry

    def enter_zone(self, zone_name: str) -> list[str] | None:
        """Update act tracking and return steps, or None if act is ambiguous/unknown."""
        self._update_act(zone_name)
        return self._resolve_steps(zone_name)

    def get_possible_acts(self, zone_name: str) -> list[int]:
        """Return all acts this zone appears in (empty list = unknown zone)."""
        zone = self._zone_entry(zone_name)
        if not zone:
            return []
        return sorted(int(k) for k in zone.keys())

    def set_act(self, act: int) -> None:
        """Explicitly set the current act (called after player selects from UI)."""
        self.current_act = act

    def resolve_current(self, zone_name: str) -> list[str] | None:
        """Resolve steps for zone_name using the current act (no act update)."""
        return self._resolve_steps(zone_name)

    def _update_act(self, zone_name: str) -> None:
        # Lioneye's Watch is both the Act 1 town and the Act 6 start zone.
        # Only advance to Act 6 if we've already completed Act 5.
        if _normalize(zone_name) == _normalize(ACT6_TRIGGER) and self.current_act == 5:
            self.current_act = 6
            return

        new_act = self._milestones.get(zone_name)
        if new_act is None:
            new_act = self._milestones_norm.get(_normalize(zone_name))
        if new_act is not None and new_act > self.current_act:
            self.current_act = new_act

    def _resolve_steps(self, zone_name: str) -> list[str] | None:
        zone = self._zone_entry(zone_name)
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
