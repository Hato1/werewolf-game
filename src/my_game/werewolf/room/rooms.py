"""Room definitions for the werewolf game."""

from my_game.werewolf.room import props
from my_game.werewolf.room.loaders import RoomData

TEST_ROOM = RoomData(
    name="Test Room",
    description="A room for testing the room rendering system.",
    props=[props.BACKGROUND, props.STUDIO],
)
