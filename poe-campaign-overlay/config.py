import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

SEARCH_PATHS = [
    Path.home() / ".steam/steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".local/share/Steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".wine/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path("C:/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt"),
    Path("C:/Program Files/Grinding Gear Games/Path of Exile/logs/Client.txt"),
]


def find_client_log() -> str | None:
    """Check config.json first, then search known paths. Returns path string or None."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            path = Path(data.get("client_log_path", ""))
            if path.exists():
                return str(path)
        except (json.JSONDecodeError, OSError):
            pass

    for path in SEARCH_PATHS:
        if path.exists():
            return str(path)

    return None


def save_client_log_path(path: str) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump({"client_log_path": path}, f, indent=2)
