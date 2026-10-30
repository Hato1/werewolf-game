"""State factories and defaults for the werewolf game."""

from collections.abc import Callable

from my_game.core.state_manager import State, StateRegistry
from my_game.werewolf.inputs import input_manager
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData
from my_game.werewolf.states.main_menu import MainMenu

STATE_FACTORIES: dict[
    WerewolfState,
    Callable[[], State[WerewolfState, WerewolfTransitionData]],
] = {
    WerewolfState.MAIN_MENU: MainMenu,
}
STATE_REGISTRY = StateRegistry(STATE_FACTORIES, WerewolfState.MAIN_MENU, WerewolfTransitionData)
__all__ = ["STATE_REGISTRY", "input_manager"]
