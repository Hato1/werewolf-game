"""Shared state identifiers and transition payload for the werewolf game."""

from dataclasses import dataclass
from enum import StrEnum, auto

from my_game.core.state_manager import TransitionData


class WerewolfState(StrEnum):
    MAIN_MENU = auto()
    PROLOGUE = auto()
    TEST_ROOM = auto()
    RENDER_TEST = auto()


@dataclass
class WerewolfTransitionData(TransitionData): ...
