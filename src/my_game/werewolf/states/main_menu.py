import random
from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


def random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return (r, g, b)


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    FONT = Fonts.PICO8.load(6)

    def __init__(self) -> None:
        super().__init__()
        self.background_color = pg.Color("gray20")

    def enter(
        self,
        surface_rect: pg.Rect,
        transition_data: WerewolfTransitionData,
    ) -> None:
        super().enter(surface_rect, transition_data)
        self.background_color = random_color()

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, surface: pg.Surface, dt: float) -> None:
        surface.fill(self.background_color)

        text = "press enter to start"
        anti_alias = True
        text_surface = self.FONT.render(text, anti_alias, pg.Color("yellow"))
        text_rect = text_surface.get_rect(center=(surface.get_rect().center))
        surface.blit(text_surface, text_rect)
