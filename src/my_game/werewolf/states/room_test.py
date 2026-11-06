"""A simple room scene for testing room rendering.

VERY UGLY WIP, DO NOT READ
"""

from enum import Enum

import pygame as pg

from my_game.constants import SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.room import Prop, Room
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class RoomTest(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        super().__init__()
        background = pg.transform.scale(Images.TEST_ROOM_BACKGROUND.load(), SCREEN_SIZE)
        self.room = Room(
            "Test Room",
            "A room for testing the room rendering system.",
            [Prop("Background", "The room background.", background)],
            [],
            [],
        )
        self.prompt_font = Fonts.PICO8.load(12)
        self.prompt = self.prompt_font.render(
            "Test room - press Esc to return", antialias=True, color=pg.Color("white")
        )
        self.prompt_rect = self.prompt.get_rect(topleft=(16, 16))

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        pass

    def draw(self, renderer: Renderer, dt: float) -> None:
        self.room.draw(renderer)
        renderer(self.prompt, self.prompt_rect, unlit=True)
