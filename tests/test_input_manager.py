from enum import Enum, auto

import pygame as pg
import pytest

from my_game.core.input_manager import (
    AXIS_MAX_VALUE,
    InputEvent,
    InputManager,
)


class Action(Enum):
    SELECT = auto()
    MOUSE_CLICK = auto()
    JOYSTICK_CLICK = auto()


def test_mouse_and_joystick_buttons_have_distinct_bindings() -> None:
    manager = InputManager(Action)
    manager.bind(Action.MOUSE_CLICK, InputEvent.mouse_button(1))
    manager.bind(Action.JOYSTICK_CLICK, InputEvent.controller_button(1))

    mouse_actions = manager.process_pygame_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(10, 20)))
    controller_actions = manager.process_pygame_event(pg.event.Event(pg.CONTROLLERBUTTONDOWN, button=1, instance_id=7))

    assert mouse_actions == {Action.MOUSE_CLICK}
    assert controller_actions == {Action.JOYSTICK_CLICK}


def test_controller_button_event_resolves_controller_binding() -> None:
    manager = InputManager(Action)
    manager.bind(
        Action.SELECT,
        InputEvent.controller_button(pg.CONTROLLER_BUTTON_A),
    )

    actions = manager.process_pygame_event(
        pg.event.Event(pg.CONTROLLERBUTTONDOWN, button=pg.CONTROLLER_BUTTON_A, instance_id=4)
    )

    assert actions == {Action.SELECT}


def test_get_binding_returns_structured_input_identity() -> None:
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.keyboard(pg.K_RETURN))
    manager.bind(
        Action.SELECT,
        InputEvent.controller_button(pg.CONTROLLER_BUTTON_A),
    )

    assert manager.get_bound_inputs(Action.SELECT) == {
        InputEvent.keyboard(pg.K_RETURN),
        InputEvent.controller_button(pg.CONTROLLER_BUTTON_A),
    }


def test_held_actions_follow_button_down_and_up_events() -> None:
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.keyboard(pg.K_RETURN))
    manager.bind(Action.MOUSE_CLICK, InputEvent.mouse_button(1))
    manager.bind(Action.JOYSTICK_CLICK, InputEvent.controller_button(1))

    manager.process_pygame_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    manager.process_pygame_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERBUTTONDOWN, button=1, instance_id=3))
    assert manager.get_held_actions() == {Action.SELECT, Action.MOUSE_CLICK, Action.JOYSTICK_CLICK}

    manager.process_pygame_event(pg.event.Event(pg.KEYUP, key=pg.K_RETURN))
    assert manager.get_held_actions() == {Action.MOUSE_CLICK, Action.JOYSTICK_CLICK}

    manager.process_pygame_event(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERBUTTONUP, button=1, instance_id=3))
    assert manager.get_held_actions() == set()


def test_non_button_inputs_are_not_held_and_focus_loss_clears_held_inputs() -> None:
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.keyboard(pg.K_RETURN))

    manager.process_pygame_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    manager.process_pygame_event(pg.event.Event(pg.MOUSEMOTION, pos=(10, 20), rel=(1, 1), buttons=(0, 0, 0)))
    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERAXISMOTION, axis=0, value=10000, instance_id=3))
    assert manager.get_held_actions() == {Action.SELECT}

    manager.process_pygame_event(pg.event.Event(pg.WINDOWFOCUSLOST))
    assert manager.get_held_actions() == set()


def test_controller_removal_clears_held_controller_buttons_only() -> None:
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.keyboard(pg.K_RETURN))
    manager.bind(Action.JOYSTICK_CLICK, InputEvent.controller_button(1))
    manager.process_pygame_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERBUTTONDOWN, button=1, instance_id=3))

    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERDEVICEREMOVED, instance_id=3))

    assert manager.get_held_actions() == {Action.SELECT}


def test_action_strength_scales_axis_after_deadzone() -> None:
    # TODO: These tests assume the deadzone defined in InputManager.AXIS_DEADZONE is 0.2.
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.controller_axis(pg.CONTROLLER_AXIS_LEFTX, direction=1))
    manager.bind(Action.MOUSE_CLICK, InputEvent.controller_axis(pg.CONTROLLER_AXIS_LEFTX, direction=-1))

    def move_stick(value: float) -> None:
        value = int(value * AXIS_MAX_VALUE)
        manager.process_pygame_event(
            pg.event.Event(pg.CONTROLLERAXISMOTION, axis=pg.CONTROLLER_AXIS_LEFTX, value=value, instance_id=3)
        )

    move_stick(0.1)
    assert manager.get_action_strength(Action.SELECT) == 0.0

    move_stick(0.6)
    assert manager.get_action_strength(Action.SELECT) == pytest.approx(0.5, rel=1e-4)
    assert manager.get_action_strength(Action.MOUSE_CLICK) == 0.0

    move_stick(-1.0)
    assert manager.get_action_strength(Action.SELECT) == 0.0
    assert manager.get_action_strength(Action.MOUSE_CLICK) == 1.0
    assert manager.get_held_actions() == set()

    manager.process_pygame_event(pg.event.Event(pg.CONTROLLERDEVICEREMOVED, instance_id=3))
    assert manager.get_action_strength(Action.MOUSE_CLICK) == 0.0


def test_action_strength_is_full_for_held_buttons() -> None:
    manager = InputManager(Action)
    manager.bind(Action.SELECT, InputEvent.keyboard(pg.K_RETURN))

    assert manager.get_action_strength(Action.SELECT) == 0.0
    manager.process_pygame_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    assert manager.get_action_strength(Action.SELECT) == 1.0
