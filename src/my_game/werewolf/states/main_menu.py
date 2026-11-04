import random
from enum import Enum

import pygame as pg

from my_game.core.gl_renderer import GLRenderer
from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData
from my_game.constants import *

class MainMenuButtons():
    def __init__(self, font, text, pos, selected, next_state) -> None:
        self.text = text
        self.selected = selected
        self.font_color = "white"
        self.font = font
        self.pos = pos
        self.next_state = next_state

        #shapes
        self.surf = self.font.render(self.text, True, pg.Color("white"))
        self.rect = self.surf.get_rect(topleft=pos)

    def draw(self, surface, gl_renderer: GLRenderer | None = None) -> None:
        draw_pos = self.pos
        if self.selected:
            self.font_color = "yellow"
            draw_pos = self.pos[0]+25, self.pos[1]
        else:
            self.font_color = "white"
        self.surf = self.font.render(self.text, True, pg.Color(self.font_color))
        self.rect = self.surf.get_rect(topleft=(draw_pos))


        if gl_renderer:
            gl_renderer.blit_to_unlit(self.surf, self.rect)
        else:
            surface.blit(self.surf, self.rect)


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        super().__init__()

        #background
        self.background = Images.TEST_BACKGROUND.load()

        #text
        self.FONT = Fonts.PICO8.load(24)
        self.TITLE_FONT = Fonts.PICO8.load(60)
        self.anti_alias = True

        #title
        title = "The Beast of \nTemerev"
        self.title_surface = self.TITLE_FONT.render(title, self.anti_alias, pg.Color("white"))
        self.title_rect = self.title_surface.get_rect(topleft=(50,50))

        #buttons
        self.buttons = [
            MainMenuButtons(self.FONT, "Start", (75, 200), True, WerewolfState.MAIN_MENU),
            MainMenuButtons(self.FONT, "Load", (75, 250), False, WerewolfState.MAIN_MENU),
            MainMenuButtons(self.FONT, "Options", (75, 300), False, WerewolfState.MAIN_MENU),
            MainMenuButtons(self.FONT, "Exit", (75, 350), False, WerewolfState.MAIN_MENU)
        ]
        self.button_index = 0
        
        

    def enter(
        self,
        surface_rect: pg.Rect,
        transition_data: WerewolfTransitionData,
        gl_renderer: GLRenderer | None = None,
    ) -> None:
        super().enter(surface_rect, transition_data, gl_renderer)
        if gl_renderer:
            gl_renderer.set_light_position(0.5, 0.19)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if  Action.UI_SELECT in actions:
            self.done = True
            self.next_state = self.buttons[self.button_index].next_state

        if  Action.UP in actions:
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index - 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True

        if  Action.DOWN in actions:
            self.buttons[self.button_index].selected = False
            self.button_index = (self.button_index + 1) % len(self.buttons)
            self.buttons[self.button_index].selected = True

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, surface: pg.Surface, dt: float, gl_renderer: GLRenderer | None = None) -> None:

        if gl_renderer:
            gl_renderer.blit_to_lit(
                gl_renderer.resize_surface_to_fit(self.background), surface.get_rect(),
            )
            gl_renderer.blit_to_unlit(self.title_surface, self.title_rect)
            
        else:
            pass

        for button in self.buttons:
            button.draw(surface, gl_renderer)