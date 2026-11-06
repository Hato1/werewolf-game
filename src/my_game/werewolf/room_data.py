"""Serialisable room definitions, and the code that turns them into live Room objects.

The dataclasses here are the file format shared with the level editor: the editor reads and
writes them with `room_from_json` / `room_to_json`, and the game calls `build_room`.
Only plain data lives in the files; textures are referenced by their `Images` enum value (the filename).
"""

import json
from dataclasses import asdict, dataclass, field, fields

import pygame as pg

from my_game.werewolf.assets import Images, Rooms
from my_game.werewolf.room import Prop, Room


@dataclass
class PropData:
    name: str
    description: str
    image: Images
    position: tuple[int, int] = (0, 0)
    # Uniform scale applied to the image. Ignored when `size` is set.
    scale: float = 1.0
    # Exact pixel size to stretch the image to.
    size: tuple[int, int] | None = None
    height: int = 0
    parallax: float = 0.0
    visible: bool = True
    clickable: bool = True


@dataclass
class RoomData:
    name: str
    description: str
    props: list[PropData] = field(default_factory=list)


def _from_dict[T](cls: type[T], data: dict, context: str) -> T:
    known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
    unknown = data.keys() - known
    if unknown:
        raise ValueError(f"Unknown {context} keys: {sorted(unknown)}")
    return cls(**data)


def room_from_json(text: str) -> RoomData:
    """Parse a room definition. Raises ValueError for malformed or unrecognised data."""
    raw = json.loads(text)
    props = [_from_dict(PropData, prop, "prop") for prop in raw.pop("props", [])]
    for prop in props:
        prop.image = Images(prop.image)
        prop.position = tuple(prop.position)  # type: ignore[assignment]
        if prop.size is not None:
            prop.size = tuple(prop.size)  # type: ignore[assignment]
    room = _from_dict(RoomData, {**raw, "props": props}, "room")
    return room


def room_to_json(room: RoomData) -> str:
    return json.dumps(asdict(room), indent=2) + "\n"


def build_prop(data: PropData) -> Prop:
    sprite = data.image.load()
    if data.size is not None:
        sprite = pg.transform.smoothscale(sprite, data.size)
    elif data.scale != 1.0:
        sprite = pg.transform.smoothscale_by(sprite, data.scale)

    prop = Prop(data.name, data.description, sprite)
    prop.position = data.position
    prop.height = data.height
    prop.parallax = data.parallax
    prop.visible = data.visible
    prop.clickable = data.clickable
    return prop


def build_room(data: RoomData) -> Room:
    props = [build_prop(prop) for prop in data.props]
    return Room(data.name, data.description, props, [], [])


def load_room(source: Rooms) -> Room:
    return build_room(room_from_json(source.load()))
