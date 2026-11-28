import sys
from enum import Enum

import pygame as pg

from my_game.constants import MENU_ANTI_ALIAS, MENU_BUTTON_OFFSET_X, MENU_BUTTON_SPACING_Y, MENU_FONT_SIZE
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

        # shapes
        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=self.pos)

    def draw(self, renderer: Renderer, *, selected: bool) -> None:
        draw_pos = self.pos
        font_color = "white"
        if selected:
            font_color = "yellow"
            draw_pos = self.pos[0] + 25 // 2, self.pos[1]

        self.surf = self.font.render(self.text, MENU_ANTI_ALIAS, pg.Color(font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))

        renderer(self.surf, self.rect, unlit=True)

    def set_pos(self, pos):
        self.pos = pos
        self.rect = self.surf.get_rect(topleft=pos)


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    TITLE_FONT_SIZE = 32
    MENU_BUTTON_OFFSET_Y = 200 // 2
    CLOUD_SPEED = 5

    def __init__(self) -> None:
        super().__init__()

        self.FONT = Fonts.PICO8.load(MENU_FONT_SIZE)
        self.TITLE_FONT = Fonts.BITMGOTHIC.load(self.TITLE_FONT_SIZE)

        # background
        self.clouds = Images.BACKGROUND_CLOUDS.load()
        self.clouds_rect = self.clouds.get_rect()
        self.total_dt = 0.0

        # title
        title = "The Beast of \nTemerev"
        self.title_surface = self.TITLE_FONT.render(title, MENU_ANTI_ALIAS, pg.Color("white"))
        self.title_rect = self.title_surface.get_rect(topleft=(50 // 2, 50 // 2))

        # buttons
        self.buttons = [
            MainMenuButton(self.FONT, "start", WerewolfState.ROOM),
            MainMenuButton(self.FONT, "enter test room", WerewolfState.TEST_ROOM),
            MainMenuButton(self.FONT, "load", WerewolfState.RENDER_TEST),
            MainMenuButton(self.FONT, "options", WerewolfState.OPTIONS_MENU),
        ]
        if sys.platform != "emscripten":
            self.buttons.append(MainMenuButton(self.FONT, "exit", None))
        self.button_index = 0

        for i in range(len(self.buttons)):
            self.buttons[i].set_pos((MENU_BUTTON_OFFSET_X, self.MENU_BUTTON_OFFSET_Y + (i * MENU_BUTTON_SPACING_Y)))

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

    def update(self, dt: float, input_state: InputState) -> None:
        self.total_dt += dt
        self.clouds_rect.x = (
            -self.total_dt * self.CLOUD_SPEED % self.clouds.get_width()
        )  # Move clouds to the left over time

    def draw(self, renderer: Renderer, dt: float) -> None:
        second_clouds_rect = self.clouds_rect.copy()
        second_clouds_rect.x -= self.clouds.get_width()

        renderer(Images.BACKGROUND_NIGHTSKY.load())
        renderer(Images.BACKGROUND_FULLMOON.load())
        renderer(self.clouds, self.clouds_rect)
        renderer(self.clouds, second_clouds_rect)
        renderer(Images.TITLE_SCREEN.load())

        renderer(self.title_surface, self.title_rect, unlit=True)

        for i in range(len(self.buttons)):
            self.buttons[i].draw(renderer, selected=self.button_index == i)
