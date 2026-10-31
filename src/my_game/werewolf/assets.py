"""Asset catalog for the werewolf game."""

from enum import Enum, unique
from functools import cache
from importlib.resources import files

import pygame as pg

from my_game.core.asset_manager import load_font, load_image, load_sound, read_text

ASSETS_PATH = files(__package__) / "assets"
IMAGES_PATH = ASSETS_PATH / "images"
SOUNDS_PATH = ASSETS_PATH / "sounds"
FONTS_PATH = ASSETS_PATH / "fonts"
DIALOGUE_PATH = ASSETS_PATH / "dialogue"
UI_PATH = ASSETS_PATH / "ui"
SHADERS_PATH = ASSETS_PATH / "shaders"


@unique
class Images(Enum):
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

    @cache
    def load(self) -> str:
        """Return the text."""
        return read_text(SHADERS_PATH / self.value)


@unique
class UIElements(Enum):
    @cache
    def load(self) -> pg.Surface:
        return load_image(UI_PATH / self.value)
