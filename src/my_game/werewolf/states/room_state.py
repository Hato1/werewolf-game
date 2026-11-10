"""State representing rooms in the game.

This state handles displaying a room, responding to prop clicks,
showing timed messages, and handling room transitions.
"""

from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts
from my_game.werewolf.inputs import Action
from my_game.werewolf.room import rooms
from my_game.werewolf.room.loaders import RoomData
from my_game.werewolf.room.models import Room
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class RoomState(State[WerewolfState, WerewolfTransitionData]):
    MESSAGE_DURATION_MS = 3000
    MESSAGE_FONT_SIZE = 36
    MESSAGE_COLOR = pg.Color("white")
    # Distance from bottom of the screen to display the message in pixels.
    MESSAGE_DISPLAY_OFFSET = 16

    def __init__(self, room: RoomData) -> None:
        super().__init__()
        self.room = Room.from_room_data(room)
        self.message_font = Fonts.PICO8.load(self.MESSAGE_FONT_SIZE)
        # By having only one message surface, we ensure that only one message is shown at a time.
        self.message_surface: pg.Surface | None = None
        self.message_expires_at = 0

    def change_room(self, room: RoomData) -> None:
        self.room.on_exit()
        self.room = Room.from_room_data(room)
        self.room.on_enter()

    def show_message(self, text: str) -> None:
        self.message_surface = self.message_font.render(text, antialias=True, color=self.MESSAGE_COLOR)
        self.message_expires_at = pg.time.get_ticks() + self.MESSAGE_DURATION_MS

    def on_prop_clicked(self, prop_description: str) -> None:
        """Hook for subclasses; by default the prop's description is shown."""
        self.show_message(prop_description)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.MOUSE_SELECT in actions:
            prop = self.room.get_clicked_prop(event.pos)
            if prop is not None:
                self.on_prop_clicked(prop.description)
        elif Action.DEBUG_ROOM_1 in actions:
            self.change_room(rooms.CHURCH_CEMETARY)
        elif Action.DEBUG_ROOM_2 in actions:
            self.change_room(rooms.INN)
        elif Action.DEBUG_ROOM_3 in actions:
            self.change_room(rooms.TOWN_CENTER)
        elif Action.DEBUG_ROOM_4 in actions:
            self.change_room(rooms.TOWN_ENTRANCE)
        elif Action.DEBUG_ROOM_5 in actions:
            self.change_room(rooms.TOWN_HALL)
        elif Action.DEBUG_ROOM_6 in actions:
            self.change_room(rooms.WOODS)

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        if self.message_surface is not None and pg.time.get_ticks() >= self.message_expires_at:
            self.message_surface = None

    def draw(self, renderer: Renderer, dt: float) -> None:
        self.room.draw(renderer)
        if self.message_surface is not None:
            message_rect = self.message_surface.get_rect(
                midbottom=(renderer.rect.centerx, renderer.rect.bottom - self.MESSAGE_DISPLAY_OFFSET)
            )
            renderer(self.message_surface, message_rect, unlit=True)
