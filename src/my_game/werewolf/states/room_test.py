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
    MESSAGE_DURATION_MS = 3000
    STUDIO_SCALE = 0.1

    def __init__(self) -> None:
        super().__init__()
        background = pg.transform.scale(Images.TEST_ROOM_BACKGROUND.load(), SCREEN_SIZE)
        studio_sprite = pg.transform.smoothscale_by(Images.STUDIO.load(), self.STUDIO_SCALE)
        studio = Prop("Studio", "a tiny studio model.", studio_sprite)
        studio.position = (SCREEN_SIZE[0] - studio_sprite.get_width() - 48, SCREEN_SIZE[1] - studio_sprite.get_height())
        background_prop = Prop("Background", "The room background.", background)
        background_prop.clickable = False
        self.room = Room(
            "Test Room",
            "A room for testing the room rendering system.",
            [background_prop, studio],
            [],
            [],
        )
        self.prompt_font = Fonts.PICO8.load(12)
        self.prompt = self.prompt_font.render(
            "Test room - press Esc to return", antialias=True, color=pg.Color("white")
        )
        self.prompt_rect = self.prompt.get_rect(topleft=(16, 16))
        self.message_surface: pg.Surface | None = None
        self.message_expires_at = 0

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU
        elif Action.MOUSE_SELECT in actions:
            prop = self.room.get_clicked_prop(event.pos)
            if prop is not None:
                self.message_surface = Fonts.PICO8.load(36).render(
                    prop.description, antialias=True, color=pg.Color("white")
                )
                self.message_expires_at = pg.time.get_ticks() + self.MESSAGE_DURATION_MS

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        if self.message_surface is not None and pg.time.get_ticks() >= self.message_expires_at:
            self.message_surface = None

    def draw(self, renderer: Renderer, dt: float) -> None:
        self.room.draw(renderer)
        renderer(self.prompt, self.prompt_rect, unlit=True)
        if self.message_surface is not None:
            message_rect = self.message_surface.get_rect(midbottom=(renderer.rect.centerx, renderer.rect.bottom - 16))
            renderer(self.message_surface, message_rect, unlit=True)
