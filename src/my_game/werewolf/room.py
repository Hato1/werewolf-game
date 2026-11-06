"""Object representing a room in the game."""

Point = tuple[int, int]
polygon = list[Point]


class Character:
    """Character represents an entity within the room that the player can converse with.

    # TODO: Add dialogue and interaction methods for the character.
    """

    def __init__(self, name: str, sprite, point: Point) -> None:
        self.name = name
        self.sprite = sprite
        self.position: Point = point

    def draw(self):
        """Draw the character in the room."""
        # Drawing logic goes here.
        pass


class Hotspot:
    """Hotspot represents an interactive area within a room."""

    def __init__(self, name: str, polygon: polygon) -> None:
        self.name = name
        self.polygon = polygon

    def look(self):
        """Called when the player uses the 'look' verb on the hotspot."""
        pass

    def use(self):
        """Called when the player uses the 'use' verb on the hotspot."""
        pass

    def contains_point(self, point: Point) -> bool:
        raise NotImplementedError


class Region:
    """Region represents a distinct area within a room that may have specific properties or rules."""

    def __init__(self, name: str, polygon: polygon) -> None:
        self.name = name
        self.polygon = polygon

    def enter(self):
        """Called when the player enters the region."""
        pass

    def exit(self):
        """Called when the player exits the region."""
        pass

    def contains_point(self, point: Point) -> bool:
        """Check if the given point is within the region."""
        raise NotImplementedError


class Prop:
    """Props are objects within a room that the player can interact with."""

    def __init__(self, name: str, description: str, sprite) -> None:
        self.name = name
        self.description = description
        self.sprite = sprite
        # Hotspot coordinates within the prop that the player can interact with.
        # This does not currently support 'donut' shapes.
        # Use None to default sprite to hotspot.
        self.hotspot: Hotspot | None = None
        self.visible = True
        self.clickable = True
        self.position: Point = (0, 0)

        self.parallax: float = 0
        # Baseline represents the reference point for the prop's position relative to its sprite.
        # This will determine the order in which props are rendered relative to each other.
        self.height: int = 0

    def hide(self):
        """Hide the prop from the room."""
        self.visible = False
        self.clickable = False

    def draw(self):
        """Draw the prop in the room."""
        if not self.visible:
            return
        # Drawing logic goes here.
        pass


class Room:
    """Room represents a location in the game that contains props the player can interact with."""

    def __init__(
        self, name: str, description: str, props: list[Prop], regions: list[polygon], hotspots: list[Hotspot]
    ) -> None:
        self.name = name
        self.description = description

        # Hotspots are interactive areas within the room.
        self.hotspots: list[Hotspot] = hotspots
        # Props are objects within the room. This includes the background.
        self.props: list[Prop] = props
        # Regions are distinct areas within the room that may have specific properties or rules.
        self.regions: list[polygon] = regions
        # Points are specific coordinates within the room that may be of interest or have special significance.
        # EG: The player's spawn point.
        self.points: list[Point] = []
        # Characters are entities within the room that the player can converse with.
        self.characters: list[Character] = []

        # Walkable areas are regions within the room where the player can move freely.
        # It's defined as a list of polygons, where each polygon is represented as a list of coordinate tuples.
        self.walkable_areas: list[polygon] = []

    def draw(self):
        """Draw the room and its contents."""
        for prop in sorted(self.props, key=lambda p: p.height):
            prop.draw()

        for character in self.characters:
            character.draw()
