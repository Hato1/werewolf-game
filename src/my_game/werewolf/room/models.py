"""Object representing a room in the game."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar, Self

import pygame as pg

from my_game.constants import SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.logger import get_logger
from my_game.core.renderer import Renderer
from my_game.werewolf.assets import Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.interactions.definitions import InteractionData
from my_game.werewolf.room.loaders import CharacterData, HotspotData, NamedPointData, PropData, RegionData, RoomData

logger = get_logger(__name__)

Point = tuple[int, int]
Polygon = tuple[Point, ...]


def split_frames(sheet: pg.Surface, frame_width: int) -> list[pg.Surface]:
    """Split a horizontal sprite sheet into frames of the given width."""
    width = sheet.get_width()
    return [
        sheet.subsurface(pg.Rect(x, 0, frame_width, sheet.get_height())).copy() for x in range(0, width, frame_width)
    ]


def scale_image(image: pg.Surface, size: tuple[int, int] | None, scale: float) -> pg.Surface:
    if size is not None:
        return pg.transform.smoothscale(image, size)
    elif scale != 1.0:
        return pg.transform.smoothscale_by(image, scale)
    return image


def load_image(image: Images, size: tuple[int, int] | None, scale: float) -> pg.Surface:
    sprite = image.load()
    return scale_image(sprite, size, scale)


def load_spritesheet(image: Images, size: tuple[int, int] | None, scale: float, frame_width: int) -> list[pg.Surface]:
    sheet = image.load()
    frames = split_frames(sheet, frame_width)
    return [scale_image(frame, size, scale) for frame in frames]


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
        walk_to_interact: Whether the player walks up to the prop before its interaction triggers.
        id: Stable identifier for interaction references.
        interactions: Interaction rules attached to this prop.
    """

    name: str
    description: str
    sprite: pg.Surface
    normal_sprite: pg.Surface | None
    position: Point
    visible: bool
    clickable: bool
    hotspot: Hotspot | None
    scale: float
    size: tuple[int, int] | None
    parallax: float
    depth: int
    baseline: int
    walk_to_interact: bool = False
    id: str = ""
    interactions: tuple[InteractionData, ...] = ()

    @classmethod
    def from_prop_data(cls, data: PropData) -> Self:
        sprite = load_image(data.image, data.size, data.scale)
        normal_sprite = load_image(data.normal_image, data.size, data.scale) if data.normal_image else None
        if normal_sprite and sprite.get_size() != normal_sprite.get_size():
            logger.error(
                "Sprite size mismatch.", size=sprite.get_size(), normal_size=normal_sprite.get_size(), sprite=data.name
            )
            raise ValueError("Sprite size does not match normal sprite size (See above log for details).")
        prop = cls(
            data.name,
            data.description,
            sprite,
            normal_sprite,
            data.position,
            data.visible,
            data.clickable,
            Hotspot.from_hotspot_data(data.hotspot) if data.hotspot is not None else None,
            data.scale,
            data.size,
            data.parallax,
            data.depth,
            data.baseline,
            data.walk_to_interact,
            id=data.id,
            interactions=data.interactions,
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
        if self.normal_sprite:
            renderer(self.normal_sprite, rect, to_normal=True)

    def get_inventory_sprite(self) -> pg.Surface:
        """Return the sprite used for the inventory."""
        # TODO: Implement inventory-specific sprite handling if needed.
        return self.sprite


@dataclass
class Character:
    """Character represents an animated entity within the room.

    Characters move according to the direction returned by `get_direction`. By default that
    follows a preprogrammed path; subclasses (such as the player) can override it.

    Attributes:
        name: Character's display name.
        description: Character's description.
        idle_frames: Animation frames shown while standing still.
        walk_frames: Animation frames shown while moving.
        position: Point at the bottom-centre of the character's feet.
        speed: Movement speed in pixels per second.
        path: Waypoints the character walks through in order.
        loop: Whether to restart the path once the last waypoint is reached.
        facing_left: Whether the sprite is mirrored to face left.
        walking: Whether the character moved during the last update.
        id: Stable identifier for interaction references.
        interactions: Interaction rules attached to this character.
    """

    SPEED = 200.0
    FRAME_DURATION = 0.1

    name: str
    description: str
    idle_frames: list[pg.Surface]
    normal_idle_frames: list[pg.Surface] | None
    walk_frames: list[pg.Surface]
    normal_walk_frames: list[pg.Surface] | None
    position: pg.Vector2
    depth: int
    speed: float
    path: tuple[Point, ...]
    loop: bool
    path_index: int = 0
    facing_left: bool = False
    walking: bool = False
    frame_index: int = 0
    frame_time: float = 0.0
    id: str = ""
    interactions: tuple[InteractionData, ...] = ()

    @classmethod
    def from_character_data(cls, data: CharacterData) -> Self:
        # Walk sheets are made of frames the same size as the idle frame.
        frame_width = data.image.load().get_width()
        idle = load_spritesheet(data.image, data.size, data.scale, frame_width)
        normal_idle = (
            load_spritesheet(data.normal_image, data.size, data.scale, frame_width) if data.normal_image else None
        )
        walk = load_spritesheet(data.walk_image, data.size, data.scale, frame_width) if data.walk_image else idle
        normal_walk = (
            load_spritesheet(data.normal_walk_image, data.size, data.scale, frame_width)
            if data.normal_walk_image
            else None
        )

        if normal_idle and idle[0].get_size() != normal_idle[0].get_size():
            logger.error(
                "Idle sprite size mismatch.",
                size=idle[0].get_size(),
                normal_size=normal_idle[0].get_size(),
                sprite=data.name,
            )
            raise ValueError("Idle Sprite size does not match normal sprite size (See above log for details).")
        if normal_walk and walk[0].get_size() != normal_walk[0].get_size():
            logger.error(
                "Walk sprite size mismatch.",
                size=walk[0].get_size(),
                normal_size=normal_walk[0].get_size(),
                sprite=data.name,
            )
            raise ValueError("Walk Sprite size does not match normal sprite size (See above log for details).")

        character = cls(
            data.name,
            data.description,
            idle,
            normal_idle,
            walk,
            normal_walk,
            pg.Vector2(data.position),
            data.depth,
            data.speed,
            data.path,
            loop=data.loop,
            id=data.id,
            interactions=data.interactions,
        )
        return character

    @property
    def frames(self) -> list[pg.Surface]:
        return self.walk_frames if self.walking else self.idle_frames

    def normal_frames(self) -> list[pg.Surface] | None:
        if self.walking:
            return self.normal_walk_frames if self.normal_walk_frames else self.normal_idle_frames
        return self.normal_idle_frames

    @property
    def sprite(self) -> pg.Surface:
        sprite = self.frames[self.frame_index % len(self.frames)]
        return pg.transform.flip(sprite, flip_x=True, flip_y=False) if self.facing_left else sprite

    @property
    def normal_sprite(self) -> pg.Surface | None:
        if frames := self.normal_frames():
            sprite = frames[self.frame_index % len(frames)]
            return pg.transform.flip(sprite, flip_x=True, flip_y=False) if self.facing_left else sprite
        return None

    @property
    def rect(self) -> pg.Rect:
        return self.sprite.get_rect(topleft=(round(self.position.x), round(self.position.y)))

    def get_direction(self, dt: float, input_state: InputState) -> pg.Vector2:
        """Return this frame's movement as a vector of length at most 1 (a fraction of full speed).

        The default behaviour walks along `path`, scaling the final step so the character lands
        exactly on each waypoint.
        """
        if self.path_index >= len(self.path):
            if not (self.loop and self.path):
                return pg.Vector2()
            self.path_index = 0
        delta = pg.Vector2(self.path[self.path_index]) - self.position
        step = self.speed * dt
        if delta.length() <= step:
            self.path_index += 1
            return delta / step if step else pg.Vector2()
        return delta.normalize()

    def update(self, dt: float, input_state: InputState) -> None:
        direction = self.get_direction(dt, input_state)
        was_walking = self.walking
        self.walking = direction.length_squared() > 0
        if self.walking != was_walking:
            self.frame_index = 0
            self.frame_time = 0.0

        if self.walking:
            self.position += direction * self.speed * dt
            if direction.x:
                self.facing_left = direction.x < 0
            self.position.x = min(max(self.position.x, 0), SCREEN_SIZE[0])
            self.position.y = min(max(self.position.y, 0), SCREEN_SIZE[1])

        self.frame_time += dt
        while self.frame_time >= self.FRAME_DURATION:
            self.frame_time -= self.FRAME_DURATION
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def draw(self, renderer: Renderer) -> None:
        """Draw the character in the room."""
        renderer(self.sprite, self.rect)
        if self.normal_sprite:
            renderer(self.normal_sprite, self.rect, to_normal=True)


@dataclass
class Player(Character):
    """A character whose movement is driven by player input.

    The player can also be sent to walk up to a target rect, calling `on_arrive` once within
    `INTERACT_DISTANCE` of it. Any directional input cancels the walk.
    """

    # How close (in pixels) the player's feet get to a target before stopping.
    INTERACT_DISTANCE: ClassVar[int] = 20

    target: pg.Rect | None = None
    on_arrive: Callable[[], None] | None = None

    def walk_to(self, target: pg.Rect, on_arrive: Callable[[], None]) -> None:
        """Walk towards the target rect, then call `on_arrive`."""
        self.target = target
        self.on_arrive = on_arrive

    def cancel_walk(self) -> None:
        self.target = None
        self.on_arrive = None

    def vector_to_target(self) -> pg.Vector2:
        """Return the vector from the player's feet to the nearest point on the target."""
        if self.target is None:
            return pg.Vector2()
        nearest = pg.Vector2(
            min(max(self.position.x, self.target.left), self.target.right),
            min(max(self.position.y, self.target.top), self.target.bottom),
        )
        return nearest - self.position

    def get_direction(self, dt: float, input_state: InputState) -> pg.Vector2:
        direction = pg.Vector2(
            (Action.RIGHT in input_state) - (Action.LEFT in input_state),
            (Action.DOWN in input_state) - (Action.UP in input_state),
        )
        if direction:
            self.cancel_walk()
            return direction.normalize()
        to_target = self.vector_to_target()
        if self.target is None or to_target.length() <= self.INTERACT_DISTANCE:
            return pg.Vector2()
        return to_target.normalize()

    def update(self, dt: float, input_state: InputState) -> None:
        super().update(dt, input_state)
        if self.target is not None and self.vector_to_target().length() <= self.INTERACT_DISTANCE:
            on_arrive = self.on_arrive
            self.cancel_walk()
            if on_arrive is not None:
                on_arrive()


@dataclass
class Hotspot:
    """Hotspot represents an interactive area within a room.

    Attributes:
        name: Hotspot's display name.
        description: Hotspot's description.
        polygon: List of coordinate tuples defining the hotspot's shape.
        id: Stable identifier for interaction references.
        interactions: Interaction rules attached to this hotspot.
    """

    name: str
    description: str
    polygon: Polygon
    id: str = ""
    interactions: tuple[InteractionData, ...] = ()

    @classmethod
    def from_hotspot_data(cls, data: HotspotData) -> Self:
        hotspot = cls(data.name, data.description, data.polygon, id=data.id, interactions=data.interactions)
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
        description: Region's description.
        polygon: List of coordinate tuples defining the region's shape.
        id: Stable identifier for interaction references.
        interactions: Interaction rules attached to this region.
    """

    name: str
    description: str = ""
    polygon: Polygon = ()
    id: str = ""
    interactions: tuple[InteractionData, ...] = ()

    def enter(self):
        """Called when the player enters the region."""
        pass

    def exit(self):
        """Called when the player exits the region."""
        pass

    def contains_point(self, point: Point) -> bool:
        """Check if the given point is within the region."""
        raise NotImplementedError

    @classmethod
    def from_region_data(cls, data: RegionData) -> Self:
        region = cls(
            data.name,
            data.description,
            data.polygon,
            id=data.id,
            interactions=data.interactions,
        )
        return region


@dataclass(frozen=True)
class NamedPoint:
    """A named location in a room.

    Attributes:
        name: Point's display name.
        description: Point's description.
        position: Coordinates of the point.
        id: Stable identifier for interaction references.
        interactions: Interaction rules attached to this point.
    """

    name: str
    description: str = ""
    position: tuple[int, int] = (0, 0)
    id: str = ""
    interactions: tuple[InteractionData, ...] = ()

    @classmethod
    def from_point_data(cls, data: NamedPointData) -> Self:
        return cls(
            data.name,
            data.description,
            data.position,
            id=data.id,
            interactions=data.interactions,
        )


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

    registry: ClassVar[dict[RoomData, Self]] = {}

    name: str
    description: str
    props: list[Prop] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    hotspots: list[Hotspot] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    points: list[NamedPoint] = field(default_factory=list)
    walkable_areas: list[Polygon] = field(default_factory=list)

    @classmethod
    def from_room_data(cls, data: RoomData, *, overwrite=False) -> Self:
        if data in cls.registry and not overwrite:
            return cls.registry[data]
        room = cls(
            name=data.name,
            description=data.description,
            props=[Prop.from_prop_data(prop) for prop in data.props],
            characters=[Character.from_character_data(ch) for ch in data.characters],
            hotspots=[Hotspot.from_hotspot_data(hs) for hs in data.hotspots],
            regions=[Region.from_region_data(r) for r in data.regions],
            points=[NamedPoint.from_point_data(p) for p in data.points],
            walkable_areas=list(data.walkable_areas),
        )
        cls.registry[data] = room
        return room

    def update(self, dt: float, input_state: InputState) -> None:
        """Advance the room's characters."""
        for character in self.characters:
            character.update(dt, input_state)

    def draw(self, renderer: Renderer) -> None:
        """Draw the room and its contents."""

        prop_and_character: list[Prop | Character] = [*self.props, *self.characters]
        for sorted_prop_and_character in sorted(prop_and_character, key=lambda p: p.depth, reverse=True):
            sorted_prop_and_character.draw(renderer)

    def get_clicked(self, point: Point) -> Prop | Character | None:
        """Return the topmost clickable object at the given point."""
        clickable_objects: list[Prop | Character] = [*self.props, *self.characters]
        for object in clickable_objects:
            if (
                getattr(object, "clickable", True)
                and getattr(object, "visible", True)
                and object.rect.collidepoint(point)
            ):
                return object
        return None

    def on_enter(self, renderer: Renderer) -> None:
        """Hook for when the player enters the room."""
        pass

    def on_exit(self, renderer: Renderer) -> None:
        """Hook for when the player exits the room."""
        pass
