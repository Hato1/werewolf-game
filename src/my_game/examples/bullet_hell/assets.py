"""Asset catalog for the bullet-hell example."""

from enum import Enum, unique
from functools import cache
from importlib.resources import files

import pygame as pg

from my_game.core.asset_manager import load_font, load_image, load_sound, read_text

ASSETS_PATH = files(__package__) / "assets"
IMAGES_PATH = ASSETS_PATH / "images"
SOUNDS_PATH = ASSETS_PATH / "sounds"
FONTS_PATH = ASSETS_PATH / "fonts"
LEVELS_PATH = ASSETS_PATH / "levels"
UI_PATH = ASSETS_PATH / "ui"


@unique
class Images(Enum):
    MONSTER_FRAME_0 = "monster/frame_0.png"
    MONSTER_FRAME_1 = "monster/frame_1.png"

    @cache
    def load(self) -> pg.Surface:
        return load_image(IMAGES_PATH / self.value)


@unique
class Sounds(Enum):
    # Placeholder entries: add matching files under assets/sounds/ before loading.
    # Web builds with PygBag only support OGG sounds.
    EXPLOSION = "explosion.wav"
    SHOOT = "shoot.wav"
    # Background music needs a separate loader based on pg.mixer.music.
    BACKGROUND_MUSIC = "background.mp3"

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
class Levels(Enum):
    # Placeholder entries: add matching JSON files under assets/levels/ before loading.
    LEVEL_1 = "level_1.json"
    LEVEL_2 = "level_2.json"

    @cache
    def load(self) -> str:
        """Return the level's UTF-8 JSON text."""
        return read_text(LEVELS_PATH / self.value)


@unique
class UIElements(Enum):
    HEART_FULL = "healthbar/heart_full.png"
    HEART_EMPTY = "healthbar/heart_empty.png"

    @cache
    def load(self) -> pg.Surface:
        return load_image(UI_PATH / self.value)
