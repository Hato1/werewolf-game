"""Reusable prop definitions for room construction."""

from my_game.werewolf.assets import Images
from my_game.werewolf.room.loaders import PropData

BACKGROUND = PropData(
    name="Background",
    description="The room background.",
    image=Images.TEST_ROOM_BACKGROUND,
    position=(0, 0),
    size=(960, 540),
    clickable=False,
    depth=9999,
)

STUDIO = PropData(
    name="Studio",
    description="a tiny studio model.",
    image=Images.STUDIO,
    position=(380, 200),
    scale=0.1,
    depth=0,
)
