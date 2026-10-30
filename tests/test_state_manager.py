from dataclasses import dataclass
from enum import Enum

import pytest

from my_game.core.input_manager import InputManager, InputState
from my_game.core.state_manager import State, StateManager, StateRegistry, TransitionData


def test_state_transition_uses_explicit_enter_exit_and_payload() -> None:
    """State transitions should pass payloads through an explicit lifecycle."""
    import pygame as pg

    class StateKey(Enum):
        ALPHA = 1
        BETA = 2

    @dataclass
    class TestTransitionData(TransitionData):
        score: int = 0

    class Alpha(State[StateKey, TestTransitionData]):
        def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
            pass

        def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
            pass

        def draw(self, surface: pg.Surface, dt: float) -> None:
            pass

    class Beta(State[StateKey, TestTransitionData]):
        def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
            pass

        def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
            pass

        def draw(self, surface: pg.Surface, dt: float) -> None:
            pass

        def enter(self, surface_rect: pg.Rect, transition_data: TestTransitionData) -> None:
            super().enter(surface_rect, transition_data)
            assert transition_data.previous_state is StateKey.ALPHA
            assert transition_data.score == 42

    screen = pg.display.set_mode((64, 64))
    registry = StateRegistry(
        {StateKey.ALPHA: Alpha, StateKey.BETA: Beta},
        StateKey.ALPHA,
        TestTransitionData,
    )
    manager = StateManager(screen, registry, InputManager(Enum), "Transition test")

    alpha = manager.current_state
    alpha.done = True
    alpha.transition_data.score = 42

    manager.change_state(StateKey.BETA)

    assert isinstance(manager.current_state, Beta)
    assert manager.current_state is not alpha
    assert manager.current_state_id is StateKey.BETA


def test_state_manager_passes_held_actions_to_update(monkeypatch) -> None:
    import pygame as pg

    from my_game.core.input_manager import AXIS_MAX_VALUE, InputEvent
    from my_game.core.state_manager import StateRegistry

    class StateKey(Enum):
        TEST = 1

    @dataclass
    class TestTransitionData(TransitionData):
        pass

    class Action(Enum):
        MOVE = 1
        ANALOG_MOVE = 2

    class TestState(State[StateKey, TestTransitionData]):
        def __init__(self) -> None:
            super().__init__()
            self.input_state: InputState | None = None

        def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
            pass

        def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
            self.input_state = input_state

        def draw(self, surface: pg.Surface, dt: float) -> None:
            pass

    input_manager = InputManager(Action)
    input_manager.bind(Action.MOVE, InputEvent.keyboard(pg.K_w))
    input_manager.bind(Action.ANALOG_MOVE, InputEvent.controller_axis(pg.CONTROLLER_AXIS_LEFTX))
    screen = pg.display.set_mode((64, 64))
    manager = StateManager(
        screen,
        StateRegistry({StateKey.TEST: TestState}, StateKey.TEST, TestTransitionData),
        input_manager,
        "Held input test",
    )
    monkeypatch.setattr(
        pg.event,
        "get",
        lambda: [
            pg.event.Event(pg.KEYDOWN, key=pg.K_w),
            pg.event.Event(
                pg.CONTROLLERAXISMOTION,
                axis=pg.CONTROLLER_AXIS_LEFTX,
                value=int(0.6 * AXIS_MAX_VALUE),
                instance_id=1,
            ),
        ],
    )

    manager.handle_events()
    manager.update(1 / 60)

    assert isinstance(manager.current_state, TestState)
    input_state = manager.current_state.input_state
    assert input_state is not None
    assert input_state.held_actions == {Action.MOVE}
    assert Action.MOVE in input_state
    assert Action.ANALOG_MOVE not in input_state
    assert input_state.get_action_strength(Action.MOVE) == 1.0
    assert input_state.get_action_strength(Action.ANALOG_MOVE) == pytest.approx(0.5, rel=1e-4)
