"""Room-editor data conversion and Python source generation.

The editor works with immutable room dataclasses. These helpers translate form
values and write selected definitions back to the existing room module.
"""

import ast
import json
import re
from collections.abc import Callable
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from types import ModuleType
from typing import Any

from my_game.werewolf.assets import DialogueFile, Images
from my_game.werewolf.interactions.definitions import (
    AllOf,
    AnyOf,
    ChangeRoom,
    Describe,
    EnterDialogue,
    FlagIs,
    InteractionData,
    Not,
    ObjectKind,
    ObjectRef,
    SetFlag,
    Verb,
    WalkTo,
)
from my_game.werewolf.room import characters, props
from my_game.werewolf.room.loaders import CharacterData, NamedPointData, PropData, RegionData, RoomData


def named_values[T](module: ModuleType, value_type: type[T]) -> dict[str, T]:
    """Find public module-level definitions of the requested data type."""
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and isinstance(value, value_type)
    }


def json_value(value: Any) -> Any:
    """Convert dataclasses, image enums and tuples to JSON-compatible values."""
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return {field.name: json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    return value


def _catalog_reference(value: Any) -> str | None:
    """Use a catalog reference when a value exactly matches a reusable definition."""
    for module_name, module in (("props", props), ("characters", characters)):
        for name, catalog_item in vars(module).items():
            if isinstance(catalog_item, type(value)) and catalog_item == value:
                return f"{module_name}.{name}"
    return None


def _python_expression(value: Any, indent: int = 0, *, use_catalog: bool = True) -> str:
    """Render a room data value as a Python expression for rooms.py."""
    if use_catalog and (reference := _catalog_reference(value)) is not None:
        return reference
    if isinstance(value, Enum):
        return f"{type(value).__name__}.{value.name}"
    if is_dataclass(value):
        members = fields(value)
        if not members:
            return f"{type(value).__name__}()"
        padding = " " * (indent + 4)
        arguments = [
            f"{padding}{field.name}={_python_expression(getattr(value, field.name), indent + 4)}," for field in members
        ]
        return f"{type(value).__name__}(\n" + "\n".join(arguments) + f"\n{' ' * indent})"
    if isinstance(value, tuple):
        elements = ", ".join(_python_expression(item, indent) for item in value)
        return f"({elements}{',' if len(value) == 1 else ''})"
    return repr(value)


def _set_import(source: str, module_name: str, names: set[str]) -> str:
    """Replace or insert a from-import needed by generated expressions."""
    tree = ast.parse(source)
    import_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == module_name and node.level == 0
        ),
        None,
    )
    lines = source.splitlines()
    import_line = f"from {module_name} import {', '.join(sorted(names))}"
    if import_node is not None:
        end_line = import_node.end_lineno or import_node.lineno
        lines[import_node.lineno - 1 : end_line] = [import_line]
        return "\n".join(lines) + "\n"

    insert_at = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insert_at = tree.body[0].end_lineno or tree.body[0].lineno
    lines.insert(insert_at, import_line)
    return "\n".join(lines) + "\n"


def _find_room_assignments(tree: ast.Module) -> dict[str, ast.stmt]:
    """Locate top-level assignments by name for replacement."""
    assignments: dict[str, ast.stmt] = {}
    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node
    return assignments


def update_room_source(source: str, updates: dict[str, RoomData]) -> str:
    """Replace selected room assignments while preserving the rest of rooms.py."""
    tree = ast.parse(source)
    assignments = _find_room_assignments(tree)
    lines = source.splitlines()
    replacements: list[tuple[int, int, list[str]]] = []
    additions: list[str] = []
    for name, room_data in updates.items():
        statement = f"{name} = {_python_expression(room_data, use_catalog=False)}"
        if name in assignments:
            node = assignments[name]
            replacements.append((node.lineno - 1, node.end_lineno or node.lineno, statement.splitlines()))
        else:
            additions.extend(["", statement])
    for start, end, statement_lines in sorted(replacements, reverse=True):
        lines[start:end] = statement_lines
    lines.extend(additions)
    updated = "\n".join(lines).rstrip() + "\n"

    asset_names = {asset_type.__name__ for asset_type in (Images, DialogueFile) if f"{asset_type.__name__}." in updated}
    if asset_names:
        updated = _set_import(updated, "my_game.werewolf.assets", asset_names)

    used_types = {
        data_type.__name__
        for data_type in (CharacterData, PropData, RegionData, NamedPointData, RoomData)
        if re.search(rf"\b{data_type.__name__}\(", updated)
    }
    if used_types:
        updated = _set_import(updated, "my_game.werewolf.room.loaders", used_types)

    interaction_names = {
        definition.__name__
        for definition in (
            AllOf,
            AnyOf,
            ChangeRoom,
            Describe,
            EnterDialogue,
            FlagIs,
            InteractionData,
            Not,
            ObjectRef,
            SetFlag,
            WalkTo,
        )
        if re.search(rf"\b{definition.__name__}\(", updated)
    }
    interaction_names.update(
        enum_type.__name__ for enum_type in (Verb, ObjectKind) if re.search(rf"\b{enum_type.__name__}\.", updated)
    )
    if interaction_names:
        updated = _set_import(updated, "my_game.werewolf.interactions.definitions", interaction_names)

    if "characters." in updated:
        updated = _set_import(
            updated, "my_game.werewolf.room", {"characters", "props"} if "props." in updated else {"characters"}
        )
    elif "props." not in updated:
        updated = re.sub(r"^from my_game\.werewolf\.room import props\s*\n", "", updated, flags=re.MULTILINE)

    ast.parse(updated)
    return updated


def _restore_boolean(raw_value: str) -> bool:
    """Parse an explicit boolean rather than accepting arbitrary truthy strings."""
    normalized = raw_value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError("Enter true or false.")
    return normalized == "true"


def _restore_tuple(raw_value: str) -> tuple[Any, ...]:
    """Restore nested JSON arrays to the tuples used by room dataclasses."""

    def tuples(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(tuples(item) for item in value)
        return value

    return tuples(json.loads(raw_value))


def _restore_optional(raw_value: str, field_name: str) -> Any:
    """Parse an optional field whose current value does not reveal its type."""
    normalized = raw_value.strip()
    if normalized.lower() in {"null", "none"}:
        return None
    if field_name in {"size", "path", "position", "polygon"}:
        return _restore_tuple(raw_value)
    if field_name in {"image", "walk_image", "normal_image", "normal_walk_image"}:
        return Images[normalized]
    raise ValueError(f"Unsupported field value for {field_name}.")


def restore_value(raw_value: str, current: Any, field_name: str) -> Any:
    """Parse a form value using the existing field value to determine its type."""
    if isinstance(current, Images):
        return Images[raw_value.strip()]
    if isinstance(current, tuple):
        return _restore_tuple(raw_value)
    if current is None:
        return _restore_optional(raw_value, field_name)
    converters: dict[type, Callable[[str], Any]] = {
        bool: _restore_boolean,
        int: int,
        float: float,
        str: str,
    }
    converter = converters.get(type(current))
    if converter is None:
        raise ValueError(f"Unsupported field value for {field_name}.")
    return converter(raw_value)


def replace_room_contents(room: RoomData, kind: str, values: tuple[Any, ...]) -> RoomData:
    """Return a room with one collection replaced, leaving the original immutable."""
    if kind == "props":
        return replace(room, props=values)
    if kind == "characters":
        return replace(room, characters=values)
    if kind == "regions":
        return replace(room, regions=values)
    if kind == "points":
        return replace(room, points=values)
    if kind == "walkable_areas":
        return replace(room, walkable_areas=values)
    raise ValueError(f"Unknown room content field: {kind}")
