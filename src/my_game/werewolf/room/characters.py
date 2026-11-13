"""The player-controlled character that moves around rooms."""

from my_game.werewolf.assets import Images
from my_game.werewolf.room.loaders import CharacterData

PLAYER = CharacterData(
    name="Player",
    description="The player character.",
    image=Images.PLAYER_IDLE,
    position=(480, 380),
    walk_image=Images.PLAYER_WALK,
    scale=2,
)
