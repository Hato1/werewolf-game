"""Shared state identifiers and transition payload for the bullet hell example."""

from dataclasses import dataclass
from enum import StrEnum, auto

from my_game.core.state_manager import TransitionData


class BulletHellState(StrEnum):
    MAIN_MENU = auto()
    GAME = auto()
    SCOREBOARD = auto()


@dataclass
class BulletHellTransitionData(TransitionData):
    score: float = 0.0
