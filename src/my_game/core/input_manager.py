"""Manages input mappings for the game.

Pygame key constants can be found here:
https://pyga.me/docs/ref/key.html
Pygame event types can be found here:
https://pyga.me/docs/ref/event.html
"""

import sys
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple

import pygame as pg

# Pygbag (web) does not include the pygame._sdl2.controller module, but tries to import it anyway.
# https://pygame-web.github.io/wiki/pygbag/#adding-modules
if TYPE_CHECKING:
    from pygame._sdl2.controller import Controller
elif sys.platform != "emscripten":
    import importlib

    Controller = importlib.import_module("pygame._sdl2.controller").Controller
else:

    class Controller:
        """Stand-in for the controller class missing from the pygbag (web) build."""

        def __init__(self, device_index: int) -> None:
            self.id = device_index


# Absolute maximum value for a controller axis in Pygame. Joysticks range from -32767 to 32767.
AXIS_MAX_VALUE = 32767


@dataclass(frozen=True)
class InputState[Action: Enum]:
    """Frame-scoped input data exposed to game states."""

    held_actions: frozenset[Action]
    action_strengths: Mapping[Action, float]

    def __post_init__(self) -> None:
        # A frozen dataclass does not freeze mutable field values.
        object.__setattr__(self, "action_strengths", MappingProxyType(dict(self.action_strengths)))

    def __contains__(self, action: Action) -> bool:
        return action in self.held_actions

    def get_action_strength(self, action: Action) -> float:
        """Return the current strength of an action, or zero when inactive."""
        return self.action_strengths.get(action, 0.0)


class InputType(StrEnum):
    KEYBOARD = "keyboard"
    MOUSE_BUTTON = "mouse_button"
    MOUSE_MOTION = "mouse_motion"
    CONTROLLER_BUTTON = "controller_button"
    CONTROLLER_AXIS = "controller_axis"


class InputEvent(NamedTuple):
    """Represents an input event that can be bound to an action.

    value (Any): A key, button, or axis id (see pygame-ce key constants).
    input_type (str): The kind of input, such as keyboard or controller_button.
    keyup (bool): Bind to keyup instead of keydown.

    Inputs that don't toggle such as mouse motion or joystick
    axis should always be mapped to keydown.
    """

    value: int
    input_type: InputType
    keyup: bool = False
    direction: int = 0

    @classmethod
    def keyboard(cls, value: int, *, keyup: bool = False):
        return cls(value, InputType.KEYBOARD, keyup)

    @classmethod
    def mouse_button(cls, value: int, *, keyup: bool = False):
        return cls(value, InputType.MOUSE_BUTTON, keyup)

    @classmethod
    def mouse_motion(cls, value: int):
        return cls(value, InputType.MOUSE_MOTION, keyup=False)

    @classmethod
    def controller_button(cls, value: int, *, keyup: bool = False):
        return cls(value, InputType.CONTROLLER_BUTTON, keyup)

    @classmethod
    def controller_axis(cls, value: int, *, direction: int = 1):
        """For analogue controller joysticks and triggers."""
        if direction not in (-1, 1):
            raise ValueError("Direction must be either -1 or 1.")
        return cls(value, InputType.CONTROLLER_AXIS, keyup=False, direction=direction)


def is_keyup(event: pg.Event):
    return event.type in [pg.KEYUP, pg.CONTROLLERBUTTONUP, pg.MOUSEBUTTONUP]


class InputManager[Action: Enum]:
    """Maps actions to Pygame inputs.

    Attributes:
        bindings (defaultdict[InputEvent, set[Action]]): Maps input events to sets of actions.
        held_inputs (set[InputEvent]): Tracks currently held input events.
        axis_values (dict[int, float]): Latest value (-1 to 1) of each controller axis.
        controllers (dict[int, Controller]): Tracks connected controllers.

    Axes are analog: they never appear in held_inputs, use get_action_strength() to read them.
    """

    AXIS_DEADZONE = 0.2

    def __init__(self, actions: type[Action]) -> None:
        """Initialize the InputManager with a set of actions.

        The actions arg is not used, but it is included for type checking and documentation purposes.

        Args:
            actions (type[Action]): The Enum of possible actions that can be bound to inputs.
        """
        self.bindings: defaultdict[InputEvent, set[Action]] = defaultdict(set)
        self.held_inputs: set[InputEvent] = set()
        self.axis_values: dict[int, float] = {}
        # Can leave this empty for now as pygame sends CONTROLLERDEVICEADDED events
        # for all connected controllers at start of program.
        self.controllers: dict[int, Controller] = {}

    def bind(
        self,
        action: Action,
        input_event: InputEvent,
    ) -> None:
        """Register binding

        Args:
            action (Action): The action to bind.
            input_event (InputEvent): The users input.
        """
        self.bindings[input_event].add(action)

    def unbind(
        self,
        input_event: InputEvent,
        action: Action,
    ) -> None:
        """Unregister binding

        If the action was not previously bound to the input event, this method does nothing.

        Args:
            input_event (InputEvent): The input event to unbind from the action.
            action (Action): The action to unbind.
        """
        self.bindings[input_event].discard(action)

    def get_bound_actions(
        self,
        input_event: InputEvent,
    ) -> set[Action]:
        """Returns actions associated with binding.

        Returns:
            set[Action]: Associated actions.
        """
        return self.bindings.get(input_event, set())

    def get_bound_inputs(self, action: Action) -> set[InputEvent]:
        """Returns input kind, value, and pressed/released direction for an action.

        This is useful for displaying mapped keys when rebinding controls.

        Args:
            action (Action): The action to look up.

        Returns:
            set[InputEvent]: Corresponding inputs.
        """
        keys = set()
        for key, actions in self.bindings.items():
            if action in actions:
                keys.add(key)
        return keys

    def get_held_actions(self) -> set[Action]:
        """Return actions bound to currently held inputs."""
        held_actions: set[Action] = set()
        for input_event in self.held_inputs:
            held_actions.update(self.get_bound_actions(input_event))
        return held_actions

    def get_input_state(self) -> InputState[Action]:
        """Return a snapshot of held actions and their current strengths."""
        actions = {action for bound_actions in self.bindings.values() for action in bound_actions}
        strengths: dict[Action, float] = {action: self.get_action_strength(action) for action in actions}
        return InputState(frozenset(self.get_held_actions()), strengths)

    def get_action_strength(self, action: Action) -> float:
        """Return how strongly an action is active, from 0 to 1.

        Held buttons and keys count as 1. Axis bindings scale with the stick or trigger
        position after the deadzone. The strongest binding wins.
        """
        strength = 0.0
        for input_event, actions in self.bindings.items():
            if action not in actions:
                continue
            if input_event.input_type == InputType.CONTROLLER_AXIS:
                value = self.axis_values.get(input_event.value, 0.0) * input_event.direction
                if value > self.AXIS_DEADZONE:
                    strength = max(strength, min((value - self.AXIS_DEADZONE) / (1 - self.AXIS_DEADZONE), 1.0))
            elif input_event in self.held_inputs:
                strength = 1.0
        return strength

    def clear_held_controller_inputs(self) -> None:
        """Clear all held controller button and axis inputs."""
        self.axis_values.clear()
        controller_events = (InputType.CONTROLLER_BUTTON, InputType.CONTROLLER_AXIS)
        self.held_inputs = {
            input_event for input_event in self.held_inputs if input_event.input_type not in controller_events
        }

    def add_controller(self, device_index: int) -> None:
        """Open a controller so pygame delivers its CONTROLLER* events."""
        controller = Controller(device_index)
        self.controllers[controller.id] = controller

    def remove_controller(self, instance_id: int) -> None:
        self.controllers.pop(instance_id, None)
        self.clear_held_controller_inputs()

    def _update_held_input(self, input_event: InputEvent) -> None:
        if input_event.keyup:
            self.held_inputs.discard(input_event._replace(keyup=False))
        else:
            self.held_inputs.add(input_event)

    def process_pygame_event(self, event: pg.Event) -> set[Action]:
        """Update held-button state and return actions bound to this event."""
        input_event: InputEvent | None = None

        match event.type:
            case pg.QUIT:
                raise ValueError("Quit event should not be passed to InputManager")
            case pg.WINDOWFOCUSLOST:
                self.held_inputs.clear()
                self.axis_values.clear()
            case pg.CONTROLLERDEVICEADDED:
                self.add_controller(event.device_index)
            case pg.CONTROLLERDEVICEREMOVED:
                self.remove_controller(event.instance_id)
            case pg.KEYDOWN | pg.KEYUP:
                input_event = InputEvent.keyboard(event.key, keyup=is_keyup(event))
                self._update_held_input(input_event)
            case pg.MOUSEBUTTONDOWN | pg.MOUSEBUTTONUP:
                input_event = InputEvent.mouse_button(event.button, keyup=is_keyup(event))
                self._update_held_input(input_event)
            case pg.CONTROLLERBUTTONDOWN | pg.CONTROLLERBUTTONUP:
                input_event = InputEvent.controller_button(event.button, keyup=is_keyup(event))
                self._update_held_input(input_event)
            case pg.CONTROLLERAXISMOTION:
                self.axis_values[event.axis] = event.value / AXIS_MAX_VALUE
            # Mouse motion events are not considered "held" inputs, so we don't update held_inputs.
            case pg.MOUSEMOTION:
                input_event = InputEvent.mouse_motion(event.pos)

        return self.get_bound_actions(input_event) if input_event else set()
