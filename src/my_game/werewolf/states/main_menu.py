from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class MainMenuButton:
    def __init__(self, font, text, next_state: WerewolfState | None) -> None:
        self.text = text
        self.font = font
        self.pos = (0, 0)
        self.next_state = next_state
        self.antialias = True

        # shapes
        self.surf = self.font.render(self.text, self.antialias, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        draw_pos = self.pos
        font_color = "white"
        if selected:
            font_color = "yellow"
            draw_pos = self.pos[0] + 25, self.pos[1]

        self.surf = self.font.render(self.text, self.antialias, pg.Color(font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))

        renderer(self.surf, self.rect, unlit=True)

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
            MainMenuButton(self.FONT, "Start", WerewolfState.TEST_ROOM),
            MainMenuButton(self.FONT, "Load", WerewolfState.RENDER_TEST),
            MainMenuButton(self.FONT, "Options", WerewolfState.MAIN_MENU),
            MainMenuButton(self.FONT, "Exit", None),
        ]
        self.button_index = 0

        for i in range(len(self.buttons)):
            self.buttons[i].set_pos((self.BUTTON_OFFSET_X, self.BUTTON_OFFSET_Y + (i * self.BUTTON_SPACING_Y)))

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = self.buttons[self.button_index].next_state
            if not self.next_state:
                self.quit = True

        if Action.UP in actions:
            self.button_index = (self.button_index - 1) % len(self.buttons)

        if Action.DOWN in actions:
            self.button_index = (self.button_index + 1) % len(self.buttons)

        if Action.MOUSE_SELECT in actions:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    self.done = True
                    self.next_state = button.next_state
                    if not self.next_state:
                        self.quit = True

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, renderer: Renderer, dt: float) -> None:
        renderer.fill(self.background_color)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.title_surface, self.title_rect, unlit=True)

        for i in range(len(self.buttons)):
            self.buttons[i].draw(renderer, selected=self.button_index == i)
