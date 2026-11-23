import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Self

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

SAVE_FILE = Path("TemerevSave.json")

"""Save state data classes"""


@dataclass
class SaveData:
    version: int = 1
    timestamp: str = datetime.now().astimezone().isoformat()
    current_chapter: int = 0
    current_room: str = ""
    inventory: list[str] = field(default_factory=list)
    flags: list[DataFlags] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Room contains characters and props."""
        return {
            "version": self.version,
            "timestamp": datetime.now().astimezone().isoformat(),
            "current_chapter": self.current_chapter,
            "current_room": self.current_room,
            "inventory": self.inventory,
            "flags": self.flags,
        }

    @classmethod
    def from_persistent_storage_desktop(cls) -> Self:
        try:
            with SAVE_FILE.open("r") as player_data_file:
                saved_settings = json.loads(player_data_file.read())
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError:
            return cls()
        else:
            s = saved_settings[0]
            return cls(**s)

    @classmethod
    def from_persistent_storage_emscripten(cls) -> Self:
        player_data = window.localStorage.getItem(SAVE_FILE.stem)  # pyright: ignore[reportAttributeAccessIssue, reportPossiblyUnboundVariable]
        if player_data:
            try:
                saved_player_data = json.loads(player_data)
            except json.JSONDecodeError:
                return cls()
            else:
                return cls(**saved_player_data)
        return cls()

    @classmethod
    def from_persistent_storage(cls) -> Self:
        if sys.platform == "emscripten":
            return cls.from_persistent_storage_emscripten()
        else:
            return cls.from_persistent_storage_desktop()

    def to_persistent_storage_desktop(self) -> None:
        with SAVE_FILE.open("w") as player_data_file:
            json.dump([asdict(self)], player_data_file, indent=4)

    def to_persistent_storage_emscripten(self) -> None:
        window.localStorage.setItem(SAVE_FILE.stem, json.dumps(asdict(self)))  # pyright: ignore[reportAttributeAccessIssue, reportPossiblyUnboundVariable]

    def to_persistent_storage(self) -> None:
        if sys.platform == "emscripten":
            self.to_persistent_storage_emscripten()
        else:
            self.to_persistent_storage_desktop()


@dataclass
class DataFlags:
    flag_name: str
    value: str
