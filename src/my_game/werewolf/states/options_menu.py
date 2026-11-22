import sys
from collections.abc import Callable, Sequence
from enum import Enum

import pygame as pg

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE, SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.logger import get_logger
from my_game.core.renderer import Renderer, get_available_scales
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.settings import Settings
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData

logger = get_logger(__name__)


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
    FONT_COLOR = pg.Color("white")
    FONT_HIGHLIGHT_COLOR = pg.Color("yellow")

    def __init__(self, name: str, *, options: Sequence[str | int], restart=False, callback: Callable | None = None):
        self.pos_key = (0, 0)
        self.pos_value = (self.MENU_BUTTON_OPTION_X, 0)

        self.name = name
        self.options = options
        self.selected_index: int = 0
        self.restart = restart
        self.callback = callback

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

    def cycle(self, n: int, restart_func: Callable | None = None) -> None:
        self.selected_index = (self.selected_index + n) % len(self.options)
        if self.callback:
            self.callback(self.value)
        if self.restart and restart_func:
            restart_func()

    def cycle_next(self, restart_func: Callable | None) -> None:
        """Move to the next option."""
        self.cycle(1, restart_func)

    def cycle_prev(self, restart_func: Callable | None) -> None:
        """Move to the previous option."""
        self.cycle(-1, restart_func)

    def draw_key(self, renderer: Renderer, *, color: pg.Color) -> None:
        draw_pos = self.pos_key
        if color == self.FONT_HIGHLIGHT_COLOR:
            draw_pos = self.pos_key[0] + 25, self.pos_key[1]

        surf = self.FONT.render(self.name, MENU_ANTI_ALIAS, color)
        self.key_rect = surf.get_rect(topleft=(draw_pos))

        renderer(surf, self.key_rect, unlit=True)

    def draw_value(self, renderer: Renderer, *, color: pg.Color) -> None:
        surf = self.FONT.render(self.text, MENU_ANTI_ALIAS, color)
        self.value_rect = surf.get_rect(topleft=self.pos_value)
        renderer(surf, self.value_rect, unlit=True)

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        color = self.FONT_HIGHLIGHT_COLOR if selected else self.FONT_COLOR
        self.draw_key(renderer, color=color)
        self.draw_value(renderer, color=color)

    def set_pos(self, pos) -> None:
        self.pos_key = pos
        self.pos_value = (pos[0] + self.MENU_BUTTON_OPTION_X, pos[1])

    def collidepoint(self, pos) -> bool:
        return self.key_rect.collidepoint(pos) or self.value_rect.collidepoint(pos)


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

        self.renderer: Renderer | None = None

        # buttons
        self.buttons: list[SelectorButton | ExitButton] = []
        self.add_button("music")
        self.add_button("sound effects")
        if sys.platform != "emscripten":
            self.add_button("fullscreen", callback=self._on_fullscreen_change)
            self.add_button("resolution scale", get_available_scales(), callback=self._on_resolution_scale_change)
            self.add_button("lighting", restart_needed=True)
        self.buttons.append(ExitButton())

        self.highlighted_button_index = 0
        self.load()

        # restart menu
        self.restart_question = False
        self.restart_submenu: RestartSubMenu | None = None

    def enter(self, transition_data, renderer: Renderer) -> None:
        """Store references for immediate setting changes."""
        super().enter(transition_data, renderer)
        self.renderer = renderer

    def _on_fullscreen_change(self, value) -> None:
        """Toggle fullscreen mode immediately."""
        if self.renderer is not None:
            self.renderer.toggle_fullscreen()

    def _on_resolution_scale_change(self, value: int) -> None:
        """Apply resolution scale change immediately."""
        if self.renderer is not None:
            self.renderer.set_scale_factor(value)

    def add_button(
        self,
        text: str,
        options: Sequence[str | int] = ("off", "on"),
        *,
        restart_needed: bool = False,
        callback: Callable | None = None,
    ) -> None:
        button = SelectorButton(text, options=options, restart=restart_needed, callback=callback)
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
