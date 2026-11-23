import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from my_game.werewolf.data.data_models import DataFlags, SaveData

"""Save file versioning so old files can still work if we update the game"""
CURRENT_VERSION = 1
SAVE_FILE = Path("TemerevSave.json")


class SaveFile:
    instance = None
    current_room: str
    inventory: list[str]
    flags: list[DataFlags]
    save_data: SaveData

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.save_data = SaveData.from_persistent_storage()
        return cls.instance

    def __init__(self):
        self.inventory: list[str] = []
        self.flags: list[DataFlags] = []

    @staticmethod
    def get_save_dir() -> Path:
        save_dir = Path(user_data_dir("BeastOfTemerev", "Gevaudan"))
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    def save_game(self) -> None:
        path = SAVE_FILE
        self.save_data.version = CURRENT_VERSION
        self.save_data.timestamp = datetime.now().astimezone().isoformat()
        self.save_data.current_chapter = 1
        self.save_data.inventory = self.inventory
        self.save_data.flags = self.flags

        """Save game, but ensure there is a backup in case something goes wrong"""
        try:
            if path.exists():
                self.save_data.to_persistent_storage()
        except OSError as e:
            print(f"Save operation failed: {e}")

    def load_game(self) -> None:
        print("Loading game...")
        path = SAVE_FILE
        if not path.exists():
            return
        try:
            self.save_data = SaveData.from_persistent_storage()
            self.inventory = self.save_data.inventory
            self.flags = self.save_data.flags

        except (json.JSONDecodeError, OSError) as e:
            print(f"Load failed: {e}")

    def update_room(self, room_name: str):
        self.save_data.current_room = room_name

    def update_chapter(self, chapter: int):
        self.save_data.current_chapter = chapter

    def update_inventory(self, inventory: list[str]):
        self.save_data.inventory = inventory

    @staticmethod
    def migrate_save(data: dict) -> dict:
        data["version"] = CURRENT_VERSION
        return data

    @staticmethod
    def to_json(collection: list[Any]) -> str:
        return json.dumps([asdict(item) for item in collection])

    @staticmethod
    def from_json(json_data: str, obj_type: Any) -> Any:
        return [obj_type(**item) for item in json.loads(json_data)]

    """Save slots not currently supported"""
    # def slot_path(slot: int) -> Path:
    #     return get_save_dir() / f"slot_{slot}.json"

    # def list_slots(self, max_slots: int = 3) -> list:
    #     slots = []
    #     for i in range(max_slots):
    #         path = slot_path(i)
    #         if path.exists():
    #             data = self.load_game(path)
    #             slots.append(
    #                 {
    #                     "slot": i,
    #                     "empty": False,
    #                     "timestamp": data.get("timestamp") if data is not None else None,
    #                     "chapter": data.get("current_chapter") if data is not None else 0,
    #                 }
    #             )
    #         else:
    #             slots.append({"slot": i, "empty": True})
    #     return slots

    # @staticmethod
    # def delete_slot(slot: int) -> None:
    #     path = slot_path(slot)
    #     path.unlink(missing_ok=True)
    #     path.with_suffix(".json.bak").unlink(missing_ok=True)
