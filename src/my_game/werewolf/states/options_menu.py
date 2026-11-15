import json
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import pygame as pg

if __import__("sys").platform == "emscripten":
    from platform import window

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class ToggleButton:
    def __init__(self, font, *, true="On", false="Off", status: bool):
        self.font = font
        self.pos = (0, 0)

        self.status = status
        self.true = true
        self.false = false
        self.text = self.true if self.status else self.false

        # shapes
        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    def action(self):
        self.status = not self.status
        self.text = self.true if self.status else self.false

    def draw(self, renderer: Renderer, *, selected) -> None:
        font_color = "white"
        if selected:
            font_color = "yellow"

        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color(font_color))

        renderer(self.surf, self.rect, unlit=True)

    def set_pos(self, pos) -> None:
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)
        text = '"Type:":"ToggleButton", '
        text += '"Status:":"' + str(self.status) + '", '
        text += '"True:":"' + self.true + '", '
        text += '"False:":"' + self.false + '"'
        return text


class Option:
    def __init__(self, font, text, key) -> None:
        self.key = key
        self.text = text
        self.font = font
        self.pos = (0, 0)

        # shapes
        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        draw_pos = self.pos
        font_color = "white"
        if selected:
            font_color = "yellow"
            draw_pos = self.pos[0] + 25, self.pos[1]

        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color(font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))

        renderer(self.surf, self.rect, unlit=True)

    def set_pos(self, pos) -> None:
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)


class OptionsMenuButton:
    def __init__(self, option: Option, button: ToggleButton | None):
        self.option = option
        self.button = button

    def save(self) -> SavedOptions:
        if self.button:
            return SavedOptions(self.option.key, self.button.status)
        else:
            junk = False
            return SavedOptions(self.option.key, junk)


@dataclass
class SavedOptions:
    key: str
    status: bool


class OptionsMenu(State[WerewolfState, WerewolfTransitionData]):
    TITLE_FONT_SIZE = 36
    MENU_BUTTON_OFFSET_Y = 150
    MENU_BUTTON_OPTION_X = 300

    def __init__(self) -> None:
        super().__init__()

        # background
        self.background_color = pg.Color("gray20")
        self.background = Images.TEST_BACKGROUND.load()

        # text
        self.FONT = Fonts.PICO8.load(MENU_FONT_SIZE)
        self.TITLE_FONT = Fonts.PICO8.load(self.TITLE_FONT_SIZE)

        # title
        title = "Options"
        self.title_surface = self.TITLE_FONT.render(title, MENU_ANTI_ALIAS, pg.Color("white"))
        self.title_rect = self.title_surface.get_rect(topleft=(50, 50))

        # buttons
        self.buttons: list[OptionsMenuButton] = [
            OptionsMenuButton(Option(self.FONT, "Music", "MUSIC"), ToggleButton(self.FONT, status=True)),
            OptionsMenuButton(Option(self.FONT, "Sound Effects", "SOUND"), ToggleButton(self.FONT, status=True)),
        ]
        if sys.platform != "emscripten":
            self.buttons.append(
                OptionsMenuButton(Option(self.FONT, "Lighting", "LIGHT"), ToggleButton(self.FONT, status=True))
            )
        self.buttons.append(OptionsMenuButton(Option(self.FONT, "Exit", "EXIT"), None))

        self.button_x = 0
        self.button_y = 0

        for i, sel in enumerate(self.buttons):
            sel.option.set_pos((MENU_BUTTON_OFFSET_X, self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y)))
            if sel.button:
                sel.button.set_pos(
                    (
                        MENU_BUTTON_OFFSET_X + self.MENU_BUTTON_OPTION_X,
                        self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y),
                    )
                )

        self.load()

    def save(self) -> None:
        button_list = []
        for sel in self.buttons:
            button_list.append(asdict(sel.save()))
        json_settings = json.dumps(button_list)

        if sys.platform != "emscripten":
            with Path("settings").open("w") as settings:
                settings.write(json_settings)
        else:
            window.localStorage.setItem("settings", json_settings)

    def load(self) -> None:
        saved_settings = []

        if sys.platform != "emscripten":
            with Path("settings").open("r") as settings:
                try:
                    saved_settings = json.loads(settings.read())
                except json.JSONDecodeError:
                    pass
        else:
            try:
                settings = window.localStorage.getItem("settings")
                if settings:
                    saved_settings = json.loads(settings)
            finally:
                pass

        for setting in saved_settings:
            for button in self.buttons:
                if (
                    button.button
                    and setting.get("key") == button.option.key
                    and setting.get("status") != button.button.status
                ):
                    button.button.action()

    def handle_keyboard(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UP in actions:
            self.button_y = (self.button_y - 1) % len(self.buttons)

        if Action.DOWN in actions:
            self.button_y = (self.button_y + 1) % len(self.buttons)

        if Action.RIGHT in actions and self.button_x == 0:
            self.button_x = 1

        if Action.LEFT in actions and self.button_x == 1:
            self.button_x = 0

        if Action.MOUSE_SELECT in actions:
            for i, sel in enumerate(self.buttons):
                if sel.button and sel.button.rect.collidepoint(event.pos):
                    self.button_y = i
                    self.button_x = 1
                    sel.button.action()
                if sel.option and sel.option.rect.collidepoint(event.pos):
                    self.button_y = i
                    self.button_x = 0
                    if not sel.button:
                        self.done = True
                        self.next_state = WerewolfState.MAIN_MENU
                        self.save()

    def handle_mouse(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            if self.button_x == 0 and not self.buttons[self.button_y].button:
                self.done = True
                self.next_state = WerewolfState.MAIN_MENU
                self.save()
            elif self.button_x == 1:
                for i, sel in enumerate(self.buttons):
                    if i == self.button_y and sel.button:
                        sel.button.action()

    def normalize_menu(self) -> None:
        if self.button_x == 1 and not self.buttons[self.button_y].button:
            self.button_x = 0

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        self.handle_keyboard(actions, event)
        self.handle_mouse(actions, event)
        self.normalize_menu()

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, renderer: Renderer, dt: float) -> None:
        renderer.fill(self.background_color)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.title_surface, self.title_rect, unlit=True)

        for i, sel in enumerate(self.buttons):
            sel.option.draw(renderer, selected=self.button_y == i)
            if sel.button:
                sel.button.draw(renderer, selected=self.button_y == i and self.button_x == 1)
