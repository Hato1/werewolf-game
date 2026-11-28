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
from my_game.werewolf.interactions.definitions import (
    AllOf,
    AnyOf,
    ChangeRoom,
    Describe,
    FlagIs,
    InteractionData,
    Not,
    SetFlag,
    Verb,
    WalkTo,
)
from my_game.werewolf.room import props, rooms
from my_game.werewolf.room.editor_data import update_room_source
from my_game.werewolf.room.geometry import point_in_polygon
from my_game.werewolf.room.loaders import CharacterData, PropData, RegionData, RoomData
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
        id="chains",
        description="Teleporting chains",
        image=props.GRAVEYARD_CHAINS.image,
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(ChangeRoom(room_id="church_cemetary"),)),),
    )
    room_state = make_room_state(RoomData(id="chain_room", description="A room with chains.", props=(prop,)))

    click(room_state, room_state.room.props[0].rect.center)
    # finish_player_walk(room_state)

    assert room_state.room is Room.from_room_data(rooms.CHURCH_CEMETARY)


def test_highest_priority_interaction_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(
        id="prop",
        description="A prop.",
        image=props.STUDIO.image,
        position=(100, 100),
        interactions=(
            InteractionData(verb=Verb.INTERACT, effects=(Describe("low priority"),), priority=0),
            InteractionData(verb=Verb.INTERACT, effects=(Describe("high priority"),), priority=10),
        ),
    )
    room_state = make_room_state(RoomData(id="priority_room", description="A room with a prop.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["high priority"]


def test_prop_without_interactions_uses_its_description(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(id="prop", description="A plain prop.", image=props.STUDIO.image, position=(100, 100))
    room_state = make_room_state(RoomData(id="description_room", description="A room with a prop.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["A plain prop."]


def test_character_click_dispatches_its_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    character = CharacterData(
        description="An NPC.",
        image=Images.MC_IDLE,
        position=(100, 100),
        id="npc",
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(Describe("Hello!"),)),),
    )
    room_state = make_room_state(
        RoomData(id="character_room", description="A room with a character.", characters=(character,))
    )
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.characters[0].rect.center)

    assert messages == ["Hello!"]


def make_walk_to_room_state(monkeypatch: pytest.MonkeyPatch) -> tuple[RoomState, list[str]]:
    """Create a room whose prop walks to itself between two effects."""
    prop = PropData(
        id="far_prop",
        description="A far away prop.",
        image=props.STUDIO.image,
        position=(100, 100),
        interactions=(
            InteractionData(
                verb=Verb.INTERACT,
                effects=(Describe("before"), WalkTo(), Describe("after")),
            ),
        ),
    )
    room_state = make_room_state(RoomData(id="walk_room", description="A room with a prop.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)
    return room_state, messages


def test_walk_to_defers_following_effects_until_arrival(monkeypatch: pytest.MonkeyPatch) -> None:
    room_state, messages = make_walk_to_room_state(monkeypatch)

    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["before"]
    assert room_state.player.target is not None
    finish_player_walk(room_state)
    assert messages == ["before", "after"]


def test_cancelling_walk_to_skips_following_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    room_state, messages = make_walk_to_room_state(monkeypatch)

    click(room_state, room_state.room.props[0].rect.center)
    room_state.update(0.05, InputState(frozenset({Action.RIGHT}), {}))

    assert room_state.player.target is None
    idle: InputState = InputState(frozenset(), {})
    for _ in range(300):
        room_state.update(0.05, idle)
    assert messages == ["before"]


def test_point_in_polygon_identifies_inside_and_outside() -> None:
    polygon = ((0, 0), (10, 0), (10, 10), (0, 10))

    assert point_in_polygon((5, 5), polygon)
    assert not point_in_polygon((15, 5), polygon)


def test_region_enter_and_exit_dispatch_interactions(monkeypatch: pytest.MonkeyPatch) -> None:
    region = RegionData(
        id="region",
        description="A region.",
        polygon=((200, 50), (480, 50), (480, 300), (200, 300)),
        interactions=(
            InteractionData(verb=Verb.ENTER, effects=(Describe("entered"),)),
            InteractionData(verb=Verb.EXIT, effects=(Describe("exited"),)),
        ),
    )
    room_state = make_room_state(RoomData(id="region_room", description="A room with a region.", regions=(region,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)
    idle: InputState = InputState(frozenset(), {})

    room_state.update(0.0, idle)
    assert messages == ["entered"]

    room_state.update(1.0, InputState(frozenset({Action.RIGHT}), {}))
    assert messages == ["entered", "exited"]

    room_state.update(0.0, idle)
    assert messages == ["entered", "exited"]


def test_region_without_interactions_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    region = RegionData(
        id="region",
        description="A region.",
        polygon=((200, 50), (280, 50), (280, 100), (200, 100)),
    )
    room_state = make_room_state(
        RoomData(id="silent_region_room", description="A room with a region.", regions=(region,))
    )
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    room_state.update(0.0, InputState(frozenset(), {}))

    assert messages == []


def test_set_flag_enables_conditional_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    setter = PropData(
        id="setter",
        description="Sets a flag.",
        image=props.STUDIO.image,
        position=(50, 50),
        size=(20, 20),
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(SetFlag(flag="unlocked", value=True),)),),
    )
    gated = PropData(
        id="gated",
        description="A gated prop.",
        image=props.STUDIO.image,
        position=(300, 50),
        size=(20, 20),
        interactions=(
            InteractionData(
                verb=Verb.INTERACT,
                effects=(Describe("unlocked"),),
                priority=10,
                conditions=(FlagIs(flag="unlocked"),),
            ),
            InteractionData(verb=Verb.INTERACT, effects=(Describe("locked"),), priority=0),
        ),
    )
    room_state = make_room_state(RoomData(id="flags_room", description="A room.", props=(setter, gated)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[1].rect.center)
    click(room_state, room_state.room.props[0].rect.center)
    click(room_state, room_state.room.props[1].rect.center)

    assert messages == ["locked", "unlocked"]
    assert room_state.get_flag("unlocked")


def test_composite_conditions_gate_an_interaction(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(
        id="conditional",
        description="A conditional prop.",
        image=props.STUDIO.image,
        position=(100, 100),
        interactions=(
            InteractionData(
                verb=Verb.INTERACT,
                effects=(Describe("allowed"),),
                priority=10,
                conditions=(
                    AllOf((FlagIs(flag="ready"), Not(FlagIs(flag="blocked")))),
                    AnyOf((FlagIs(flag="a"), FlagIs(flag="b"))),
                ),
            ),
            InteractionData(verb=Verb.INTERACT, effects=(Describe("denied"),), priority=0),
        ),
    )
    room_state = make_room_state(RoomData(id="conditions_room", description="A room.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)
    room_state.set_flag("ready", value=True)
    room_state.set_flag("a", value=True)
    click(room_state, room_state.room.props[0].rect.center)
    room_state.set_flag("blocked", value=True)
    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["denied", "allowed", "denied"]


def test_once_interaction_falls_back_after_first_use(monkeypatch: pytest.MonkeyPatch) -> None:
    prop = PropData(
        id="once_prop",
        description="A prop with a one-shot interaction.",
        image=props.STUDIO.image,
        position=(100, 100),
        interactions=(
            InteractionData(verb=Verb.INTERACT, effects=(Describe("once"),), priority=10, once=True),
            InteractionData(verb=Verb.INTERACT, effects=(Describe("again"),), priority=0),
        ),
    )
    room_state = make_room_state(RoomData(id="once_room", description="A room.", props=(prop,)))
    messages: list[str] = []
    monkeypatch.setattr(room_state, "show_message", messages.append)

    click(room_state, room_state.room.props[0].rect.center)
    click(room_state, room_state.room.props[0].rect.center)

    assert messages == ["once", "again"]


def test_flags_are_loaded_and_saved_with_transition_data() -> None:
    room_state = make_room_state(RoomData(id="flags_room", description="A room."))
    transition_data = WerewolfTransitionData(flags={"from_previous": True})

    room_state.enter(transition_data, room_state.renderer)
    assert room_state.get_flag("from_previous")

    room_state.set_flag("set_here", value=True)
    returned = room_state.exit()

    assert returned is transition_data
    assert returned.flags == {"from_previous": True, "set_here": True}


def test_flag_interaction_definitions_survive_editor_source_generation() -> None:
    prop = PropData(
        id="flags",
        description="Flags.",
        image=Images.CHAINS_1,
        interactions=(
            InteractionData(
                verb=Verb.INTERACT,
                effects=(SetFlag(flag="seen", value=True),),
                conditions=(FlagIs(flag="ready"), Not(FlagIs(flag="blocked"))),
                once=True,
            ),
        ),
    )
    room = replace(RoomData(id="test_room", description="Test room."), props=(prop,))

    updated = update_room_source("ROOM = None\n", {"ROOM": room})
    ast.parse(updated)

    assert "SetFlag(" in updated
    assert "FlagIs(" in updated
    assert "Not(" in updated
    assert "once=True" in updated
    assert (
        "from my_game.werewolf.interactions.definitions import FlagIs, InteractionData, Not, SetFlag, Verb" in updated
    )


def test_generated_source_uses_double_quoted_strings() -> None:
    room = RoomData(id="quotes", description='Says "hello".')

    updated = update_room_source("ROOM = None\n", {"ROOM": room})

    ast.parse(updated)
    assert 'id="quotes"' in updated
    assert 'description="Says \\"hello\\"."' in updated
    assert "'quotes'" not in updated


def test_interaction_definitions_survive_editor_source_generation() -> None:
    prop = PropData(
        id="chains",
        description="Chains.",
        image=Images.CHAINS_1,
        interactions=(InteractionData(verb=Verb.INTERACT, effects=(WalkTo(), ChangeRoom(room_id="church_cemetary"))),),
    )
    room = replace(RoomData(id="test_room", description="Test room."), props=(prop,))

    updated = update_room_source("ROOM = None\n", {"ROOM": room})
    ast.parse(updated)

    assert "Verb.INTERACT" in updated
    assert "WalkTo()" in updated
    assert "ChangeRoom(" in updated
    assert "from my_game.werewolf.interactions.definitions import ChangeRoom, InteractionData, Verb, WalkTo" in updated
