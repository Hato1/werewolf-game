from enum import Enum

import pygame as pg

from my_game.constants import SCREEN_SIZE
from my_game.core.gl_renderer import GLRenderer
from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class MainMenuButton:
    def __init__(self, font, text, next_state) -> None:
        self.text = text
        self.font = font
        self.pos = (0, 0)
        self.next_state = next_state
        self.antialias = True

        # shapes
        self.surf = self.font.render(self.text, self.antialias, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    def draw(self, surface, selected, gl_renderer: GLRenderer | None = None) -> None:
        draw_pos = self.pos
        font_color = "white"
        if selected:
            font_color = "yellow"
            draw_pos = self.pos[0] + 25, self.pos[1]

        self.surf = self.font.render(self.text, self.antialias, pg.Color(font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))

        if gl_renderer:
            gl_renderer.blit_to_unlit(self.surf, self.rect)
        else:
            surface.blit(self.surf, self.rect)

    def set_pos(self, pos):
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    MENU_FONT_SIZE = 24
    TITLE_FONT_SIZE = 60
    BUTTON_OFFSET_X = 75
    BUTTON_OFFSET_Y = 200
    # Distance between buttons
    BUTTON_SPACING_Y = 50

    def __init__(self) -> None:
        super().__init__()

        # background
        self.background_color = pg.Color("gray20")
        self.background = Images.TEST_BACKGROUND.load()

        # text
        self.FONT = Fonts.PICO8.load(self.MENU_FONT_SIZE)
        self.TITLE_FONT = Fonts.PICO8.load(self.TITLE_FONT_SIZE)
        self.anti_alias = True

        # title
        title = "The Beast of \nTemerev"
        self.title_surface = self.TITLE_FONT.render(title, self.anti_alias, pg.Color("white"))
        self.title_rect = self.title_surface.get_rect(topleft=(50, 50))

        # buttons
        self.buttons = [
            MainMenuButton(self.FONT, "Start", WerewolfState.MAIN_MENU),
            MainMenuButton(self.FONT, "Load", WerewolfState.MAIN_MENU),
            MainMenuButton(self.FONT, "Options", WerewolfState.MAIN_MENU),
            MainMenuButton(self.FONT, "Exit", WerewolfState.MAIN_MENU),
        ]
        self.button_index = 0

        for i in range(len(self.buttons)):
            self.buttons[i].set_pos((self.BUTTON_OFFSET_X, self.BUTTON_OFFSET_Y + (i * self.BUTTON_SPACING_Y)))

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = self.buttons[self.button_index].next_state

        if Action.UP in actions:
            self.button_index = (self.button_index - 1) % len(self.buttons)

        if Action.DOWN in actions:
            self.button_index = (self.button_index + 1) % len(self.buttons)

        if Action.MOUSE_SELECT in actions:
            pos = pg.mouse.get_pos()
            for button in self.buttons:
                if button.rect.collidepoint(pos):
                    self.done = True
                    self.next_state = button.next_state

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, surface: pg.Surface, dt: float, gl_renderer: GLRenderer | None = None) -> None:

        surface.fill(self.background_color)

        if gl_renderer:
            gl_renderer.blit_to_lit(surface, surface.get_rect())
            gl_renderer.blit_to_lit(
                gl_renderer.resize_surface_to_fit(self.background),
                surface.get_rect(),
            )
            gl_renderer.blit_to_unlit(self.title_surface, self.title_rect)

        else:
            background = pg.transform.scale(self.background, SCREEN_SIZE)
            surface.blit(background, surface.get_rect())
            surface.blit(self.title_surface, self.title_rect)

        for i in range(len(self.buttons)):
            self.buttons[i].draw(surface, self.button_index == i, gl_renderer)
