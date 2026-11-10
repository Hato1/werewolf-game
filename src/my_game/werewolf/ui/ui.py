import json
from pathlib import Path

import pygame as pg
import pygame_gui
from pygame_gui.core import ObjectID

from my_game.constants import SCREEN_SIZE
from my_game.core.renderer import Renderer
from my_game.werewolf.assets import IMAGES_PATH, UI_PATH, Fonts

manager = pygame_gui.UIManager(SCREEN_SIZE, theme_path="../assets/ui/ui_theme.json")

DATA_PATH = "src/my_game/werewolf/data"

ui_clock = pg.time.Clock()

FONT = Fonts.PICO8.load(10)

portrait_size = (100, 150)
inventory_button_size = (100, 100)
frame_size = (SCREEN_SIZE[0] - 10, 105)
ui_surface = pg.Surface(frame_size)


def load_data(file_path):
    with Path.open(file_path) as save_file:
        data = json.load(save_file)
        return data


def load_save(file_name):
    file_path = f"{DATA_PATH}/{file_name}"
    print("retrieving data from: ", file_path)

    if Path(file_path).exists():
        return load_data(file_path)
    else:
        return {"inventory": [], "flags": {"theme": ""}}


def load_ui(ui_file_name):
    file_path = f"{UI_PATH}/{ui_file_name}"
    print("retrieving data from: ", file_path)
    return load_data(file_path)


class InventoryButton:
    def __init__(self, slot_number, current_ui_frame) -> None:
        x_pos = (slot_number * 105) + 5

        self.button = pygame_gui.elements.UIButton(
            relative_rect=pg.Rect((x_pos, -105), inventory_button_size),
            text="",
            manager=manager,
            container=current_ui_frame,
            anchors={"left": "left", "bottom": "bottom"},
            object_id=ObjectID(class_id=f"@inv_{slot_number}", object_id=f"#inv_{slot_number}"),
        )
        # self.button.image = pg.image.load("../assets/textures/item.png").convert_alpha()


# Store player data as JSON and parse to get inventory and any relevant flags that the UI might need to care about
class PlayerUI:
    # FRAME_SIZE = SCREEN_SIZE[0], 100
    # FRAME_POSITION = (5, SCREEN_SIZE[1] - 100)
    ui_running = False

    def __init__(self, save_file) -> None:
        # player save data will track inventory, ui theme, and other things, as needed
        self.player_data = load_save(save_file)

        self.position = (5, SCREEN_SIZE[1] - 100)  # Bottom-left of screen = bottom-left of inventory

        # use theme flag to determine UI frame and other graphical elements
        self.theme_flag = self.player_data["flags"]["theme"]
        self.theme = None
        self.inventory_buttons = []

        if self.theme_flag in {"test", ""}:
            sprite_path = "{}/{}".format(IMAGES_PATH, "ui_test_only.png")
            self.sprite = pg.image.load(sprite_path).convert_alpha()
        elif self.theme_flag == "Heug":
            # self.theme = load_ui("ui_theme.json")
            self.theme = "../assets/ui/ui_theme.json"

        """
        Manager knows screen size, this can be used for scaling
        theme path helps keep a uniform style
        """
        self.manager = pygame_gui.UIManager(SCREEN_SIZE, theme_path=self.theme)

        # UI Frame - container for all other UI elements
        self.ui_frame = pygame_gui.elements.UIPanel(
            relative_rect=pg.Rect((5, -165), frame_size),
            manager=manager,
            object_id=ObjectID(class_id="@frame_1", object_id="#ui"),
            anchors={"left": "left", "bottom": "bottom"},
        )

        # Portrait can be a button to display a menu, if we want. Or to do fun little things when clicked.
        self.portrait = pygame_gui.elements.UIButton(
            relative_rect=pg.Rect((5, -155), portrait_size),
            manager=manager,
            container=self.ui_frame,
            object_id=ObjectID(class_id="@portrait", object_id="#ui_portrait"),
            anchors={"left": "left", "bottom": "bottom"},
            text="",
        )

        # create inventory buttons
        for i in range(1, 5):
            self.inventory_buttons.append(InventoryButton(i, self.ui_frame))
            # self.inventory_buttons[i-1].draw(self.manager)

    # check player inventory for a specific item
    def check_inventory(self, item):
        return self.player_data["inventory"][item]

    def run_ui(self) -> None:
        # 60 FPS should be enough
        time_delta = ui_clock.tick(60) / 1000.0

        for event in pg.event.get():
            match event.type:
                # pygame_gui has its own special events for button presses and other ui interactions
                case pygame_gui.UI_BUTTON_PRESSED:
                    # Because the buttons are contained in the frame (#ui), objectID for empty inventory is: #ui.#inv_empty
                    print(f"{event.ui_object_id} pressed")

            manager.process_events(event)
        manager.update(time_delta)

    def draw_ui(self, renderer: Renderer) -> None:
        manager.draw_ui(ui_surface)  # update UI on screen
        frame_rect = pg.Rect(5, SCREEN_SIZE[1] - 110, SCREEN_SIZE[0] - 10, 55)
        renderer(ui_surface, frame_rect)
