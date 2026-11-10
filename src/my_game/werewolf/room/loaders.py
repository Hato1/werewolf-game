"""Serialisable room definitions.

Only plain data lives in the files; textures are referenced by their `Images` enum value (the filename).
"""

from dataclasses import dataclass, field

from my_game.werewolf.assets import Images

Point = tuple[int, int]
Polygon = list[Point]


@dataclass
class CharacterData:
    """Data representation of a character."""

    name: str
    description: str
    image: Images
    position: Point


@dataclass
class HotspotData:
    """Data representation of a hotspot."""

    name: str
    description: str
    polygon: Polygon = field(default_factory=list)


@dataclass
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


@dataclass
class RoomData:
    """Data representation of a room."""

    name: str
    description: str
    props: list[PropData] = field(default_factory=list)
    hotspots: list[HotspotData] = field(default_factory=list)
    characters: list[CharacterData] = field(default_factory=list)
    regions: list[Polygon] = field(default_factory=list)
    points: list[Point] = field(default_factory=list)
    walkable_areas: list[Polygon] = field(default_factory=list)
