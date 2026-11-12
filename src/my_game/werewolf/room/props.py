"""Reusable prop definitions for room construction.

The long term goal for this file is to be exclusively machine generated using
a 'room builder' tool that generates prop definitions automatically.
"""

from my_game.werewolf.assets import Images
from my_game.werewolf.room.loaders import PropData

BACKGROUND = PropData(
    name="Background",
    description="The room background.",
    image=Images.TEST_ROOM_BACKGROUND,
    size=(960, 540),
    clickable=False,
    depth=9999,
)

STUDIO = PropData(
    name="Studio Background",
    description="a tiny studio model.",
    image=Images.STUDIO,
    position=(380, 200),
    scale=0.1,
    depth=0,
)

BACKGROUND_CHURCH_CEMETARY = PropData(
    name="Church Cemetary Background",
    description="The church cemetary background.",
    image=Images.BACKGROUND_CHURCH_CEMETARY,
    scale=2,
    clickable=False,
    depth=9999,
)

BACKGROUND_INN = PropData(
    name="Inn Background",
    description="The inn background.",
    image=Images.BACKGROUND_INN,
    scale=2,
    clickable=False,
    depth=9999,
)

BACKGROUND_TOWN_CENTER = PropData(
    name="Town Center Background",
    description="The town center background.",
    image=Images.BACKGROUND_TOWN_CENTER,
    size=(960, 540),
    clickable=False,
    depth=9999,
)

BACKGROUND_TOWN_ENTRANCE = PropData(
    name="Town Entrance Background",
    description="The town entrance background.",
    image=Images.BACKGROUND_TOWN_ENTRANCE,
    size=(960, 540),
    clickable=False,
    depth=9999,
)

BACKGROUND_TOWN_HALL = PropData(
    name="Town Hall Background",
    description="The town hall background.",
    image=Images.BACKGROUND_TOWN_HALL,
    size=(960, 540),
    clickable=False,
    depth=9999,
)

BACKGROUND_WOODS = PropData(
    name="Woods Background",
    description="The woods background.",
    image=Images.BACKGROUND_WOODS,
    scale=2,
    clickable=False,
    depth=9999,
)

GRAVEYARD_CHAINS = PropData(
    name="Graveyard Chains",
    description="An interactable set of graveyard chains.",
    image=Images.INTERACTABLE_GRAVEYARD_CHAINS,
    position=(400, 300),
    scale=2,
    clickable=True,
    depth=500,
)
