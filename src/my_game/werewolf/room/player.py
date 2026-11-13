"""The player-controlled character that moves around rooms."""

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.werewolf.assets import Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.room.loaders import CharacterData
from my_game.werewolf.room.models import Character

PLAYER = CharacterData(
    name="Player",
    description="The player character.",
    image=Images.PLAYER_IDLE,
    position=(480, 480),
    walk_image=Images.PLAYER_WALK,
    scale=2,
)


class Player(Character):
    """A character whose movement is driven by player input."""

    def get_direction(self, dt: float, input_state: InputState) -> pg.Vector2:
        direction = pg.Vector2(
            (Action.RIGHT in input_state) - (Action.LEFT in input_state),
            (Action.DOWN in input_state) - (Action.UP in input_state),
        )
        return direction.normalize() if direction else direction
