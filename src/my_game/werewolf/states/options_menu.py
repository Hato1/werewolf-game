from enum import Enum

import pygame as pg

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class ToggleButton:
    def __init__(self, font, true, false, *, status: bool):
        self.selected = False
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
        self.selected = not self.selected

    def draw(self, renderer: Renderer, *, selected) -> None:
        font_color = "white"
        if selected:
            font_color = "yellow"

        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color(font_color))

        renderer(self.surf, self.rect, unlit=True)

    def set_pos(self, pos):
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)


class OptionsMenuButton:
    def __init__(self, font, text) -> None:
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

    def set_pos(self, pos):
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)


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
        self.buttons: list[tuple[OptionsMenuButton, ToggleButton | None]] = [
            (OptionsMenuButton(self.FONT, "Music"), ToggleButton(self.FONT, "On", "Off", status=True)),
            (OptionsMenuButton(self.FONT, "Sound Effects"), ToggleButton(self.FONT, "On", "Off", status=True)),
            (OptionsMenuButton(self.FONT, "Lighting"), ToggleButton(self.FONT, "On", "Off", status=True)),
            (OptionsMenuButton(self.FONT, "Exit"), None),
        ]
        self.button_x = 0
        self.button_y = 0

        for i, (button, toggle) in enumerate(self.buttons):
            button.set_pos((MENU_BUTTON_OFFSET_X, self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y)))
            if toggle:
                toggle.set_pos(
                    (
                        MENU_BUTTON_OFFSET_X + self.MENU_BUTTON_OPTION_X,
                        self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y),
                    )
                )

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UP in actions and self.button_x == 0:
            self.button_y = (self.button_y - 1) % len(self.buttons)

        if Action.DOWN in actions and self.button_x == 0:
            self.button_y = (self.button_y + 1) % len(self.buttons)

        if Action.UI_SELECT in actions:
            if self.button_x == 0 and not self.buttons[self.button_y][1]:
                self.done = True
                self.next_state = WerewolfState.MAIN_MENU

        if Action.MOUSE_SELECT in actions:
            for button in self.buttons:
                if button[0].rect.collidepoint(event.pos):
                    pass

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, renderer: Renderer, dt: float) -> None:
        renderer.fill(self.background_color)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.title_surface, self.title_rect, unlit=True)

        for i, (button, toggle) in enumerate(self.buttons):
            button.draw(renderer, selected=self.button_y == i)
            if toggle:
                toggle.draw(renderer, selected=self.button_y == i and self.button_x == 1)
