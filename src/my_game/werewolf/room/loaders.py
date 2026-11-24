"""Serialisable room definitions.

Only plain data lives in the files; textures are referenced by their `Images` enum value (the filename).
"""

from dataclasses import dataclass, field

from my_game.werewolf.assets import Images
from my_game.werewolf.interactions.definitions import InteractionData

Point = tuple[int, int]
Polygon = tuple[Point, ...]


@dataclass(frozen=True)
class CharacterData:
    """Data representation of a character."""

    id: str
    description: str
    image: Images
    # Normal image for lighting engine.
    normal_image: Images | None = None
    position: Point = (0, 0)
    walk_image: Images | None = None
    normal_walk_image: Images | None = None
    scale: float = 1.0
    size: tuple[int, int] | None = None
    speed: float = 200.0
    depth: int = 0
    path: tuple[Point, ...] = ()
    loop: bool = False
    clickable: bool = True
    interactions: tuple[InteractionData, ...] = ()


@dataclass(frozen=True)
class PropData:
    """Data representation of a prop."""

    id: str
    description: str
    image: Images
    # Normal image for lighting engine.
    normal_image: Images | None = None
    position: Point = (0, 0)
    visible: bool = True
    clickable: bool = True
    clickable_area: Polygon | None = None
    scale: float = 1.0
    size: tuple[int, int] | None = None
    parallax: float = 0.0
    depth: int = 0
    baseline: int = 0
    walk_to_interact: bool = False
    interactions: tuple[InteractionData, ...] = ()


@dataclass(frozen=True)
class RegionData:
    """Data representation of a region."""

    id: str
    description: str
    polygon: Polygon = field(default_factory=tuple)
    depth: int = 0
    clickable: bool = True
    interactions: tuple[InteractionData, ...] = ()


@dataclass(frozen=True)
class NamedPointData:
    """Data representation of a point."""

    id: str
    description: str
    position: Point
    interactions: tuple[InteractionData, ...] = ()
    light_index : int = -1# index of the light -1 to disable, 0-5 are valid
    light_z_position: float = 1.0# z coord if there's depth. leave at 1 if no depth
    light_color: tuple[float, float, float] = (1.0, 0.7, 0.1)# color
    light_intensity: float = 1 # color multiplier
    light_flicker_intensity: float = 0.1 # from 0 - 1. higher flickers more strongly
    light_radius : float = 0.5#in screen space


@dataclass(frozen=True)
class RoomData:
    """Data representation of a room."""

    id: str
    description: str
    props: tuple[PropData, ...] = field(default_factory=tuple)
    characters: tuple[CharacterData, ...] = field(default_factory=tuple)
    regions: tuple[RegionData, ...] = field(default_factory=tuple)
    points: tuple[NamedPointData, ...] = field(default_factory=tuple)
    walkable_areas: tuple[Polygon, ...] = field(default_factory=tuple)
