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
    def __init__(self, font, text, pos, next_state, selected) -> None:
        self.text = text
        self.selected = selected
        self.font_color = "white"
        self.font = font
        self.pos = pos
        self.next_state = next_state
        self.antialias = True

        # shapes
        self.surf = self.font.render(self.text, self.antialias, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=pos)

    def draw(self, surface, gl_renderer: GLRenderer | None = None) -> None:
        draw_pos = self.pos
        if self.selected:
            self.font_color = "yellow"
            draw_pos = self.pos[0] + 25, self.pos[1]
        else:
            self.font_color = "white"
        self.surf = self.font.render(self.text, self.antialias, pg.Color(self.font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))

        if gl_renderer:
            gl_renderer.blit_to_unlit(self.surf, self.rect)
        else:
            surface.blit(self.surf, self.rect)


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        super().__init__()

        # background
        self.background_color = pg.Color("gray20")
        self.background = Images.TEST_BACKGROUND.load()

        # text
        self.FONT = Fonts.PICO8.load(24)
        self.TITLE_FONT = Fonts.PICO8.load(60)
        self.anti_alias = True

        # title
        title = "The Beast of \nTemerev"
        self.title_surface = self.TITLE_FONT.render(title, self.anti_alias, pg.Color("white"))
        self.title_rect = self.title_surface.get_rect(topleft=(50, 50))

        # buttons
        self.buttons = [
            MainMenuButton(self.FONT, "Start", (75, 200), WerewolfState.MAIN_MENU, selected=True),
            MainMenuButton(self.FONT, "Load", (75, 250), WerewolfState.MAIN_MENU, selected=False),
            MainMenuButton(self.FONT, "Options", (75, 300), WerewolfState.MAIN_MENU, selected=False),
            MainMenuButton(self.FONT, "Exit", (75, 350), WerewolfState.MAIN_MENU, selected=False),
        ]
        self.button_index = 0

        # timer
        self.stick_time = pg.time.get_ticks()
        self.first_time = pg.time.get_ticks()
        self.stick_delay = 125
        self.first_delay = 250

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = self.buttons[self.button_index].next_state

        if Action.UP in actions:
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index - 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True
            self.stick_time = pg.time.get_ticks()
            self.first_time = pg.time.get_ticks()

        if Action.DOWN in actions:
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index + 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True
            self.stick_time = pg.time.get_ticks()
            self.first_time = pg.time.get_ticks()

        if Action.MOUSE_SELECT in actions:
            pos = pg.mouse.get_pos()
            for button in self.buttons:
                if button.rect.collidepoint(pos):
                    self.done = True
                    self.next_state = button.next_state

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        up_power = input_state.get_action_strength(Action.UP)
        down_power = input_state.get_action_strength(Action.DOWN)

        if (
            up_power > 0
            and pg.time.get_ticks() - self.first_time >= self.first_delay
            and pg.time.get_ticks() - self.stick_time >= self.stick_delay * (1 / up_power)
        ):
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index - 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True
            self.stick_time = pg.time.get_ticks()

        elif (
            down_power > 0
            and pg.time.get_ticks() - self.first_time >= self.first_delay
            and pg.time.get_ticks() - self.stick_time >= self.stick_delay * (1 / down_power)
        ):
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index + 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True
            self.stick_time = pg.time.get_ticks()

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

        for button in self.buttons:
            button.draw(surface, gl_renderer)
