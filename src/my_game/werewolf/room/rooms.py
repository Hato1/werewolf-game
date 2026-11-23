"""Room definitions for the werewolf game."""

from my_game.werewolf.assets import Images
from my_game.werewolf.room import characters, props, regions  # noqa: F401
from my_game.werewolf.room.loaders import CharacterData, NamedPointData, PropData, RegionData, RoomData

TEST_ROOM = RoomData(
    name="Test Room",
    description="A room for testing the room rendering system.",
    props=(
        props.BACKGROUND_INN,
        PropData(
            name="Studio",
            description="a tiny studio model.",
            image=Images.STUDIO,
            position=(401, 38),
            visible=True,
            clickable=True,
            hotspot=None,
            scale=0.025,
            size=None,
            parallax=0.0,
            depth=0,
            baseline=0,
            walk_to_interact=True,
        ),
        PropData(
            name="Prop2",
            description="New prop",
            image=Images.LANTERN_1,
            position=(162, 38),
            visible=True,
            clickable=True,
            hotspot=None,
            scale=1.0,
            size=None,
            parallax=0.0,
            depth=0,
            baseline=0,
            walk_to_interact=False,
        ),
    ),
    hotspots=(),
    characters=(
        CharacterData(
            name="Test Character",
            description="A test character.",
            image=Images.MC_IDLE,
            position=(75, 64),
            walk_image=Images.MC_WALK,
            scale=1,
            size=None,
            speed=200.0,
            depth=0,
            path=(),
            loop=False,
        ),
    ),
    regions=(
        RegionData(
            name="Test Region",
            description="A region for testing purposes.",
            polygon=((10, 10), (100, 10), (100, 100), (10, 100)),
        ),
    ),
    points=(
        NamedPointData(
            name="Test Point",
            description="A test named point.",
            position=(324, 100),
        ),
    ),
    walkable_areas=(),
)

CHURCH_CEMETARY = RoomData(
    name="Church Cemetary Room",
    description="A room set in the church cemetary.",
    props=(props.BACKGROUND_CHURCH_CEMETARY,),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)

INN = RoomData(
    name="Inn Room",
    description="A room set in the inn.",
    props=(props.BACKGROUND_INN, props.GRAVEYARD_CHAINS),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)

TOWN_CENTER = RoomData(
    name="Town Center Room",
    description="A room set in the town center.",
    props=(props.BACKGROUND_TOWN_CENTER,),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)

TOWN_ENTRANCE = RoomData(
    name="Town Entrance Room",
    description="A room set in the town entrance.",
    props=(props.BACKGROUND_TOWN_ENTRANCE,),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)

TOWN_HALL = RoomData(
    name="Town Hall Room",
    description="A room set in the town hall.",
    props=(props.BACKGROUND_TOWN_HALL,),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)

WOODS = RoomData(
    name="Woods Room",
    description="A room set in the woods.",
    props=(props.BACKGROUND_WOODS,),
    hotspots=(),
    characters=(),
    regions=(),
    points=(),
    walkable_areas=(),
)
