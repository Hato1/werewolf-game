"""State factories and defaults for the bullet-hell example game."""

from collections.abc import Callable

from my_game.core.state_manager import State, StateRegistry
from my_game.examples.bullet_hell.inputs import input_manager
from my_game.examples.bullet_hell.state_data import BulletHellState, BulletHellTransitionData
from my_game.examples.bullet_hell.states.game import Game
from my_game.examples.bullet_hell.states.main_menu import MainMenu
from my_game.examples.bullet_hell.states.scoreboard import Scoreboard

STATE_FACTORIES: dict[
    BulletHellState,
    Callable[[], State[BulletHellState, BulletHellTransitionData]],
] = {
    BulletHellState.MAIN_MENU: MainMenu,
    BulletHellState.GAME: Game,
    BulletHellState.SCOREBOARD: Scoreboard,
}
STATE_REGISTRY = StateRegistry(STATE_FACTORIES, BulletHellState.MAIN_MENU, BulletHellTransitionData)
__all__ = ["STATE_REGISTRY", "input_manager"]
