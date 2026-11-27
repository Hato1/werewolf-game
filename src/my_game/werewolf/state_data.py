"""Shared state identifiers and transition payload for the werewolf game."""

from dataclasses import dataclass
from enum import StrEnum, auto

from my_game.core.state_manager import TransitionData
from my_game.werewolf.room.loaders import CharacterData
from my_game.werewolf.room.models import Room


class WerewolfState(StrEnum):
    MAIN_MENU = auto()
    PROLOGUE = auto()
    TEST_ROOM = auto()
    ROOM = auto()
    RENDER_TEST = auto()
    OPTIONS_MENU = auto()
    DIALOGUE = auto()


@dataclass
class WerewolfTransitionData(TransitionData):
    flags: dict[str, bool] | None = None
    current_room: Room | None = None

    # Dialogue
    dialogue_partner: CharacterData | None = None
