from enum import Enum

import pygame as pg

from my_game.core.gl_renderer import GLRenderer
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
        self.normal_map = Images.load(Images.TEST_NORMALS)
        self.light_z = 0.5

    def draw(self, renderer: Renderer, dt: float) -> None:
        # renderer(background)
        # super().draw(renderer, dt)
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.light_mask, self.light_mask.get_rect(), draw_mode=1, fit=True)
        renderer(self.normal_map, self.normal_map.get_rect(), draw_mode=2, fit=True)
        renderer(self.prompt, self.prompt_rect, unlit=True)
        GLRenderer.light_z = self.light_z

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        # move mouse z position
        if Action.UP in input_state.held_actions:
            self.light_z += dt
        if Action.DOWN in input_state.held_actions:
            self.light_z -= dt
        self.light_z = max(-1, min(1, self.light_z))
