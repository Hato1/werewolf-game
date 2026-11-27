"""Serializable definitions of interactions between the player and room objects.

Definitions only contain plain data so they can be stored in room data files and
written back to Python source by the room editor. Runtime behaviour lives in
`my_game.werewolf.interactions.executor`.
"""

from dataclasses import dataclass
from enum import StrEnum, auto

from my_game.werewolf.assets import Dialogue


class Verb(StrEnum):
    """Action that triggers an interaction."""

    # Mouse click on an object
    INTERACT = auto()

    # Player enters a region
    ENTER = auto()
    EXIT = auto()


class ObjectKind(StrEnum):
    """Kind of room object an interaction is attached to."""

    PROP = auto()
    CHARACTER = auto()
    REGION = auto()
    POINT = auto()


@dataclass(frozen=True)
class ObjectRef:
    """Stable reference to a room object, independent of its display name."""

    kind: ObjectKind
    id: str


class Effect:
    """Marker base class for effects stored in interaction definitions."""


@dataclass(frozen=True)
class Describe(Effect):
    """Show the target's description, or explicit text when provided."""

    text: str | None = None


@dataclass(frozen=True)
class WalkTo(Effect):
    """Walk the player up to the selected object before applying later effects."""

    # No fields: the target is the object the interaction was dispatched on.


@dataclass(frozen=True)
class ChangeRoom(Effect):
    """Move the player to the room with the given ID."""

    room_id: str


@dataclass(frozen=True)
class EnterDialogue(Effect):
    """Enter a dialogue with the given ID."""

    dialogue: Dialogue


@dataclass(frozen=True)
class InteractionData:
    """A verb and its effects, attached to a room object definition."""

    verb: Verb
    effects: tuple[Effect, ...]
    # Higher priority interactions are checked first.
    priority: int = 0
