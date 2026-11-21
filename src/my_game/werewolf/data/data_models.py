from dataclasses import dataclass, field
from datetime import datetime

from my_game.werewolf.room.loaders import CharacterData, RoomData
from my_game.werewolf.room.models import Prop

"""Save state data classes"""


@dataclass
class SaveData:
    version: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    current_chapter: int = 0
    player: CharacterData | None = None
    current_room: RoomData | None = None
    inventory: list[Prop] | None = None
    flags: list[DataFlags] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Room contains characters and props."""
        return {
            "version": self.version,
            "timestamp": datetime.now(datetime.now().astimezone().tzinfo),
            "current_chapter": self.current_chapter,
            "player": self.player,
            "current_room": self.current_room,
            "inventory": self.inventory,
            "points": self.flags,
        }


@dataclass
class DataFlags:
    flag_name: str
    value: str | int | float | bool | object
