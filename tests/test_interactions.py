"""Tests for data-driven interactions with room objects."""

import ast
from dataclasses import replace
from enum import Enum

import pygame as pg
import pytest

from my_game.core.input_manager import InputManager, InputState
from my_game.core.renderer import Renderer
from my_game.werewolf.assets import Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.interactions.definitions import ChangeRoom, Describe, InteractionData, Verb
from my_game.werewolf.room import props, rooms
from my_game.werewolf.room.editor_data import update_room_source
from my_game.werewolf.room.loaders import CharacterData, PropData, RoomData
from my_game.werewolf.room.models import Room
from my_game.werewolf.state_data import WerewolfTransitionData
from my_game.werewolf.states.room_state import RoomState


def make_room_state(room: RoomData) -> RoomState:
    """Create a room state whose renderer hooks are available for room changes."""
    pg.init()
    pg.display.set_mode((1, 1))
    input_manager = InputManager(Enum)
    renderer = Renderer(input_manager=input_manager, open_gl=False, scale_factor=1, fullscreen=False)
    room_state = RoomState(room)
    room_state.enter(WerewolfTransitionData(), renderer)
    return room_state


def click(room_state: RoomState, position: tuple[int, int]) -> None:
    """Send a mouse-select event at ``position`` to the room state."""
    room_state.handle_event(
        {Action.MOUSE_SELECT},
        pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=position),
    )


def finish_player_walk(room_state: RoomState) -> None:
    """Advance the room until a deferred interaction completes."""
    idle: InputState = InputState(frozenset(), {})
    assert room_state.player.target is not None
    for _ in range(300):
        room_state.update(0.05, idle)
        if room_state.player.target is None:
            break
    assert room_state.player.target is None


def test_chains_interaction_changes_room() -> None:
    prop = PropData(
        "chains",
        "chains",
        "Teleporting chains",
        image=props.GRAVEYARD_CHAINS.image,
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(ChangeRoom(room_id="church_cemetary"),)),),
    )
    room_state = make_room_state(RoomData("Chain room", "Chain room", "A room with chains.", props=(prop,)))

    click(room_state, room_state.room.props[0].rect.center)
    # finish_player_walk(room_state)

    assert room_state.room is Room.from_room_data(rooms.CHURCH_CEMETARY)


def test_highest_priority_interaction_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(
        name="Prop",
        id="prop",
        description="A prop.",
        image=props.STUDIO.image,
        position=(100, 100),
        interactions=(
            InteractionData(verb=Verb.INTERACT, effects=(Describe("low priority"),), priority=0),
            InteractionData(verb=Verb.INTERACT, effects=(Describe("high priority"),), priority=10),
        ),
    )
    room_state = make_room_state(RoomData("Priority room", "Priority room", "A room with a prop.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["high priority"]


def test_prop_without_interactions_uses_its_description(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(name="Prop", id="prop", description="A plain prop.", image=props.STUDIO.image, position=(100, 100))
    room_state = make_room_state(RoomData("Description room", "Description room", "A room with a prop.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["A plain prop."]


def test_character_click_dispatches_its_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    character = CharacterData(
        name="NPC",
        description="An NPC.",
        image=Images.MC_IDLE,
        position=(100, 100),
        id="npc",
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(Describe("Hello!"),)),),
    )
    room_state = make_room_state(
        RoomData("Character room", "Character room", "A room with a character.", characters=(character,))
    )
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.characters[0].rect.center)

    assert messages == ["Hello!"]


def test_interaction_definitions_survive_editor_source_generation() -> None:
    prop = PropData(
        name="Chains",
        id="chains",
        description="Chains.",
        image=Images.CHAINS_1,
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(ChangeRoom(room_id="church_cemetary"),)),),
    )
    room = replace(RoomData(name="Test", description="Test room.", id="test_room"), props=(prop,))

    updated = update_room_source("ROOM = None\n", {"ROOM": room})
    ast.parse(updated)

    assert "Verb.INTERACT" in updated
    assert "ChangeRoom(" in updated
    assert "from my_game.werewolf.interactions.definitions import ChangeRoom, InteractionData, Verb" in updated
