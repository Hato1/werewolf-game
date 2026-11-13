"""Asset catalog for the werewolf game."""

from enum import Enum, StrEnum, unique
from functools import cache
from importlib.resources import files

import pygame as pg

from my_game.core.asset_manager import load_font, load_image, load_sound, read_text

ASSETS_PATH = files(__package__) / "assets"
IMAGES_PATH = ASSETS_PATH / "textures"
SOUNDS_PATH = ASSETS_PATH / "sounds"
FONTS_PATH = ASSETS_PATH / "fonts"
DIALOGUE_PATH = ASSETS_PATH / "dialogue"
ROOMS_PATH = ASSETS_PATH / "rooms"
UI_PATH = ASSETS_PATH / "ui"
SHADERS_PATH = ASSETS_PATH / "shaders"


@unique
class Images(StrEnum):
    BACKGROUND_CHURCH_CEMETARY = "backgrounds/church_cemetary.png"
    BACKGROUND_INN = "backgrounds/inn.png"
    BACKGROUND_TOWN_CENTER = "backgrounds/town_center.png"
    BACKGROUND_TOWN_ENTRANCE = "backgrounds/town_entrance.png"
    BACKGROUND_TOWN_HALL = "backgrounds/town_hall.png"
    BACKGROUND_WOODS = "backgrounds/woods.png"

    # Props
    INTERACTABLE_GRAVEYARD_CHAINS = "interactable_graveyard_chains.png"

    # Characters (horizontal sprite sheets of equally sized frames)
    PLAYER_IDLE = "characters/mc_idle.png"
    PLAYER_WALK = "characters/mc_walk.png"

    # Test and miscellaneous images
    TEST_BACKGROUND = "bgtest2.png"
    TEST_ROOM_BACKGROUND = "bg1.png"
    STUDIO = "studio.png"
    TEST_SHADOW = "bg_shadow.png"
    TEST_NORMALS = "bg1_normals.png"
    TEST_UI_BACKGROUND = "ui_test_only.png"
    TEST_SHADER = "shader_test_image.png"
    TEST_SHADER_0 = "shader_test_image_0.png"

    @cache
    def load(self) -> pg.Surface:
        return load_image(IMAGES_PATH / self.value)


@unique
class Sounds(Enum):
    @cache
    def load(self) -> pg.Sound:
        return load_sound(SOUNDS_PATH / self.value)


@unique
class Fonts(Enum):
    # This monospace font looks best in lowercase at pt size multiples of 6.
    PICO8 = "pico-8.ttf"

    @cache
    def load(self, size: int = 20) -> pg.Font:
        return load_font(FONTS_PATH / self.value, size)


@unique
class Dialogue(Enum):
    # Is this a sane way to handle storing/retrieving passages of text?

    @cache
    def load(self) -> str:
        """Return the text."""
        return read_text(DIALOGUE_PATH / self.value)


@unique
class Shaders(Enum):
    """GLSL shader files to use with OpenGL."""

    UNLIT_FRAG = "unlit_fragment.shader"
    OUTLINE_FRAG = "outline_fragment.shader"
    LIT_FRAG = "lit_fragment.shader"
    POINT_LIGHTS_FRAG = "point_light_fragment.shader"

    STANDARD_VERT = "standard_vertex.shader"
    OUTLINE_VERT = "outline_vertex.shader"

    @cache
    def load(self) -> str:
        """Return the text."""
        return read_text(SHADERS_PATH / self.value)


@unique
class UIElements(Enum):
    UI_THEME = "ui_theme.json"

    @cache
    def load(self) -> pg.Surface:
        return load_image(UI_PATH / self.value)
