import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Self

import pygame as pg

from my_game.core.logger import get_logger

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE, SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData

logger = get_logger(__name__)

OPTIONS_FILE = Path("settings.json")


def get_available_scales() -> list[int]:
    """Get list of available resolution scales that fit in the user's display."""
    if sys.platform == "emscripten":
        return [1]

    try:
        # TODO: Don't default to the first display size blindly, consider all available displays.
        display_info = pg.display.get_desktop_sizes()[0]
    except pg.error:
        display_info = (3840, 2160)
        logger.exception(f"Failed to get display info. Defaulting to {display_info}.")

    max_width = display_info[0]
    max_height = display_info[1]

    base_width = SCREEN_SIZE[0]
    base_height = SCREEN_SIZE[1]

    available_scales = []
    scale = 0
    while True:
        scale += 1
        scaled_width = base_width * scale
        scaled_height = base_height * scale
        if scaled_width <= max_width and scaled_height <= max_height:
            available_scales.append(scale)
        else:
            break

    return available_scales if available_scales else [1]


def suggest_resolution_scale():
    """Suggest a sane resolution scale based on available display scales."""
    scales = get_available_scales()
    if len(scales) > 2:  # noqa: PLR2004
        return scales[-2]
    return scales[-1]


class ExitButton:
    """Represents an exit button in the options menu."""

    FONT = Fonts.PICO8.load(MENU_FONT_SIZE)

    def __init__(self, text: str = "back"):
        self.text = text
        self.pos = (0, 0)

        # Mouseclick hitbox.
        self.rect = pg.Rect()

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        color = pg.Color("yellow") if selected else pg.Color("white")
        surf = self.FONT.render(self.text, MENU_ANTI_ALIAS, color)
        self.rect = surf.get_rect(topleft=self.pos)
        renderer(surf, self.rect, unlit=True)

    def set_pos(self, pos) -> None:
        self.pos = pos

    def collidepoint(self, pos) -> bool:
        return self.rect.collidepoint(pos)


class SelectorButton:
    """Represents a button that cycles through multiple options."""

    FONT = Fonts.PICO8.load(MENU_FONT_SIZE)
    MENU_BUTTON_OPTION_X = 400 // 2

    def __init__(self, name: str, *, options: Sequence[str | int], restart=False):
        self.pos_key = (0, 0)
        self.pos_value = (self.MENU_BUTTON_OPTION_X, 0)

        self.name = name
        self.options = options
        self.selected_index: int = 0
        self.restart = restart

        # Mouseclick hitboxes. Keep these updated as text changes.
        self.key_rect: pg.Rect = pg.Rect()
        self.value_rect: pg.Rect = pg.Rect()

    @property
    def text(self) -> str:
        return str(self.options[self.selected_index])

    @property
    def value(self):
        """Get the current selected value."""
        return self.options[self.selected_index]

    def cycle_next(self, restart_func: Callable | None) -> None:
        """Move to the next option."""
        self.selected_index = (self.selected_index + 1) % len(self.options)
        if self.restart and restart_func:
            restart_func()

    def cycle_prev(self, restart_func: Callable | None) -> None:
        """Move to the previous option."""
        self.selected_index = (self.selected_index - 1) % len(self.options)
        if self.restart and restart_func:
            restart_func()

    def draw_key(self, renderer: Renderer, *, color: pg.Color) -> None:
        draw_pos = self.pos_key
        if color == pg.Color("yellow"):
            draw_pos = self.pos_key[0] + 25, self.pos_key[1]

        surf = self.FONT.render(self.name, MENU_ANTI_ALIAS, color)
        self.key_rect = surf.get_rect(topleft=(draw_pos))

        renderer(surf, self.key_rect, unlit=True)

    def draw_value(self, renderer: Renderer, *, color: pg.Color) -> None:
        surf = self.FONT.render(self.text, MENU_ANTI_ALIAS, color)
        self.value_rect = surf.get_rect(topleft=self.pos_value)
        renderer(surf, self.value_rect, unlit=True)

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        color = pg.Color("yellow") if selected else pg.Color("white")
        self.draw_key(renderer, color=color)
        self.draw_value(renderer, color=color)

    def set_pos(self, pos) -> None:
        self.pos_key = pos
        self.pos_value = (pos[0] + self.MENU_BUTTON_OPTION_X, pos[1])

    def collidepoint(self, pos) -> bool:
        return self.key_rect.collidepoint(pos) or self.value_rect.collidepoint(pos)


@dataclass
class Settings:
    """Represents the overall settings for the options menu."""

    lighting: bool = field(default_factory=lambda: sys.platform != "emscripten")
    fullscreen: bool = False
    resolution_scale: int = field(default_factory=suggest_resolution_scale)
    sound_effects: bool = True
    music: bool = True

    @classmethod
    def from_persistent_storage_desktop(cls) -> Self:
        try:
            with OPTIONS_FILE.open("r") as settings_file:
                saved_settings = json.loads(settings_file.read())
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError:
            return cls()
        else:
            s = saved_settings[0]
            return cls(**s)

    @classmethod
    def from_persistent_storage_emscripten(cls) -> Self:
        settings = window.localStorage.getItem(OPTIONS_FILE.stem)  # pyright: ignore[reportPossiblyUnboundVariable]
        if settings:
            try:
                saved_settings = json.loads(settings)
            except json.JSONDecodeError:
                return cls()
            else:
                return cls(**saved_settings)
        return cls()

    @classmethod
    def from_persistent_storage(cls) -> Self:
        if sys.platform == "emscripten":
            return cls.from_persistent_storage_emscripten()
        else:
            return cls.from_persistent_storage_desktop()

    def to_persistent_storage_desktop(self) -> None:
        with OPTIONS_FILE.open("w") as settings_file:
            json.dump([asdict(self)], settings_file, indent=4)

    def to_persistent_storage_emscripten(self) -> None:
        window.localStorage.setItem(OPTIONS_FILE.stem, json.dumps(asdict(self)))  # pyright: ignore[reportPossiblyUnboundVariable]

    def to_persistent_storage(self) -> None:
        if sys.platform == "emscripten":
            self.to_persistent_storage_emscripten()
        else:
            self.to_persistent_storage_desktop()


class RestartSubMenu:
    FONT = Fonts.PICO8.load(MENU_FONT_SIZE)

    def __init__(self) -> None:
        self.FONT.align = pg.FONT_CENTER
        self.selected = False

        self.bg_surf = pg.Surface((SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2))
        self.bg_surf.fill(pg.Color(60, 40, 0))
        self.bg_rect = self.bg_surf.get_rect(center=(SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2))

        self.info_surf = pg.Font.render(
            self.FONT,
            "Changing this setting will require you to restart the game.\n\nSave and quit?",
            MENU_ANTI_ALIAS,
            pg.Color("white"),
            None,
            int(SCREEN_SIZE[0] / 2 - 20),
        )
        self.info_rect = self.info_surf.get_rect(midtop=(SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] * 1 / 4))

        self.yes_surf = self.FONT.render("Yes", MENU_ANTI_ALIAS, pg.Color("white"))
        self.yes_rect = self.yes_surf.get_rect(bottomleft=(SCREEN_SIZE[0] / 2 - 100, SCREEN_SIZE[1] * 5 / 8))

        self.no_surf = self.FONT.render("No", MENU_ANTI_ALIAS, pg.Color("white"))
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
    TITLE_FONT = Fonts.PICO8.load(18)
    TITLE = "options"
    TITLE_COLOR = pg.Color("white")
    TITLE_OFFSET = (25, 25)

    BACKGROUND_COLOR = pg.Color("gray20")
    MENU_BUTTON_OFFSET_Y = 75

    def __init__(self) -> None:
        super().__init__()

        # background
        self.background_color = self.BACKGROUND_COLOR
        self.background = Images.TEST_BACKGROUND.load()

        # title
        self.title_surface = self.TITLE_FONT.render(self.TITLE, MENU_ANTI_ALIAS, self.TITLE_COLOR)
        self.title_rect = self.title_surface.get_rect(topleft=self.TITLE_OFFSET)

        self.settings = Settings.from_persistent_storage()

        # buttons
        self.buttons: list[SelectorButton | ExitButton] = []
        self.add_button("music")
        self.add_button("sound effects")
        if sys.platform != "emscripten":
            self.add_button("fullscreen", restart_needed=True)
            self.add_button("resolution scale", get_available_scales(), restart_needed=True)
            self.add_button("lighting", restart_needed=True)
        self.buttons.append(ExitButton())

        self.highlighted_button_index = 0
        self.load()

        # restart menu
        self.restart_question = False
        self.restart_submenu: RestartSubMenu | None = None

    def add_button(
        self, text: str, options: Sequence[str | int] = ("off", "on"), *, restart_needed: bool = False
    ) -> None:
        button = SelectorButton(text, options=options, restart=restart_needed)
        self.buttons.append(button)

    @property
    def highlighted_button(self) -> SelectorButton | ExitButton:
        return self.buttons[self.highlighted_button_index]

    def next_button(self) -> None:
        self.highlighted_button_index = (self.highlighted_button_index + 1) % len(self.buttons)

    def prev_button(self) -> None:
        self.highlighted_button_index = (self.highlighted_button_index - 1) % len(self.buttons)

    def save(self) -> None:
        # Either update self.settings with the current button values here or when button values change.
        for button in self.buttons:
            if isinstance(button, SelectorButton):
                value = button.options[button.selected_index]
                if value == "on":
                    value = True
                elif value == "off":
                    value = False
                setattr(self.settings, button.name.replace(" ", "_"), value)

        self.settings.to_persistent_storage()

    def load(self) -> None:
        """Load saved settings and apply them to the buttons."""
        self.settings = Settings.from_persistent_storage()

        for button in self.buttons:
            if isinstance(button, SelectorButton):
                value = getattr(self.settings, button.name.replace(" ", "_"), None)
                if value is not None:
                    if isinstance(value, bool):
                        value = "on" if value else "off"
                    button.selected_index = button.options.index(value)

    def save_quit(self) -> None:
        self.save()
        self.quit = True

    def no_restart(self) -> None:
        self.restart_submenu = None

    def need_restart(self) -> None:
        self.restart_question = True
        self.restart_submenu = RestartSubMenu()

    def handle_keyboard(self, actions: set[Enum]) -> None:
        button = self.highlighted_button

        if Action.UP in actions:
            self.prev_button()

        if Action.DOWN in actions:
            self.next_button()
            pg.display.toggle_fullscreen()

        elif Action.RIGHT in actions:
            if isinstance(button, SelectorButton):
                button.cycle_next(self.need_restart)

        if Action.LEFT in actions:
            if isinstance(button, SelectorButton):
                button.cycle_prev(self.need_restart)

        if Action.UI_SELECT in actions:
            if isinstance(button, ExitButton):
                self.done = True
                self.next_state = WerewolfState.MAIN_MENU
                self.save()
            if isinstance(button, SelectorButton):
                button.cycle_next(self.need_restart)

    def handle_mouse(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.MOUSE_SELECT in actions:
            for i, button in enumerate(self.buttons):
                if button.collidepoint(event.pos):
                    self.highlighted_button_index = i
                    if isinstance(button, SelectorButton):
                        button.cycle_next(self.need_restart)
                    if isinstance(button, ExitButton):
                        self.done = True
                        self.next_state = WerewolfState.MAIN_MENU
                        self.save()
        # TODO: Handle mouse hover to update highlighted_button_index

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if self.restart_submenu:
            self.restart_submenu.handle_keyboard(actions, self.save_quit, self.no_restart)
            if self.restart_submenu:
                self.restart_submenu.handle_mouse(actions, event, self.save_quit, self.no_restart)
        else:
            self.handle_keyboard(actions)
            self.handle_mouse(actions, event)

    def update(self, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, renderer: Renderer, dt: float) -> None:
        renderer.fill(self.background_color)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.title_surface, self.title_rect, unlit=True)

        for i, button in enumerate(self.buttons):
            x = MENU_BUTTON_OFFSET_X
            y = self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y)
            button.set_pos((x, y))
            button.draw(renderer, selected=self.highlighted_button_index == i)

        if self.restart_submenu:
            self.restart_submenu.draw(renderer)
