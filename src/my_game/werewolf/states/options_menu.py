import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import pygame as pg

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE, SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData

OPTIONS_FILE = Path("settings.json")


class ToggleButton:
    """Represents the state of a boolean toggle button."""

    def __init__(self, font, *, status: bool, enabled_text="On", disabled_text="Off", restart=False):
        self.font = font
        self.pos = (0, 0)

        self.status = status
        self.enabled_text: str = enabled_text
        self.disabled_text: str = disabled_text
        self.restart = restart

        # shapes
        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    @property
    def text(self) -> str:
        return self.enabled_text if self.status else self.disabled_text

    def action(self, restart_func: Callable | None):
        if self.restart and restart_func:
            restart_func()
        else:
            self.status = not self.status

    def draw(self, renderer: Renderer, *, selected) -> None:
        font_color = "yellow" if selected else "white"

        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color(font_color))

        renderer(self.surf, self.rect, unlit=True)

    def set_pos(self, pos) -> None:
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)
        # text = '"Type:":"ToggleButton", '
        # text += '"Status:":"' + str(self.status) + '", '
        # text += '"True:":"' + self.enabled_text + '", '
        # text += '"False:":"' + self.disabled_text + '"'
        # return text


class Option:
    """Represents a single option in the options menu."""

    def __init__(self, font, text, key) -> None:
        # key is the identifier for this option.
        self.key: str = key
        self.text: str = text
        self.font: pg.Font = font
        self.pos: tuple[int, int] = (0, 0)

        # shapes
        self.surf: pg.Surface = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color("white"))
        self.rect: pg.Rect = self.surf.get_rect(topleft=self.pos)

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


@dataclass
class SavedOptions:
    """Represents the saved state of an option in the options menu."""

    key: str
    status: bool


class OptionsMenuButton:
    """Represents a button in the options menu, which may have an associated toggle button to change its state."""

    def __init__(self, option: Option, button: ToggleButton | None):
        self.option: Option = option
        self.button: ToggleButton | None = button

    def save(self) -> SavedOptions:
        if self.button:
            return SavedOptions(self.option.key, self.button.status)
        else:
            junk = False
            return SavedOptions(self.option.key, junk)


class RestartSubMenu:
    def __init__(self, font) -> None:
        self.font = font
        self.font_center = font
        self.font_center.align = pg.FONT_CENTER
        self.selected = False

        self.bg_surf = pg.Surface((SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2))
        self.bg_surf.fill(pg.Color(60, 40, 0))
        self.bg_rect = self.bg_surf.get_rect(center=(SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2))

        self.info_surf = pg.Font.render(
            self.font_center,
            "Changing this setting will require you to restart the game.\n\nSave and quit?",
            MENU_ANTI_ALIAS,
            pg.Color("white"),
            None,
            int(SCREEN_SIZE[0] / 2 - 20),
        )
        self.info_rect = self.info_surf.get_rect(midtop=(SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] * 1 / 4))

        self.yes_surf = self.font.render("Yes", MENU_ANTI_ALIAS, pg.Color("white"))
        self.yes_rect = self.yes_surf.get_rect(bottomleft=(SCREEN_SIZE[0] / 2 - 100, SCREEN_SIZE[1] * 5 / 8))

        self.no_surf = self.font.render("No", MENU_ANTI_ALIAS, pg.Color("white"))
        self.no_rect = self.no_surf.get_rect(bottomright=(SCREEN_SIZE[0] / 2 + 100, SCREEN_SIZE[1] * 5 / 8))

        self.sel_surf = pg.Surface((0, 0))
        self.sel_rect = self.sel_surf.get_rect(bottomleft=(0, 0))
        self.sel_rad = 15

    def draw(self, renderer) -> None:
        if self.selected:
            size = self.yes_surf.get_size()
            self.sel_surf = pg.Surface((size[0] + self.sel_rad, size[1] + self.sel_rad))
            self.sel_surf.fill("saddlebrown")
            self.sel_rect = self.sel_surf.get_rect(center=self.yes_rect.center)
        else:
            size = self.no_surf.get_size()
            self.sel_surf = pg.Surface((size[0] + self.sel_rad, size[1] + self.sel_rad))
            self.sel_surf.fill("saddlebrown")
            self.sel_rect = self.sel_surf.get_rect(center=self.no_rect.center)

        renderer(self.bg_surf, self.bg_rect, unlit=True)
        renderer(self.sel_surf, self.sel_rect, unlit=True)
        renderer(self.info_surf, self.info_rect, unlit=True)
        renderer(self.yes_surf, self.yes_rect, unlit=True)
        renderer(self.no_surf, self.no_rect, unlit=True)

    def handle_mouse(self, actions: set[Enum], event: pg.Event, done_func, exit_func) -> None:
        if Action.MOUSE_SELECT in actions:
            if self.yes_rect.collidepoint(event.pos):
                done_func()
            elif self.no_rect.collidepoint(event.pos):
                exit_func()

    def handle_keyboard(self, actions: set[Enum], done_func, exit_func) -> None:
        if Action.RIGHT in actions and self.selected:
            self.selected = False

        if Action.LEFT in actions and not self.selected:
            self.selected = True

        if Action.UI_SELECT in actions:
            if self.selected:
                done_func()
            else:
                exit_func()


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
                OptionsMenuButton(
                    Option(self.FONT, "Lighting", "LIGHT"), ToggleButton(self.FONT, status=True, restart=True)
                )
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

        # restart menu
        self.restart_question = False
        self.restart_submenu: RestartSubMenu | None = None

    def save(self) -> None:
        button_list = []
        for sel in self.buttons:
            button_list.append(asdict(sel.save()))
        json_settings = json.dumps(button_list)

        if sys.platform != "emscripten":
            with OPTIONS_FILE.open("w") as settings:
                settings.write(json_settings)
        else:
            window.localStorage.setItem("settings", json_settings)

    def load(self) -> None:
        saved_settings = []

        if sys.platform != "emscripten":
            try:
                with OPTIONS_FILE.open("r") as settings:
                    try:
                        saved_settings = json.loads(settings.read())
                    except json.JSONDecodeError:
                        pass
            except FileNotFoundError:
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
                    button.button.action(None)

    def save_quit(self) -> None:
        button = self.buttons[self.button_y].button
        if button:
            button.action(None)
        self.save()
        self.quit = True

    def no_restart(self) -> None:
        self.restart_submenu = None

    def need_restart(self) -> None:
        self.restart_question = True
        self.restart_submenu = RestartSubMenu(self.FONT)

    def handle_keyboard(self, actions: set[Enum]) -> None:
        if Action.UP in actions:
            self.button_y = (self.button_y - 1) % len(self.buttons)

        if Action.DOWN in actions:
            self.button_y = (self.button_y + 1) % len(self.buttons)

        if Action.RIGHT in actions and self.button_x == 0:
            self.button_x = 1

        if Action.LEFT in actions and self.button_x == 1:
            self.button_x = 0

        if Action.UI_SELECT in actions:
            if self.button_x == 0 and not self.buttons[self.button_y].button:
                self.done = True
                self.next_state = WerewolfState.MAIN_MENU
                self.save()
            elif self.button_x == 1:
                for i, sel in enumerate(self.buttons):
                    if i == self.button_y and sel.button:
                        sel.button.action(self.need_restart)

    def handle_mouse(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.MOUSE_SELECT in actions:
            for i, sel in enumerate(self.buttons):
                if sel.button and sel.button.rect.collidepoint(event.pos):
                    self.button_y = i
                    self.button_x = 1
                    sel.button.action(self.need_restart)
                if sel.option and sel.option.rect.collidepoint(event.pos):
                    self.button_y = i
                    self.button_x = 0
                    if not sel.button:
                        self.done = True
                        self.next_state = WerewolfState.MAIN_MENU
                        self.save()

    def normalize_menu(self) -> None:
        if self.button_x == 1 and not self.buttons[self.button_y].button:
            self.button_x = 0

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if self.restart_submenu:
            self.restart_submenu.handle_keyboard(actions, self.save_quit, self.no_restart)
            if self.restart_submenu:
                self.restart_submenu.handle_mouse(actions, event, self.save_quit, self.no_restart)
        else:
            self.handle_keyboard(actions)
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

        if self.restart_submenu:
            self.restart_submenu.draw(renderer)
