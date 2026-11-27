"""Tests for headless interaction-editor conversion helpers."""

import pytest

from my_game.werewolf.assets import Dialogue
from my_game.werewolf.interactions.definitions import (
    AllOf,
    AnyOf,
    ChangeRoom,
    Condition,
    Describe,
    Effect,
    EnterDialogue,
    FlagIs,
    InteractionData,
    Not,
    SetFlag,
    Verb,
    WalkTo,
)
from my_game.werewolf.interactions.editor_data import (
    definition_from_dict,
    definition_to_dict,
    interaction_from_dict,
    interaction_label,
    interaction_to_dict,
)
from my_game.werewolf.room import rooms
from my_game.werewolf.room.editor_data import named_values
from my_game.werewolf.room.loaders import CharacterData, NamedPointData, PropData, RegionData, RoomData


def test_definitions_round_trip_through_editor_values() -> None:
    definitions: tuple[Condition | Effect, ...] = (
        Describe(),
        Describe(text="Hello."),
        WalkTo(),
        ChangeRoom(room_id="church_cemetary"),
        EnterDialogue(dialogue=Dialogue.MAYOR),
        SetFlag(flag="seen", value=True),
        FlagIs(flag="ready"),
        FlagIs(flag="blocked", value=False),
        Not(FlagIs(flag="blocked")),
        AllOf((FlagIs(flag="a"), FlagIs(flag="b"))),
        AnyOf((FlagIs(flag="c"), Not(FlagIs(flag="d")))),
    )

    for definition in definitions:
        assert definition_from_dict(definition_to_dict(definition)) == definition


def test_interaction_round_trip_through_editor_values() -> None:
    interaction = InteractionData(
        verb=Verb.ENTER,
        effects=(WalkTo(), SetFlag(flag="entered", value=True)),
        priority=5,
        conditions=(AllOf((FlagIs(flag="ready"),)),),
        once=True,
    )

    data = interaction_to_dict(interaction)

    assert data["verb"] == "ENTER"
    assert interaction_from_dict(data) == interaction
    assert "once" in interaction_label(interaction)


def test_authored_interactions_round_trip_through_editor_values() -> None:
    objects: list[PropData | CharacterData | RegionData | NamedPointData] = []
    for room in named_values(rooms, RoomData).values():
        objects.extend(room.props)
        objects.extend(room.characters)
        objects.extend(room.regions)
        objects.extend(room.points)

    interactions = [interaction for obj in objects for interaction in obj.interactions]

    assert interactions
    for interaction in interactions:
        assert interaction_from_dict(interaction_to_dict(interaction)) == interaction


def test_blank_optional_text_is_converted_to_none() -> None:
    assert definition_from_dict({"type": "Describe", "text": ""}) == Describe()


def test_invalid_definition_types_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown interaction definition type"):
        definition_from_dict({"type": "Missing"})

    with pytest.raises(ValueError, match="Expected an Effect"):
        definition_from_dict(definition_to_dict(FlagIs(flag="ready")), Effect)
