"""Serialisable room definitions.

Only plain data lives in the files; textures are referenced by their `Images` enum value (the filename).
"""

from dataclasses import dataclass, field

from my_game.werewolf.assets import Images

Point = tuple[int, int]
Polygon = tuple[Point, ...]


@dataclass(frozen=True)
class CharacterData:
    """Data representation of a character."""

    name: str
    description: str
    image: Images
    position: Point
    walk_image: Images | None = None
    speed: float = 200.0
    path: tuple[Point, ...] = ()
    loop: bool = False


@dataclass(frozen=True)
class HotspotData:
    """Data representation of a hotspot."""

    name: str
    description: str
    polygon: Polygon = field(default_factory=tuple)


@dataclass(frozen=True)
class PropData:
    """Data representation of a prop."""

    name: str
    description: str
    image: Images
    position: Point = (0, 0)
    visible: bool = True
    clickable: bool = True
    hotspot: HotspotData | None = None
    scale: float = 1.0
    size: tuple[int, int] | None = None
    parallax: float = 0.0
    depth: int = 0
    baseline: int = 0


@dataclass(frozen=True)
class RoomData:
    """Data representation of a room."""

    name: str
    description: str
    props: tuple[PropData, ...] = field(default_factory=tuple)
    hotspots: tuple[HotspotData, ...] = field(default_factory=tuple)
    characters: tuple[CharacterData, ...] = field(default_factory=tuple)
    regions: tuple[Polygon, ...] = field(default_factory=tuple)
    points: tuple[Point, ...] = field(default_factory=tuple)
    walkable_areas: tuple[Polygon, ...] = field(default_factory=tuple)
