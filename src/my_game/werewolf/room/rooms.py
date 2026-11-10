"""Room definitions for the werewolf game."""

from my_game.werewolf.room import props
from my_game.werewolf.room.loaders import RoomData

TEST_ROOM = RoomData(
    name="Test Room",
    description="A room for testing the room rendering system.",
    props=(props.BACKGROUND, props.STUDIO),
)

CHURCH_CEMETARY = RoomData(
    name="Church Cemetary Room",
    description="A room set in the church cemetary.",
    props=(props.BACKGROUND_CHURCH_CEMETARY,),
)

INN = RoomData(
    name="Inn Room",
    description="A room set in the inn.",
    props=(props.BACKGROUND_INN,),
)

TOWN_CENTER = RoomData(
    name="Town Center Room",
    description="A room set in the town center.",
    props=(props.BACKGROUND_TOWN_CENTER,),
)

TOWN_ENTRANCE = RoomData(
    name="Town Entrance Room",
    description="A room set in the town entrance.",
    props=(props.BACKGROUND_TOWN_ENTRANCE,),
)

TOWN_HALL = RoomData(
    name="Town Hall Room",
    description="A room set in the town hall.",
    props=(props.BACKGROUND_TOWN_HALL,),
)

WOODS = RoomData(
    name="Woods Room",
    description="A room set in the woods.",
    props=(props.BACKGROUND_WOODS,),
)
