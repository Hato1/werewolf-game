"""Headless conversion helpers for the interaction editor UI.

Widgets store plain dictionaries of names and values. These helpers convert
between that form representation and the frozen interaction definitions used
by rooms, keeping the GUI layer free of parsing logic.
"""

from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from types import NoneType, UnionType
from typing import Any, cast, get_args, get_origin

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

CONDITION_TYPES: tuple[type[Condition], ...] = (FlagIs, Not, AllOf, AnyOf)
EFFECT_TYPES: tuple[type[Effect], ...] = (Describe, WalkTo, ChangeRoom, EnterDialogue, SetFlag)
DEFINITION_TYPES: tuple[type[Condition | Effect], ...] = (*CONDITION_TYPES, *EFFECT_TYPES)
DEFINITION_REGISTRY: dict[str, type[Condition | Effect]] = {
    definition_type.__name__: definition_type for definition_type in DEFINITION_TYPES
}
SCALAR_CONVERTERS: dict[Any, Callable[[Any], Any]] = {bool: bool, int: int, str: str}


def definition_to_dict(definition: Condition | Effect) -> dict[str, Any]:
    """Convert a definition into a widget-friendly dictionary."""
    return {
        "type": type(definition).__name__,
        **{field.name: _value_to_dict(getattr(definition, field.name)) for field in fields(cast(Any, definition))},
    }


def definitions_to_dicts(definitions: tuple[Condition, ...] | tuple[Effect, ...]) -> list[dict[str, Any]]:
    """Convert a tuple of definitions into widget-friendly dictionaries."""
    return [definition_to_dict(definition) for definition in definitions]


def _value_to_dict(value: Any) -> Any:
    """Convert nested definition values recursively."""
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return definition_to_dict(cast(Condition | Effect, value))
    if isinstance(value, tuple):
        return [_value_to_dict(item) for item in value]
    return value


def definition_from_dict[T: Condition | Effect](
    data: Mapping[str, Any],
    expected: type[T] | None = None,
) -> T:
    """Rebuild a condition or effect from a widget-friendly dictionary."""
    type_name = data.get("type")
    if not isinstance(type_name, str):
        raise TypeError(f"Expected a definition type name, got {type_name!r}")
    definition_type = DEFINITION_REGISTRY.get(type_name)
    if definition_type is None:
        raise ValueError(f"Unknown interaction definition type: {type_name!r}")
    if expected is not None and not issubclass(definition_type, expected):
        article = "an" if expected.__name__.startswith(("A", "E", "I", "O", "U")) else "a"
        raise ValueError(f"Expected {article} {expected.__name__}, got {definition_type.__name__}.")

    field_types = {field.name: field.type for field in fields(cast(Any, definition_type))}
    kwargs = {
        name: _value_from_dict(value, field_types.get(name))
        for name, value in data.items()
        if name != "type" and name in field_types
    }
    try:
        return cast(T, definition_type(**kwargs))
    except TypeError as error:
        raise ValueError(f"Invalid values for {definition_type.__name__}: {error}") from error


def definitions_from_dicts[T: Condition | Effect](data: Any, expected: type[T]) -> tuple[T, ...]:
    """Rebuild a tuple of conditions or effects from widget-friendly dictionaries."""
    if not isinstance(data, list):
        raise TypeError("Expected a list of definitions.")
    return tuple(definition_from_dict(item, expected) for item in data)


def _is_enum_type(field_type: Any) -> bool:
    """Return whether a field type is an enum class."""
    return isinstance(field_type, type) and issubclass(field_type, Enum)


def _is_definition_type(field_type: Any) -> bool:
    """Return whether a field type is a condition or effect class."""
    return isinstance(field_type, type) and issubclass(field_type, (Condition, Effect))


def _tuple_from_dict(value: Any, field_type: Any) -> tuple[Any, ...]:
    """Convert a widget value into a tuple of nested definitions."""
    if not isinstance(value, list):
        raise TypeError("Expected a list of nested definitions.")
    item_type = next(iter(get_args(field_type)), None)
    return tuple(_value_from_dict(item, item_type) for item in value)


def _union_from_dict(value: Any, field_type: Any) -> Any:
    """Convert a widget value using the non-optional member of a union."""
    args = get_args(field_type)
    if NoneType in args and value in (None, ""):
        return None
    for arg in args:
        if arg is not NoneType:
            return _value_from_dict(value, arg)
    return value


def _value_from_dict(value: Any, field_type: Any) -> Any:
    """Convert one widget value to the type expected by a definition field."""
    if field_type is not None:
        converter = SCALAR_CONVERTERS.get(field_type)
        if converter is not None:
            return converter(value)
        if _is_enum_type(field_type):
            return field_type[value]
        if _is_definition_type(field_type):
            return definition_from_dict(value, field_type)
        if get_origin(field_type) is tuple:
            return _tuple_from_dict(value, field_type)
        if isinstance(field_type, UnionType):
            return _union_from_dict(value, field_type)
    return value


def interaction_to_dict(interaction: InteractionData) -> dict[str, Any]:
    """Convert an interaction into a widget-friendly dictionary."""
    return {
        "verb": interaction.verb.name,
        "priority": interaction.priority,
        "once": interaction.once,
        "conditions": definitions_to_dicts(interaction.conditions),
        "effects": definitions_to_dicts(interaction.effects),
    }


def interaction_from_dict(data: Mapping[str, Any]) -> InteractionData:
    """Rebuild an interaction from a widget-friendly dictionary."""
    return InteractionData(
        verb=Verb[data["verb"]],
        effects=definitions_from_dicts(data.get("effects", []), Effect),
        priority=int(data.get("priority", 0)),
        conditions=definitions_from_dicts(data.get("conditions", []), Condition),
        once=bool(data.get("once", False)),
    )


def definition_label(definition: Condition | Effect) -> str:
    """Return a short human-readable label for an editor list row."""
    details = ", ".join(f"{key}={value!r}" for key, value in definition_to_dict(definition).items() if key != "type")
    return f"{type(definition).__name__}({details})" if details else type(definition).__name__


def interaction_label(interaction: InteractionData) -> str:
    """Return a short human-readable summary for an editor list row."""
    details = [f"priority={interaction.priority}"]
    if interaction.once:
        details.append("once")
    if interaction.conditions:
        details.append(f"{len(interaction.conditions)} condition(s)")
    details.extend(definition_label(effect) for effect in interaction.effects)
    return f"{interaction.verb.value}: " + "; ".join(details)
