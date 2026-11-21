import json
import shutil
from pathlib import Path

from platformdirs import user_data_dir

from my_game.werewolf.data.data_models import SaveData

"""Save file versioning so old files can still work if we update the game"""
CURRENT_VERSION = 1


def save_game(path: Path, data: SaveData) -> bool:
    """Save game, but ensure there is a backup in case something goes wrong"""
    try:
        json_str = json.dumps(data, indent=2)
        tmp_path = path.with_suffix(".json.tmp")
        bak_path = path.with_suffix(".json.bak")

        # Write to temp
        tmp_path.write_text(json_str, encoding="utf-8")

        # Backup current save
        if path.exists():
            shutil.copy2(path, bak_path)

        # Atomic replace
        tmp_path.replace(path)
        return True
    except OSError as e:
        print(f"Save failed: {e}")
        return False


def load_game(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        json_str = path.read_text(encoding="utf-8")
        data = json.loads(json_str)
        return migrate_save(data)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Load failed: {e}")
        return None


def migrate_save(data: dict) -> dict:
    data["version"] = CURRENT_VERSION
    return data


def get_save_dir() -> Path:
    save_dir = Path(user_data_dir("BeastOfTemerev", "Gevaudan"))
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def slot_path(slot: int) -> Path:
    return get_save_dir() / f"slot_{slot}.json"


def list_slots(max_slots: int = 3) -> list:
    slots = []
    for i in range(max_slots):
        path = slot_path(i)
        if path.exists():
            data = load_game(path)
            slots.append(
                {
                    "slot": i,
                    "empty": False,
                    "timestamp": data.get("timestamp") if data is not None else None,
                    "chapter": data.get("current_chapter") if data is not None else None,
                }
            )
        else:
            slots.append({"slot": i, "empty": True})
    return slots


def delete_slot(slot: int) -> None:
    path = slot_path(slot)
    path.unlink(missing_ok=True)
    path.with_suffix(".json.bak").unlink(missing_ok=True)
