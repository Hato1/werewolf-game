"""Asset catalog for the werewolf game."""

from enum import Enum, StrEnum, unique
from functools import cache
from importlib.resources import files

import pygame as pg

from my_game.core.asset_manager import load_font, load_image, load_sound, read_text
from my_game.core.logger import get_logger

logger = get_logger(__name__)

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
    # Root level
    ARTEMIS_STAINED_GLASS = "artemis_stained_glass.png"
    BG2 = "bg2.png"
    BG3 = "bg3.png"
    CANDLE = "candle.png"
    FOREST_ENTRANCE = "forest_entrance.png"
    INNK_EYES1 = "innk_eyes1.png"
    INNK_MOUTH1 = "innk_mouth1.png"
    MOON_SCREENSHOT = "moon_screenshot.png"
    MOON_SCREENSHOT_TREES = "moon_screenshot_trees.png"
    ROOM_TEST = "room_test.png"
    SHADER_TEST_IMAGE = "shader_test_image.png"
    SHADER_TEST_IMAGE_0 = "shader_test_image_0.png"
    SPLASH_TF_0 = "splash_tf_0.png"
    SPLASH_TF_1 = "splash_tf_1.png"
    SPLASH_TF_END = "splash_tf_end.png"
    UI_TEST_ONLY = "ui_test_only.png"

    # Backgrounds
    BACKGROUND_CLOUDS = "backgrounds/background_clouds.png"
    BACKGROUND_FULLMOON = "backgrounds/background_fullmoon.png"
    BACKGROUND_GEO = "backgrounds/background_geo.png"
    BACKGROUND_NIGHTSKY = "backgrounds/background_nightsky.png"
    BACKGROUNDTEST1 = "backgrounds/backgroundtest1.png"
    BACKGROUNDTEST2 = "backgrounds/backgroundtest2.png"
    BACKGROUNDTEST3 = "backgrounds/backgroundtest3.png"

    # Church - Cemetary
    CHURCH_CEMETARY = "backgrounds/church-cemetary/church_cemetary.png"

    # Church - Inside
    BACKGROUND_CHURCH = "backgrounds/church-inside/background_church.png"
    BACKGROUND_CHURCH_NORMALS = "backgrounds/church-inside/background_church_normals.png"
    CHURCH = "backgrounds/church-inside/church.png"

    # Church - Outside
    BACKGROUND_TOWN_CHURCH1 = "backgrounds/church-outside/background_town_church1.png"

    # Inn - Inside
    BACKGROUND1_NORMALS = "backgrounds/inn-inside/background1_normals.png"
    BACKGROUND_INN_LIGHT_MASK = "backgrounds/inn-inside/background_inn-Light Mask.png"
    BACKGROUND_INN = "backgrounds/inn-inside/background_inn.png"
    BACKGROUND_INN_DEPTH_MASK = "backgrounds/inn-inside/background_inn_depth_mask.png"
    BACKGROUND_INN_NN = "backgrounds/inn-inside/background_inn_nn.png"
    BACKGROUND_INN_WEB = "backgrounds/inn-inside/background_inn_web.png"
    BACKGROUND_SHADOW = "backgrounds/inn-inside/background_shadow.png"
    INN = "backgrounds/inn-inside/inn.png"

    # Inn - Outside
    BACKGROUND_TOWN_INN1 = "backgrounds/inn-outside/background_town_inn1.png"

    # Shed
    BACKGROUND_SHED = "backgrounds/shed/background_shed.png"
    CEMETARY_SHED = "backgrounds/shed/cemetary_shed.png"

    # Town - Center
    BACKGROUND_TOWN_CENTER = "backgrounds/town-center/background_town_center.png"

    # Town - Entrance
    BACKGROUND_TOWN_ENTRANCE_COPY = "backgrounds/town-entrance/background_town_entrance (copy).png"
    BACKGROUND_TOWN_ENTRANCE = "backgrounds/town-entrance/background_town_entrance.png"
    BACKGROUND_TOWN_ENTRANCE2_COPY = "backgrounds/town-entrance/background_town_entrance2 (copy).png"
    BACKGROUND_TOWN_ENTRANCE2 = "backgrounds/town-entrance/background_town_entrance2.png"

    # Town - Hall
    BACKGROUND_HALL = "backgrounds/town-hall/background_hall.png"
    BACKGROUND_TOWN_HALL_1 = "backgrounds/town-hall/background_town_hall_1.png"
    BACKGROUND_TOWN_HALL_2 = "backgrounds/town-hall/background_town_hall_2.png"

    # Woods
    WOODS = "backgrounds/woods/woods.png"
    WOODS_1 = "backgrounds/woods/woods_1.png"

    # Characters
    CHAR_ELDER_LIGHT_MASK = "characters/char_elder-Light Mask.png"
    CHAR_ELDER = "characters/char_elder.png"
    CHAR_ELDER_NORMAL = "characters/char_elder_Normal.png"
    CHAR_GRNDK_LIGHT_MASK = "characters/char_grndk-Light Mask.png"
    CHAR_GRNDK_NORMAL = "characters/char_grndk-Normal.png"
    CHAR_GRNDK = "characters/char_grndk.png"
    CHAR_INNK_LIGHT_MASK = "characters/char_innk-Light Mask.png"
    CHAR_INNK = "characters/char_innk.png"
    CHAR_INNK_NN = "characters/char_innk_nn.png"
    CHAR_INNK_WEB = "characters/char_innk_web.png"
    CHAR_MERCHANT = "characters/char_merchant.png"
    CHAR_NUN_LIGHT_MASK = "characters/char_nun-Light Mask.png"
    CHAR_NUN_NORMAL = "characters/char_nun-Normal.png"
    CHAR_NUN = "characters/char_nun.png"
    MC_IDLE = "characters/mc_idle.png"
    MC_IDLE_SMALL = "characters/mc_idle_small.png"
    MC_WALK_NORMAL = "characters/mc_walk-Normal.png"
    MC_WALK = "characters/mc_walk.png"
    MC_WALK_SMALL = "characters/mc_walk_small.png"
    MERCHANT_STALL1 = "props/merchant_stall1.png"

    # Miscellaneous
    PLAYER_PORTRAIT_WOLF = "krita_files/player_portrait_wolf.png"
    STUDIO_LIGHT = "misc/studio-light.png"
    STUDIO = "misc/studio.png"

    # Portraits
    ELDER_FACE1 = "portraits/elder_face1.png"
    GRNDK_FACE1 = "portraits/grndk_face1.png"
    INNK_FACE1 = "portraits/innk_face1.png"
    MC_FACE1 = "portraits/mc_face1.png"
    MC_FACE2 = "portraits/mc_face2.png"
    MERCHANT_FACE1 = "portraits/merchant_face1.png"
    NUN_FACE1 = "portraits/nun_face1.png"

    # Props
    AMMO_1 = "props/ammo_1.png"
    AMMO_2 = "props/ammo_2.png"
    BOOTS_1 = "props/boots_1.png"
    BOX_COINS = "props/box_coins.png"
    BRANCHES1 = "props/branches1.png"
    CHAINS_1 = "props/chains_1.png"
    CHEST_1 = "props/chest_1.png"
    CLOTHES_BASKET_1 = "props/clothes_basket_1.png"
    CLOTHES_BASKET_EMPTY = "props/clothes_basket_empty.png"
    CLOTHES_BASKET_FULL = "props/clothes_basket_full.png"
    DOOR_HANDLE1 = "props/door_handle1.png"
    DOOR_HANDLE2 = "props/door_handle2.png"
    DOOR_HANDLE3 = "props/door_handle3.png"
    DRAG_MARKS = "props/drag_marks.png"
    DRESSER_1 = "props/dresser_1.png"
    FLINTLOCK_1 = "props/flintlock_1.png"
    INN_LAMP = "props/inn_lamp.png"
    INN_TABLE = "props/inn_table.png"
    INTERACTABLE_CHURCH_CLOTHES_BASKET = "props/interactable_church_clothes_basket.png"
    INTERACTABLE_GRAVEYARD_CHAINS = "props/interactable_graveyard_chains.png"
    INTERACTABLE_SHED_CHEST = "props/interactable_shed_chest.png"
    INTERACTABLE_SHED_HOOK = "props/interactable_shed_hook.png"
    INTERACTABLE_SHED_HOOK_HL = "props/interactable_shed_hook_HL.png"
    INTERACTABLE_SHED_HOOK_NN = "props/interactable_shed_hook_nn.png"
    INTERACTABLE_SHED_RAGS = "props/interactable_shed_rags.png"
    LANTERN_1 = "props/lantern_1.png"
    LANTERN_2 = "props/lantern_2.png"
    OIL_JUG1 = "props/oil_jug1.png"
    PIE_TIN1 = "props/pie_tin1.png"
    PIE_TIN2 = "props/pie_tin2.png"
    RAGS_1 = "props/rags_1.png"
    SMALL_TREES = "props/small_trees.png"
    SUPPLIES1 = "props/supplies1.png"
    TANKARD_1 = "props/tankard_1.png"
    TANKARD_2 = "props/tankard_2.png"
    TAX_COLLECTOR_CORPSE = "props/tax_collector_corpse.png"
    TREE_LARGE_0 = "props/tree_large_0.png"
    TREE_LARGE_1 = "props/tree_large_1.png"
    TREE_LARGE_2 = "props/tree_large_2.png"
    TREE_TOPS_TILE = "props/tree_tops_tile.png"

    # Sequences - Transformation
    SEQUENCE_HEUG_TO_WEREWOLF_0 = "sequences/heug_to_werewolf/image_0.png"
    SEQUENCE_HEUG_TO_WEREWOLF_1 = "sequences/heug_to_werewolf/image_1.png"
    SEQUENCE_HEUG_TO_WEREWOLF_2 = "sequences/heug_to_werewolf/image_2.png"
    SEQUENCE_HEUG_TO_WEREWOLF_3 = "sequences/heug_to_werewolf/image_3.png"
    SEQUENCE_HEUG_TO_WEREWOLF_4 = "sequences/heug_to_werewolf/image_4.png"
    SEQUENCE_HEUG_TO_WEREWOLF_5 = "sequences/heug_to_werewolf/image_5.png"
    SEQUENCE_HEUG_TO_WEREWOLF_6 = "sequences/heug_to_werewolf/image_6.png"
    SEQUENCE_HEUG_TO_WEREWOLF_7 = "sequences/heug_to_werewolf/image_7.png"

    @cache
    def load(self) -> pg.Surface:
        return load_image(IMAGES_PATH / self.value)

    def get_path(self) -> str:
        return str(IMAGES_PATH / self.value)

    @cache
    def load_custom(self, file_name) -> pg.Surface:
        logger.error(f"Debug image loader called with file_name: {file_name}")
        return load_image(IMAGES_PATH / file_name)


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
