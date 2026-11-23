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
from my_game.werewolf.data.data_models import SaveData
from my_game.werewolf.inputs import Action
from my_game.werewolf.room import props, rooms
from my_game.werewolf.room.characters import PLAYER
from my_game.werewolf.room.loaders import RoomData
from my_game.werewolf.room.models import Player, Prop, Room
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData
from my_game.werewolf.ui.player_ui import UIPanel


class RoomState(State[WerewolfState, WerewolfTransitionData]):
    MESSAGE_DURATION_MS = 3000
    MESSAGE_FONT_SIZE = 18
    MESSAGE_COLOR = pg.Color("white")
    # Distance from bottom of the screen to display the message in pixels.
    MESSAGE_DISPLAY_OFFSET = 8

    def __init__(self, room: RoomData) -> None:
        super().__init__()
        self.room = Room.from_room_data(room)
        self.message_font = Fonts.PICO8.load(self.MESSAGE_FONT_SIZE)
        # By having only one message surface, we ensure that only one message is shown at a time.
        self.message_surface: pg.Surface | None = None
        self.message_expires_at = 0
        self.player = Player.from_character_data(PLAYER)
        self.ui = UIPanel()
        SaveData.current_room = room.name

    def change_room(self, room: RoomData) -> None:
        self.player.cancel_walk()
        self.room.on_exit()
        self.room = Room.from_room_data(room)
        self.room.on_enter()
        SaveData.current_room = room.name

    def show_message(self, text: str) -> None:
        self.message_surface = self.message_font.render(text, antialias=True, color=self.MESSAGE_COLOR)
        self.message_expires_at = pg.time.get_ticks() + self.MESSAGE_DURATION_MS

    def on_prop_clicked(self, prop: Prop) -> None:
        """inventory items added to player inventory, based on new pickup_on_click property"""
        print(f"pickup_on_click:{prop.pickup_on_click}")
        if prop.pickup_on_click:
            self.ui.inventory.add_item(prop)
            self.show_message(prop.description)

        """Hook for subclasses; by default the prop's description is shown."""
        if prop.name == props.GRAVEYARD_CHAINS.name:
            self.change_room(rooms.CHURCH_CEMETARY)
        else:
            self.show_message(prop.description)

    def handle_mouse_select(self, pos: tuple[int, int]) -> None:
        prop = self.room.get_clicked_prop(pos)
        self.player.cancel_walk()
        if prop is None:
            return
        if prop.walk_to_interact:
            self.player.walk_to(prop.rect, lambda: self.on_prop_clicked(prop))
        else:
            self.on_prop_clicked(prop)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        """Can also have custom functions passed in, if we want to do that later for some reason"""
        self.ui.handle_mouse(actions, event)

        if Action.MOUSE_SELECT in actions:
            self.handle_mouse_select(event.pos)
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
        elif Action.DEBUG_ADD_ITEM in actions:
            # Example: Add a test item to the inventory
            test_prop = Prop.from_prop_data(props.GRAVEYARD_CHAINS)
            self.ui.inventory.add_item(test_prop)

    def update(self, dt: float, input_state: InputState) -> None:
        self.player.update(dt, input_state)
        self.room.update(dt, input_state)
        if self.message_surface is not None and pg.time.get_ticks() >= self.message_expires_at:
            self.message_surface = None

    def draw(self, renderer: Renderer, dt: float) -> None:
        self.room.draw(renderer)
        self.player.draw(renderer)
        # Render UI before message so messages can appear in text area, rather than behind it
        self.ui.draw(renderer)
        if self.message_surface is not None:
            message_rect = self.message_surface.get_rect(
                midbottom=(renderer.rect.centerx, renderer.rect.bottom - self.MESSAGE_DISPLAY_OFFSET)
            )
            renderer(self.message_surface, message_rect, unlit=True)
        self.ui.draw(renderer)
