"""State representing rooms in the game.

This state handles displaying a room, responding to prop clicks,
showing timed messages, and handling room transitions.
"""

from collections.abc import Callable
from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Dialogue, Fonts
from my_game.werewolf.inputs import Action
from my_game.werewolf.interactions.definitions import ObjectKind, Verb
from my_game.werewolf.interactions.executor import InteractionSystem, InteractionTarget
from my_game.werewolf.interactions.flags import Flags
from my_game.werewolf.room import props, rooms
from my_game.werewolf.room.characters import PLAYER
from my_game.werewolf.room.loaders import RoomData
from my_game.werewolf.room.models import Character, Player, Prop, Region, Room
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData
from my_game.werewolf.ui.player_ui import UIPanel


def get_object_kind(target: object) -> ObjectKind:
    if isinstance(target, Prop):
        return ObjectKind.PROP
    elif isinstance(target, Character):
        return ObjectKind.CHARACTER
    elif isinstance(target, Region):
        return ObjectKind.REGION
    else:
        raise TypeError(f"Unsupported type {type(target)} from given target: {target}")


class RoomState(State[WerewolfState, WerewolfTransitionData]):
    MESSAGE_DURATION_MS = 3000
    MESSAGE_FONT_SIZE = 18
    MESSAGE_COLOR = pg.Color("white")
    # Distance from bottom of the screen to display the message in pixels.
    MESSAGE_DISPLAY_OFFSET = 8

    def __init__(self, room: RoomData | None = None) -> None:
        super().__init__()
        self.room = Room.from_room_data(room or rooms.INN)
        self.message_font = Fonts.PICO8.load(self.MESSAGE_FONT_SIZE)
        # By having only one message surface, we ensure that only one message is shown at a time.
        self.message_surface: pg.Surface | None = None
        self.message_expires_at = 0
        self.player = Player.from_character_data(PLAYER)
        self.ui = UIPanel()
        self.interactions = InteractionSystem()
        self.renderer: Renderer
        self.flags = Flags()
        self.active_region_ids: set[str] = set()
        self._reset_proximity_state()

    def enter(self, transition_data: WerewolfTransitionData, renderer: Renderer) -> None:
        super().enter(transition_data, renderer)
        self.renderer = renderer
        if transition_data.flags is not None:
            self.flags = Flags.from_mapping(transition_data.flags)
        self.room.on_enter(renderer)

    def exit(self) -> WerewolfTransitionData:
        """Persist flags before leaving this state."""
        self.transition_data.flags = self.flags.as_dict()
        return super().exit()

    def change_room(self, room: RoomData) -> None:
        self.player.cancel_walk()
        self.room.on_exit(self.renderer)
        self.room = Room.from_room_data(room)
        self.room.on_enter(self.renderer)
        self._reset_proximity_state()

    def _reset_proximity_state(self) -> None:
        """Forget transient proximity state, treating points at the player's feet as occupied."""
        self.active_region_ids = set()

    def _dispatch_proximity(self, target: InteractionTarget, verb: Verb) -> None:
        """Dispatch a non-click interaction without falling back to a description."""
        self.interactions.dispatch(target, get_object_kind(target), verb, self)

    def _update_proximity_interactions(self) -> None:
        """Fire ENTER/EXIT interactions as the player moves between regions.

        TODO: Add priority handling for overlapping regions.
        """
        room = self.room
        regions = tuple(room.regions)
        position = self.player.position_int

        current_regions = {region.id for region in regions if region.contains_point(position)}
        for region in regions:
            # If the room has changed during iteration, stop processing.
            if self.room is not room:
                return
            if region.id in current_regions and region.id not in self.active_region_ids:
                region.enter()
                self._dispatch_proximity(region, Verb.ENTER)
            elif region.id not in current_regions and region.id in self.active_region_ids:
                region.exit()
                self._dispatch_proximity(region, Verb.EXIT)
        if self.room is not room:
            return
        self.active_region_ids = current_regions

    def enter_dialogue_state(self, dialogue: Dialogue) -> None:
        """Enter a dialogue state with the given dialogue."""
        raise NotImplementedError()

        # Add to transition data here.
        self.transition_data.dialogue = dialogue
        self.transition_data.flags = self.flags.as_dict()

        self.next_state = WerewolfState.DIALOGUE
        self.done = True

    def show_message(self, text: str) -> None:
        self.message_surface = self.message_font.render(text, antialias=True, color=self.MESSAGE_COLOR)
        self.message_expires_at = pg.time.get_ticks() + self.MESSAGE_DURATION_MS

    def get_flag(self, flag: str) -> bool:
        """Return whether a runtime flag is set."""
        return self.flags.get(flag)

    def set_flag(self, flag: str, *, value: bool) -> None:
        """Set a runtime flag."""
        self.flags.set(flag, value=value)

    def walk_to(self, target: InteractionTarget, on_arrive: Callable[[], None]) -> None:
        """Walk the player up to an interaction target before continuing its effects."""
        rect = getattr(target, "rect", None)
        if not isinstance(rect, pg.Rect):
            raise TypeError(f"Interaction target {target!r} has no walkable rect.")
        self.player.walk_to(rect, on_arrive)

    def interact_with(self, target: InteractionTarget) -> None:
        """Dispatch an INTERACT interaction on a room object."""
        kind = get_object_kind(target)
        self.interactions.dispatch(target, kind, Verb.INTERACT, self)

    def handle_mouse_select(self, pos: tuple[int, int]) -> None:
        self.player.cancel_walk()
        if clicked_object := self.room.get_clicked(pos):
            self.interact_with(clicked_object)

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
        elif Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

    def update(self, dt: float, input_state: InputState) -> None:
        self.player.update(dt, input_state)
        self.room.update(dt, input_state)
        self._update_proximity_interactions()
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
