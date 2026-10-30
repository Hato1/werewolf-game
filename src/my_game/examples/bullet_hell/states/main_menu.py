from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.examples.bullet_hell.assets import Fonts
from my_game.examples.bullet_hell.inputs import Action
from my_game.examples.bullet_hell.state_data import BulletHellState, BulletHellTransitionData


class MainMenu(State[BulletHellState, BulletHellTransitionData]):
    FONT = Fonts.PICO8.load(6)

    def __init__(self) -> None:
        super().__init__()

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = BulletHellState.GAME

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, surface: pg.Surface, dt: float) -> None:
        surface.fill(pg.Color("gray20"))

        text = "press enter to start"
        anti_alias = True
        text_surface = self.FONT.render(text, anti_alias, pg.Color("yellow"))
        text_rect = text_surface.get_rect(center=(surface.get_rect().center))
        surface.blit(text_surface, text_rect)
