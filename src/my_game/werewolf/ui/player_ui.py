import json
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import pygame as pg

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

from my_game.constants import SCREEN_SIZE
from my_game.core.logger import get_logger
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action

logger = get_logger(__name__)

DATA_FILE = Path("data.json")
PORTRAIT_SIZE = (70, 110)
INVENTORY_SLOTS = 10
INVENTORY_BUTTON_SIZE = (70, 70)
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

        self.inventory_buttons: list[InventoryButton] = []
        for slot in range(INVENTORY_SLOTS):
            self.inventory_buttons.append(InventoryButton(slot))
        self.text_panel = TextDisplayPanel()

        self.second_portrait = SecondPortrait()

    def draw(self, renderer) -> None:
        renderer(self.bg_surf, self.bg_rect, unlit=True)
        self.portrait.draw(renderer)
        for inv_slot in self.inventory_buttons:
            inv_slot.draw(renderer)
        self.text_panel.draw(renderer)
        self.second_portrait.draw(renderer)

    def handle_mouse(self, actions: set[Enum], event: pg.Event, portrait_func=None, inv_func=None) -> None:
        """Allow a room state to pass in custom functions for portrait/inventory. Otherwise, use default functionality"""
        if Action.MOUSE_SELECT in actions:
            if self.portrait.get_rect().collidepoint(event.pos):
                if portrait_func is not None:
                    portrait_func()
                else:
                    logger.info("Portrait button clicked")
            elif self.second_portrait.get_rect().collidepoint(event.pos):
                self.text_panel.toggle_display()
            else:
                """check each inventory slot for mouse click"""
                for inv_slot in self.inventory_buttons:
                    """buttons can be disabled independent of the panel being visible, so we need to check for both"""
                    if inv_slot.button_enabled and not self.text_panel.visible:
                        if inv_slot.get_rect().collidepoint(event.pos):
                            if inv_func is not None:
                                inv_func()
                            else:
                                logger.info(f"Inventory button {inv_slot.get_slot_number()} clicked")

    def save_inventory(self) -> None:
        button_list = []
        for sel in self.inventory_buttons:
            button_list.append(asdict(sel.save_item()))
        json_player_data = json.dumps(button_list)

        if sys.platform != "emscripten":
            with DATA_FILE.open("w") as player_data:
                player_data.write(json_player_data)
        else:
            window.localStorage.setItem("beast_of_temerev_player_data", json_player_data)

    def load_inventory(self) -> None:
        saved_player_data = []

        if sys.platform != "emscripten":
            try:
                with DATA_FILE.open("r") as player_data:
                    try:
                        saved_player_data = json.loads(player_data.read())
                    except json.JSONDecodeError:
                        pass
            except FileNotFoundError:
                pass
        else:
            try:
                player_data = window.localStorage.getItem("beast_of_temerev_player_data")
                if player_data:
                    saved_player_data = json.loads(player_data)
            finally:
                pass

        """leverage the add_item function to add items to the inventory based on loaded data"""
        for item in saved_player_data:
            for button in self.inventory_buttons:
                if button.inventory_slot == item["inv_slot"]:
                    button.add_item(item["item_name"])

    """allow developers to enable/disable inventory wholesale, when needed"""

    def set_inventory_enabled(self, inv_enabled) -> None:
        for button in self.inventory_buttons:
            button.set_button_enabled(inv_enabled)


class PortraitButton:
    """represents the portrait button"""

    def __init__(self):
        self.portrait_surf = pg.Surface(PORTRAIT_SIZE)
        self.portrait_surf.fill("#b2972a")
        self.portrait_rect = pg.Rect(UI_POSITION[0] + 5, UI_POSITION[1] + UI_OFFSET, PORTRAIT_SIZE[0], PORTRAIT_SIZE[1])

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


class InventoryButton:
    """represents the inventory button"""

    def __init__(self, inventory_slot: int, item_image=None) -> None:
        self.inventory_slot = inventory_slot
        self.item_name: str = "Empty"

        """x position accounts for portrait position, all buttons that precede the current one, and their margins"""
        self.xpos = (
            UI_POSITION[0]
            + (7 * UI_OFFSET)
            + PORTRAIT_SIZE[0]
            + (self.inventory_slot * (INVENTORY_BUTTON_SIZE[0] + UI_OFFSET))
        )

        self.inv_surf = pg.Surface(INVENTORY_BUTTON_SIZE)
        self.inv_surf.fill("saddlebrown")
        self.inv_rect = pg.Rect(
            self.xpos, UI_POSITION[1] + UI_OFFSET, INVENTORY_BUTTON_SIZE[0], INVENTORY_BUTTON_SIZE[1]
        )
        # self.inv_surf.get_rect(bottomleft=(self.xpos, SCREEN_SIZE[1] - INVENTORY_BUTTON_SIZE[1])))

        self.item_image = item_image

        """Confirmed that images can work when displayed in inventory. We will load images when loading data from save file"""
        if self.item_image is not None:
            self.sprite: pg.Surface = pg.transform.smoothscale(self.item_image, self.item_image.size)
            self.sprite_rect = self.sprite.get_rect(center=self.inv_rect.center)

        self.selected = False
        self.item_active = False

        self.button_enabled: bool = True

    """toggle and set functions to enable/disable buttons. The latter is for when we want to enable/disable buttons en-masse"""

    def toggle_button_enabled(self) -> None:
        self.button_enabled = not self.button_enabled

    def set_button_enabled(self, button_enabled) -> None:
        self.button_enabled = button_enabled

    def get_slot_number(self) -> str:
        return f"{self.inventory_slot}"

    def set_slot_number(self, slot_number: int) -> None:
        self.inventory_slot = slot_number

    def get_item(self) -> str:
        return f"{self.item_name}"

    def get_rect(self) -> pg.Rect:
        return self.inv_rect

    def draw(self, renderer) -> None:
        renderer(self.inv_surf, self.inv_rect, unlit=True)
        if self.item_image is not None:
            renderer(self.sprite, self.sprite_rect, unlit=True)

    """used for adding/updating inventory slot"""

    def add_item(self, item_name: Images) -> None:
        self.item_name = item_name
        self.item_image = item_name.load()

        self.sprite = pg.transform.smoothscale(self.item_image, self.item_image.size)
        self.sprite_rect = self.sprite.get_rect(center=self.inv_rect.center)

        self.save_item()

    """Used for removing an item when a player is done with it"""

    def remove_item(self) -> None:
        self.item_name = "EMPTY"
        self.item_image = None
        self.save_item()

    """control whether item is active, based on input"""

    def use_item(self) -> None:
        self.item_active = True

    def stow_item(self) -> None:
        self.item_active = False

    def save_item(self):
        if self.item_name != "EMPTY" and self.item_name is not None:
            return PlayerInventory(self.inventory_slot, self.item_name, item_active=self.item_active)
        else:
            return PlayerInventory(self.inventory_slot, "EMPTY", item_active=False)


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
