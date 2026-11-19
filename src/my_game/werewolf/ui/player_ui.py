import json
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import pygame as pg

from my_game.core.renderer import Renderer
from my_game.werewolf.room.models import Prop

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

from my_game.constants import SCREEN_SIZE
from my_game.core.logger import get_logger
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action

logger = get_logger(__name__)

DATA_FILE = Path("data.json")
WEB_DATA_LOCATION = "beast_of_temerev_player_data"
PORTRAIT_SIZE = (70, 110)
# INVENTORY_SLOTS = 10
UI_OFFSET = 5
UI_SIZE = (SCREEN_SIZE[0], 125)
UI_POSITION = (0, SCREEN_SIZE[1] - UI_SIZE[1])
UI_RECT = pg.Rect(UI_POSITION[0], UI_POSITION[1], UI_SIZE[0], UI_SIZE[1])


@dataclass
class InventoryItem:
    item_name: str
    item_func_name: str


@dataclass
class PlayerInventory:
    """Represents the saved state the player's inventory"""

    inventory_slot: int
    item_name: str
    item_active: bool


class Inventory:
    """Stores and manages the player's inventory."""

    # Placement of inventory slots/buttons.
    BUTTON_COLOR = pg.Color("saddlebrown")
    BUTTON_SELECTED_COLOR = pg.Color("#D8A264")
    BUTTON_SIZE = pg.Vector2(70, 70)
    OFFSET_X = PORTRAIT_SIZE[0] + UI_OFFSET * 2
    OFFSET_Y = UI_OFFSET

    def __init__(self) -> None:
        self.inventory: list[Prop] = []
        self.selected: Prop | None = None
        self.visible = True

        button_background = pg.Surface(self.BUTTON_SIZE)
        button_background.fill(self.BUTTON_COLOR)
        self.button_background = button_background

    def has_item(self, item: Prop) -> bool:
        """Useful for avoiding duplicate items and confirming a player has an item to trigger an event"""
        name_filter = filter(lambda p: p.name == item.name, self.inventory)
        return bool(next(name_filter, False))

    def add_item(self, item: Prop) -> None:
        """Don't duplicate items, just in case"""
        if self.has_item(item):
            return

        self.inventory.append(item)

    def remove_item(self, item: Prop) -> None:
        if item in self.inventory:
            self.inventory.remove(item)

    def get_selected_item(self) -> Prop | None:
        return self.selected

    def clear_selection(self) -> None:
        self.selected = None

    def get_rect(self, slot: int) -> pg.Rect:
        return pg.Rect(
            UI_POSITION[0] + self.OFFSET_X + slot * (self.BUTTON_SIZE.x + UI_OFFSET),
            UI_POSITION[1] + self.OFFSET_Y,
            self.BUTTON_SIZE.x,
            self.BUTTON_SIZE.y,
        )

    def handle_mouse(self, pos: tuple[int, int]) -> None:
        if not self.visible:
            return
        for i, item in enumerate(self.inventory):
            if self.get_rect(i).collidepoint(pos):
                logger.info("Inventory item clicked", item=item.name)
                self.selected = item

    def draw(self, renderer: Renderer) -> None:
        # TODO: Do we want to draw empty inventory slots?
        if not self.visible:
            return
        for slot, item in enumerate(self.inventory):
            """Selected Color should be different from unselected color"""
            if self.selected:
                self.button_background.fill(self.BUTTON_SELECTED_COLOR)
            else:
                self.button_background.fill(self.BUTTON_COLOR)

            background_rect = self.get_rect(slot)
            renderer(self.button_background, background_rect, unlit=True)
            sprite = item.get_inventory_sprite()
            image_rect = sprite.get_rect(center=background_rect.center)
            renderer(sprite, image_rect, unlit=True)

    # Convert the inventory to a JSON string for saving
    # These methods should probably be part of Prop instead of here.
    def to_json(self) -> str:
        return json.dumps([asdict(item) for item in self.inventory])

    def from_json(self, json_data: str) -> None:
        self.inventory = [Prop(**item) for item in json.loads(json_data)]


class UIPanel:
    """represents the UI and all elements contained within"""

    def __init__(self) -> None:

        self.buttons = None
        self.font = Fonts.PICO8.load(size=12)
        self.font_center = self.font
        self.font_center.align = pg.FONT_CENTER
        self.selected = False

        self.bg_surf = pg.Surface(UI_SIZE)
        self.bg_surf.fill(pg.Color("#1D0900"))
        self.bg_rect = UI_RECT

        self.portrait = PortraitButton()

        self.inventory = Inventory()

        self.text_panel = TextDisplayPanel()

        self.second_portrait = SecondPortrait()

    def draw(self, renderer: Renderer) -> None:
        renderer(self.bg_surf, self.bg_rect, unlit=True)
        self.portrait.draw(renderer)
        if self.inventory.visible:
            self.inventory.draw(renderer)
        self.text_panel.draw(renderer)
        self.second_portrait.draw(renderer)

    def handle_mouse(self, actions: set[Enum], event: pg.Event, portrait_func=None) -> None:
        """Allow a room state to pass in custom functions for portrait/inventory. Otherwise, use default functionality"""
        if Action.MOUSE_SELECT in actions:
            if self.portrait.get_rect().collidepoint(event.pos):
                if portrait_func is not None:
                    portrait_func()
                else:
                    logger.info("Portrait button clicked")
            elif self.second_portrait.get_rect().collidepoint(event.pos):
                self.toggle_modes()
            else:
                """check each inventory slot for mouse click"""
                if self.inventory.visible:
                    self.inventory.handle_mouse(event.pos)

    def save_inventory(self) -> None:
        json_player_data = self.inventory.to_json()

        if sys.platform != "emscripten":
            with DATA_FILE.open("w") as player_data:
                player_data.write(json_player_data)
        else:
            window.localStorage.setItem("beast_of_temerev_player_data", json_player_data)

    def load_inventory(self) -> None:
        inventory_json = None

        if sys.platform == "emscripten":
            if player_data := window.localStorage.getItem(WEB_DATA_LOCATION):
                inventory_json = player_data
            else:
                logger.warning("Could not find inventory data in localStorage.")
                return
        else:
            try:
                with DATA_FILE.open("r") as player_data:
                    inventory_json = player_data.read()
            except FileNotFoundError:
                logger.warning("Failed to load inventory, file not found.")
                return

        self.inventory.from_json(inventory_json)

    """allow developers to enable/disable inventory wholesale, when needed"""

    def toggle_inventory(self, *, active: bool | None = None) -> None:
        """Set inventory visibility and interactibility.

        Args:
            active (bool | None): If True, show inventory. If False, hide inventory. If None, toggle current state.
        """
        self.inventory.visible = active if active else not self.inventory.visible

    def toggle_modes(self) -> None:
        """because text panel toggle function would need to know about inventory visibility otherwise"""
        self.toggle_inventory()
        self.text_panel.toggle_display()


class PortraitButton:
    """represents the portrait button"""

    def __init__(self):
        self.portrait_surf = pg.Surface(PORTRAIT_SIZE)
        self.portrait_surf.fill("#b2972a")
        self.portrait_rect = pg.Rect(
            UI_POSITION[0] + UI_OFFSET, UI_POSITION[1] + UI_OFFSET, PORTRAIT_SIZE[0], PORTRAIT_SIZE[1]
        )

        self.sprite: pg.Surface = pg.transform.scale_by(Images.MC_FACE_1.load(), 1.1)
        self.sprite_rect = self.sprite.get_rect(center=self.portrait_rect.center)

    def get_rect(self) -> pg.Rect:
        """only need to return portrait_rect because it is the whole button"""
        return self.portrait_rect

    def draw(self, renderer) -> None:
        renderer(self.portrait_surf, self.portrait_rect, unlit=True)
        renderer(self.sprite, self.sprite_rect, unlit=True)


class SecondPortrait:
    def __init__(self):
        self.portrait_surf = pg.Surface(PORTRAIT_SIZE)
        self.portrait_surf.fill("#b2972a")

        self.xpos = UI_SIZE[0] - UI_OFFSET - PORTRAIT_SIZE[0]
        self.portrait_rect = pg.Rect(self.xpos, UI_POSITION[1] + UI_OFFSET, PORTRAIT_SIZE[0], PORTRAIT_SIZE[1])

        self.sprite: pg.Surface = pg.transform.scale_by(Images.MC_FACE_2.load(), 1.1)
        self.sprite_rect = self.sprite.get_rect(center=self.portrait_rect.center)

    def get_rect(self) -> pg.Rect:
        """only need to return portrait_rect because it is the whole button"""
        return self.portrait_rect

    def draw(self, renderer) -> None:
        renderer(self.portrait_surf, self.portrait_rect, unlit=True)
        renderer(self.sprite, self.sprite_rect, unlit=True)


class TextDisplayPanel:
    def __init__(self) -> None:
        self.xpos = UI_POSITION[0] + PORTRAIT_SIZE[0] + (3 * UI_OFFSET)
        self.ypos = UI_POSITION[1] - 50
        self.width = SCREEN_SIZE[0] - (2 * PORTRAIT_SIZE[0]) - (6 * UI_OFFSET)
        self.height = UI_SIZE[1] + 45

        self.txt_surf = pg.Surface(size=(self.width, self.height))
        self.txt_surf.fill("#b2972a")
        self.txt_rect = pg.Rect(self.xpos, self.ypos, self.width, self.height)

        self.txt_inner_surf = pg.Surface(size=(self.width - 10, self.height - 10))
        self.txt_inner_surf.fill("saddlebrown")
        self.txt_inner_rect = self.txt_inner_surf.get_rect(center=self.txt_rect.center)

        self.visible = False

    def toggle_display(self) -> None:
        self.visible = not self.visible

    def draw(self, renderer) -> None:
        if self.visible:
            renderer(self.txt_surf, self.txt_rect, unlit=True)
            renderer(self.txt_inner_surf, self.txt_inner_rect, unlit=True)
