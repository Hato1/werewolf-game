"""Object representing a room in the game."""

from dataclasses import dataclass, field
from typing import Self

import pygame as pg

from my_game.core.renderer import Renderer
from my_game.werewolf.room.loaders import CharacterData, HotspotData, PropData, RoomData

Point = tuple[int, int]
Polygon = list[Point]


@dataclass
class Character:
    """Character represents an entity within the room that the player can converse with.

    Attributes:
        name: Character's display name.
        description: Character's description.
        sprite: Pygame surface containing the character's visual representation.
        position: Top-left coordinate of the character's sprite.
    """

    name: str
    description: str
    sprite: pg.Surface
    position: Point

    @classmethod
    def from_character_data(cls, data: CharacterData) -> Self:
        character = cls(data.name, data.description, data.image.load(), data.position)
        return character

    def draw(self, renderer: Renderer) -> None:
        """Draw the character in the room."""
        rect = self.sprite.get_rect(topleft=self.position)
        renderer(self.sprite, rect)


@dataclass
class Hotspot:
    """Hotspot represents an interactive area within a room.

    Attributes:
        name: Hotspot's display name.
        description: Hotspot's description.
        polygon: List of coordinate tuples defining the hotspot's shape.
    """

    name: str
    description: str
    polygon: Polygon

    @classmethod
    def from_hotspot_data(cls, data: HotspotData) -> Self:
        hotspot = cls(data.name, data.description, data.polygon)
        return hotspot

    def look(self):
        """Called when the player uses the 'look' verb on the hotspot."""
        pass

    def use(self):
        """Called when the player uses the 'use' verb on the hotspot."""
        pass

    def contains_point(self, point: Point) -> bool:
        """Check if the given point is within the hotspot."""
        raise NotImplementedError


@dataclass
class Region:
    """Region represents a distinct area within a room that may have specific properties or rules.

    Attributes:
        name: Region's display name.
        polygon: List of coordinate tuples defining the region's shape.
    """

    name: str
    polygon: Polygon

    def enter(self):
        """Called when the player enters the region."""
        pass

    def exit(self):
        """Called when the player exits the region."""
        pass

    def contains_point(self, point: Point) -> bool:
        """Check if the given point is within the region."""
        raise NotImplementedError


@dataclass
class Prop:
    """Props are objects within a room that the player can interact with.

    Attributes:
        name: Prop's display name.
        description: Prop's description.
        sprite: Pygame surface containing the prop's visual representation.
        position: Top-left coordinate of the prop's sprite.
        visible: Whether the prop is drawn.
        clickable: Whether the prop can be interacted with.
        hotspot: Optional interactive area within the prop.
        scale: Uniform scale factor applied to the image (ignored when size is set).
        size: Exact pixel size to stretch the image to.
        parallax: Parallax effect factor.
        depth: Rendering depth (higher values render on top).
        baseline: Reference point for prop positioning relative to its sprite.
    """

    name: str
    description: str
    sprite: pg.Surface
    position: Point
    visible: bool
    clickable: bool
    hotspot: Hotspot | None
    scale: float
    size: tuple[int, int] | None
    parallax: float
    depth: int
    baseline: int

    @classmethod
    def from_prop_data(cls, data: PropData) -> Self:
        sprite = data.image.load()
        if data.size is not None:
            sprite = pg.transform.smoothscale(sprite, data.size)
        elif data.scale != 1.0:
            sprite = pg.transform.smoothscale_by(sprite, data.scale)
        prop = cls(
            data.name,
            data.description,
            sprite,
            data.position,
            data.visible,
            data.clickable,
            Hotspot.from_hotspot_data(data.hotspot) if data.hotspot is not None else None,
            data.scale,
            data.size,
            data.parallax,
            data.depth,
            data.baseline,
        )
        return prop

    @property
    def rect(self) -> pg.Rect:
        return self.sprite.get_rect(topleft=self.position)

    def hide(self):
        """Hide the prop from the room."""
        self.visible = False
        self.clickable = False

    def draw(self, renderer: Renderer) -> None:
        """Draw the prop in the room."""
        if not self.visible:
            return
        rect = self.sprite.get_rect(topleft=self.position)
        renderer(self.sprite, rect)


@dataclass
class Room:
    """Room represents a location in the game that contains props the player can interact with.

    Attributes:
        name: Room's display name.
        description: Room's description.
        props: Objects within the room, including the background.
        hotspots: Interactive areas within the room.
        characters: Entities within the room that the player can converse with.
        regions: Distinct areas within the room with specific properties or rules.
        points: Specific coordinates within the room of interest.
        walkable_areas: Regions where the player can move freely.
    """

    name: str
    description: str
    props: list[Prop] = field(default_factory=list)
    hotspots: list[Hotspot] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    regions: list[Polygon] = field(default_factory=list)
    points: list[Point] = field(default_factory=list)
    walkable_areas: list[Polygon] = field(default_factory=list)

    @classmethod
    def from_room_data(cls, data: RoomData) -> Self:
        return cls(
            name=data.name,
            description=data.description,
            props=[Prop.from_prop_data(prop) for prop in data.props],
            hotspots=[Hotspot.from_hotspot_data(hs) for hs in data.hotspots],
            characters=[Character.from_character_data(ch) for ch in data.characters],
            regions=data.regions,
            points=data.points,
            walkable_areas=data.walkable_areas,
        )

    def draw(self, renderer: Renderer) -> None:
        """Draw the room and its contents."""
        for prop in sorted(self.props, key=lambda p: p.depth, reverse=True):
            prop.draw(renderer)

        for character in self.characters:
            character.draw(renderer)

    def get_clicked_prop(self, point: Point) -> Prop | None:
        """Return the topmost visible, clickable prop at the given point."""
        for prop in sorted(self.props, key=lambda p: p.depth, reverse=True):
            if prop.visible and prop.clickable and prop.rect.collidepoint(point):
                return prop
        return None
