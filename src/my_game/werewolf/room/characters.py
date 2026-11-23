"""The player-controlled character that moves around rooms."""

from my_game.werewolf.assets import Images
from my_game.werewolf.room.loaders import CharacterData

PLAYER = CharacterData(
    name="Player",
    description="The player character.",
    image=Images.PLAYER_IDLE,
    position=(240, 75),
    walk_image=Images.PLAYER_WALK,
    scale=1,
)


TEST_CHARACTER = CharacterData(
    name="Test Character",
    description="A test character.",
    image=Images.PLAYER_IDLE,
    position=(80, 60),
    walk_image=Images.PLAYER_WALK,
    scale=1,
)
