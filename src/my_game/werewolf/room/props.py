"""Reusable prop definitions for room construction.

The long term goal for this file is to be exclusively machine generated using
a 'room builder' tool that generates prop definitions automatically.
"""

from my_game.werewolf.assets import Images
from my_game.werewolf.room.loaders import PropData

BACKGROUND = PropData(
    description="The room background.",
    image=Images.ROOM_TEST,
    size=(960, 540),
    clickable=False,
    depth=9999,
    id="background",
)

STUDIO = PropData(
    description="a tiny studio model.",
    image=Images.STUDIO,
    position=(800 // 2, 70 // 2),
    scale=0.025,
    depth=0,
    walk_to_interact=True,
    id="studio",
)

BACKGROUND_CHURCH_CEMETARY = PropData(
    description="The church cemetary background.",
    image=Images.CHURCH_CEMETARY,
    scale=1,
    clickable=False,
    depth=9999,
    id="church_cemetary_background",
)

BACKGROUND_INN = PropData(
    description="The inn background.",
    image=Images.INN,
    scale=1,
    clickable=False,
    depth=9999,
    id="inn_background",
)

BACKGROUND_TOWN_CENTER = PropData(
    description="The town center background.",
    image=Images.BACKGROUND_TOWN_CENTER,
    size=(960 // 2, 540 // 2),
    clickable=False,
    depth=9999,
    id="town_center_background",
)

BACKGROUND_TOWN_ENTRANCE = PropData(
    description="The town entrance background.",
    image=Images.BACKGROUND_TOWN_ENTRANCE,
    size=(960 // 2, 540 // 2),
    clickable=False,
    depth=9999,
    id="town_entrance_background",
)

BACKGROUND_TOWN_HALL = PropData(
    description="The town hall background.",
    image=Images.BACKGROUND_TOWN_HALL_1,
    size=(960 // 2, 540 // 2),
    clickable=False,
    depth=9999,
    id="town_hall_background",
)

BACKGROUND_WOODS = PropData(
    description="The woods background.",
    image=Images.WOODS,
    scale=1,
    clickable=False,
    depth=9999,
    id="woods_background",
)

GRAVEYARD_CHAINS = PropData(
    description="An interactable set of graveyard chains.",
    image=Images.INTERACTABLE_GRAVEYARD_CHAINS,
    position=(300, 150),
    scale=1,
    clickable=True,
    depth=500,
    walk_to_interact=True,
    id="graveyard_chains",
)
