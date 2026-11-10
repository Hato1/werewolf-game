"""A simple room scene for testing room rendering."""

from enum import Enum

import pygame as pg

from my_game.core.renderer import Renderer
from my_game.werewolf.assets import Fonts, Rooms
from my_game.werewolf.inputs import Action
from my_game.werewolf.room.loaders import load_room
from my_game.werewolf.state_data import WerewolfState
from my_game.werewolf.states.room_state import RoomState


class RoomTest(RoomState):
    def __init__(self) -> None:
        super().__init__(load_room(Rooms.TEST_ROOM))
        prompt_font = Fonts.PICO8.load(12)
        self.prompt = prompt_font.render("Test room - press Esc to return", antialias=True, color=pg.Color("white"))
        self.prompt_rect = self.prompt.get_rect(topleft=(16, 16))

    def draw(self, renderer: Renderer, dt: float) -> None:
        super().draw(renderer, dt)
        renderer(self.prompt, self.prompt_rect, unlit=True)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU
        else:
            super().handle_event(actions, event)
