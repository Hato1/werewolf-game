"""Runtime dispatch for interactions defined on room objects."""

from collections.abc import Callable, Sequence
from functools import partial
from typing import Protocol

from my_game.core.logger import get_logger
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
    ObjectKind,
    ObjectRef,
    SetFlag,
    Verb,
    WalkTo,
)
from my_game.werewolf.interactions.registry import get_room
from my_game.werewolf.room.loaders import RoomData

logger = get_logger(__name__)


class InteractionTarget(Protocol):
    """Runtime object that can carry interaction definitions."""

    @property
    def id(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def interactions(self) -> tuple[InteractionData, ...]: ...


class InteractionContext(Protocol):
    """Game state that interaction effects are allowed to change."""

    def show_message(self, text: str) -> None: ...

    def change_room(self, room: RoomData) -> None: ...

    def enter_dialogue_state(self, dialogue: Dialogue) -> None: ...

    def walk_to(self, target: InteractionTarget, on_arrive: Callable[[], None]) -> None: ...

    def get_flag(self, flag: str) -> bool: ...

    def set_flag(self, flag: str, *, value: bool) -> None: ...


class InteractionSystem:
    """Select and apply the interaction attached to a room object."""

    def dispatch(self, target: InteractionTarget, kind: ObjectKind, verb: Verb, ctx: InteractionContext) -> None:
        """Apply the highest-priority eligible interaction, or describe the target."""
        logger.debug("Dispatching interaction.", target=ObjectRef(kind=kind, id=target.id), verb=verb)
        selected = self._matching_interaction(target, kind, verb, ctx)
        if selected is None:
            # Only a plain click falls back to describing the target. Proximity
            # verbs such as ENTER are silent when nothing is defined.
            if verb is not Verb.INTERACT:
                return
            effects: tuple[Effect, ...] = (Describe(),)
        else:
            index, interaction = selected
            if interaction.once:
                ctx.set_flag(self._once_flag(kind, target, verb, index), value=True)
            effects = interaction.effects
        self._apply_effects(effects, target, ctx)

    @classmethod
    def _matching_interaction(
        cls,
        target: InteractionTarget,
        kind: ObjectKind,
        verb: Verb,
        ctx: InteractionContext,
    ) -> tuple[int, InteractionData] | None:
        """Return the highest-priority eligible interaction for ``verb``, if any."""
        matching = (
            (index, interaction)
            for index, interaction in enumerate(target.interactions)
            if interaction.verb is verb
            and cls._conditions_met(interaction.conditions, ctx)
            and not (interaction.once and ctx.get_flag(cls._once_flag(kind, target, verb, index)))
        )
        return max(matching, key=lambda item: item[1].priority, default=None)

    @staticmethod
    def _once_flag(kind: ObjectKind, target: InteractionTarget, verb: Verb, index: int) -> str:
        """Return the internal flag that records a consumed one-shot interaction."""
        return f"interaction.once:{kind.value}:{target.id}:{verb.value}:{index}"

    @classmethod
    def _conditions_met(cls, conditions: Sequence[Condition], ctx: InteractionContext) -> bool:
        """Return whether every condition passes in the current game state."""
        return all(cls._condition_met(condition, ctx) for condition in conditions)

    @classmethod
    def _condition_met(cls, condition: Condition, ctx: InteractionContext) -> bool:
        """Evaluate one serializable condition."""
        match condition:
            case FlagIs(flag=flag, value=value):
                return ctx.get_flag(flag) is value
            case Not(condition=inner):
                return not cls._condition_met(inner, ctx)
            case AllOf(conditions=conditions):
                return cls._conditions_met(conditions, ctx)
            case AnyOf(conditions=conditions):
                return any(cls._condition_met(inner, ctx) for inner in conditions)
            case unknown:
                raise TypeError(f"Unsupported interaction condition: {unknown!r}")

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
            case SetFlag(flag=flag, value=value):
                ctx.set_flag(flag, value=value)
            case unknown:
                raise TypeError(f"Unsupported interaction effect: {unknown!r}")
