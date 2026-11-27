"""Runtime dispatch for interactions defined on room objects."""

from collections.abc import Callable
from functools import partial
from typing import Protocol

from my_game.core.logger import get_logger
from my_game.werewolf.assets import Dialogue
from my_game.werewolf.interactions.definitions import (
    ChangeRoom,
    Describe,
    Effect,
    EnterDialogue,
    InteractionData,
    ObjectKind,
    ObjectRef,
    Verb,
    WalkTo,
)
from my_game.werewolf.interactions.registry import get_room
from my_game.werewolf.room.loaders import RoomData

logger = get_logger(__name__)


class InteractionTarget(Protocol):
    """Runtime object that can carry interaction definitions."""

    id: str
    description: str
    interactions: tuple[InteractionData, ...]


class InteractionContext(Protocol):
    """Game state that interaction effects are allowed to change."""

    def show_message(self, text: str) -> None: ...

    def change_room(self, room: RoomData) -> None: ...

    def enter_dialogue_state(self, dialogue: Dialogue) -> None: ...

    def walk_to(self, target: InteractionTarget, on_arrive: Callable[[], None]) -> None: ...


class InteractionSystem:
    """Select and apply the interaction attached to a room object."""

    def dispatch(self, target: InteractionTarget, kind: ObjectKind, verb: Verb, ctx: InteractionContext) -> None:
        """Apply the highest-priority matching interaction, or describe the target."""
        logger.debug("Dispatching interaction.", target=ObjectRef(kind=kind, id=target.id), verb=verb)
        interaction = self._matching_interaction(target, verb)
        effects = interaction.effects if interaction is not None else (Describe(),)
        self._apply_effects(effects, target, ctx)

    @staticmethod
    def _matching_interaction(target: InteractionTarget, verb: Verb) -> InteractionData | None:
        """Return the highest-priority interaction for ``verb``, if there is one."""
        matching = (interaction for interaction in target.interactions if interaction.verb is verb)
        return max(matching, key=lambda interaction: interaction.priority, default=None)

    @classmethod
    def _apply_effects(cls, effects: tuple[Effect, ...], target: InteractionTarget, ctx: InteractionContext) -> None:
        """Apply effects in order, pausing after WalkTo until the player arrives."""
        for index, effect in enumerate(effects):
            if isinstance(effect, WalkTo):
                remaining = effects[index + 1 :]
                ctx.walk_to(target, partial(cls._apply_effects, remaining, target, ctx))
                return
            cls._apply_effect(effect, target, ctx)

    @staticmethod
    def _apply_effect(effect: Effect, target: InteractionTarget, ctx: InteractionContext) -> None:
        """Apply a single effect to the game state."""
        match effect:
            case Describe(text=text):
                ctx.show_message(text if text is not None else target.description)
            case ChangeRoom(room_id=room_id):
                ctx.change_room(get_room(room_id))
            case EnterDialogue(dialogue=dialogue):
                ctx.enter_dialogue_state(dialogue)
            case unknown:
                raise TypeError(f"Unsupported interaction effect: {unknown!r}")
