import json
from pathlib import Path

from logutil import get_logger

log = get_logger()

CONFIG_FILE = Path(__file__).parent / "config.json"

SEARCH_PATHS = [
    Path.home() / ".steam/steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".local/share/Steam/steamapps/compatdata/238960/pfx/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    Path.home() / ".wine/drive_c/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt",
    # Standalone client (Windows)
    Path("C:/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt"),
    Path("C:/Program Files/Grinding Gear Games/Path of Exile/logs/Client.txt"),
    # Steam client (Windows) — common install roots
    Path("C:/Program Files (x86)/Steam/steamapps/common/Path of Exile/logs/Client.txt"),
    Path("C:/Program Files/Steam/steamapps/common/Path of Exile/logs/Client.txt"),
    Path("D:/Steam/steamapps/common/Path of Exile/logs/Client.txt"),
    Path("D:/SteamLibrary/steamapps/common/Path of Exile/logs/Client.txt"),
]


def find_client_log() -> str | None:
    """Check config.json first, then search known paths. Returns path string or None."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            path = Path(data.get("client_log_path", ""))
            if path.exists():
                log.info("Using saved Client.txt path from config.json: %s", path)
                return str(path)
            log.warning("Saved path in config.json no longer exists: %s", path)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read config.json (%s) — falling back to auto-search.", e)

    for path in SEARCH_PATHS:
        if path.exists():
            log.info("Found Client.txt at: %s", path)
            return str(path)

    log.warning("Client.txt not found in %d known locations — prompting for manual pick.", len(SEARCH_PATHS))
    return None


def save_client_log_path(path: str) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump({"client_log_path": path}, f, indent=2)
    log.info("Saved Client.txt path to config.json: %s", path)
