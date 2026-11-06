from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class RenderTest(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        prompt_font = Fonts.PICO8.load(12)
        self.prompt = prompt_font.render("Render Test - press Esc to return", antialias=True, color=pg.Color("white"))
        self.prompt_rect = self.prompt.get_rect(topleft=(16, 16))
        self.quit = False
        self.done = False
        self.background = Images.load(Images.TEST_ROOM_BACKGROUND)
        self.light_mask = Images.load(Images.TEST_SHADOW)

    def draw(self, renderer: Renderer, dt: float) -> None:
        # renderer(background)
        # super().draw(renderer, dt)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.light_mask, self.light_mask.get_rect(), to_lightmask=True, fit=True)
        renderer(self.prompt, self.prompt_rect, unlit=True)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass
