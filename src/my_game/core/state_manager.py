"""This module contains the StateManager class and a abstract State class."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass
from enum import Enum

import pygame as pg

from my_game.core.input_manager import InputManager, InputState


@dataclass
class TransitionData:
    """Data to be passed between states during a transition."""

    previous_state: Hashable | None = None


class State[StateKey: Hashable, Payload: TransitionData](ABC):
    """Abstract base class for program states.

    Attributes:
        done (bool): Leave this state and go to the next one.
        quit (bool): Exit the entire program.
        next_state (StateKey | None): Registered state to transition to when this one is done.
        transition_data (Payload): Data to be passed to the next state.
        start_time (float): Time in seconds since the State started.

        enter(surface_rect: pg.Rect, transition_data: Payload):
            Called when this state becomes the active state.

        exit():
            Called before leaving this state.
            Last chance to prepare persistent variables for the next state!

        handle_event(event: pg.Event):
            Abstract method to process a single Pygame event.
            Must be implemented by subclasses.

        update(surface_rect: pg.Rect, dt: float, input_state: InputState[Enum]):
            Abstract method to update program logic from one frame to the next.
            Don't draw anything to any surfaces here.
            Must be implemented by subclasses.

        draw(surface: pg.Surface, dt: float):
            Abstract method to draw the program to the given surface.
            Don't update program logic here.
            Must be implemented by subclasses.
    """

    def __init__(self):
        self.done: bool = False
        self.quit: bool = False
        self.next_state: StateKey | None = None
        self.transition_data: Payload
        self.start_time: float = 0.0

    def enter(
        self,
        surface_rect: pg.Rect,
        transition_data: Payload,
    ) -> None:
        """Called when this state becomes the active state.

        surface_rect: Rect representing the surface dimensions.
        transition_data: Data delivered from the previous state.
        """
        self.transition_data = transition_data
        self.start_time = pg.time.get_ticks() / 1000.0

    def exit(self) -> Payload:
        """Called before leaving this state."""
        self.done = False
        return self.transition_data

    @abstractmethod
    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        """Handle one pygame event."""
        pass

    @abstractmethod
    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState[Enum]) -> None:
        """Update game logic. Runs every frame.

        surface_rect: Rect representing the surface dimensions.
        dt: Time in seconds since last frame.
        input_state: Frame-scoped held actions and action strengths.
        """
        pass

    @abstractmethod
    def draw(self, surface: pg.Surface, dt: float):
        """Render to the given surface. Runs every frame.

        surface: The surface to draw to.
        dt: Time in seconds since last frame.
        """
        pass


@dataclass(frozen=True)
class StateRegistry[StateKey: Hashable, Payload: TransitionData]:
    """State factories and transition-data construction for one game."""

    factories: Mapping[StateKey, Callable[[], State[StateKey, Payload]]]
    initial_state: StateKey
    transition_data_factory: Callable[[], Payload]


class StateManager[StateKey: Hashable, Payload: TransitionData]:
    """Responsible for managing the different states/scenes of a Pygame application.

    Methods:
        change_state(new_state: StateKey):
            Cleans up the current state and transitions to the next state, passing persistent variables.

        toggle_show_fps():
            Toggles the display of FPS in the window caption when F5 is pressed.

        handle_events():
            Processes all Pygame events and passes them to the current state. Handles global toggling of FPS display.

        update(dt: float):
            Updates the current state, checks for state changes, and manages quitting.

        main():
            Runs the main loop, handling events, updating states, rendering, and updating the window caption.
    """

    def __init__(
        self,
        screen: pg.Surface,
        registry: StateRegistry[StateKey, Payload],
        input_manager: InputManager,
        caption: str,
    ):
        """Initialize the manager from a state's registry."""

        self.screen: pg.Surface = screen
        self.states = dict(registry.factories)
        self.current_state_id = registry.initial_state
        self.current_state = self.states[registry.initial_state]()
        self.input_manager: InputManager = input_manager
        self.caption: str = caption  # Caption for the window.
        self.transition_data_factory = registry.transition_data_factory

        self.quit: bool = False  # Set to True to exit program.
        self.clock: pg.Clock = pg.time.Clock()
        self.fps: float = 60.0  # Used to limit the framerate.
        self.show_fps: bool = True  # Display the framerate in the caption.

        self.current_state.enter(self.screen.get_rect(), self.transition_data_factory())

    def change_state(self, next_state: StateKey | None) -> None:
        """Exit the current state, enter the next one."""
        if next_state is None:
            raise ValueError("Attempted to change state but next_state not set.")

        try:
            state_factory = self.states[next_state]
        except KeyError as error:
            raise KeyError(f"State is not registered: {next_state!r}") from error

        transition_data = self.current_state.exit()
        transition_data.previous_state = self.current_state_id
        self.current_state_id = next_state
        self.current_state = state_factory()
        self.current_state.enter(
            self.screen.get_rect(),
            transition_data=transition_data,
        )

    def toggle_show_fps(self) -> None:
        """Toggle displaying the framerate in the window caption."""
        self.show_fps = not self.show_fps
        if not self.show_fps:
            pg.display.set_caption(self.caption)

    def handle_events(self) -> None:
        """Process all events and pass them down to current State."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit = True
            else:
                actions = self.input_manager.process_pygame_event(event)
                self.current_state.handle_event(actions, event)

    def update(self, dt: float):
        """Checks for state change and updates the current state.

        dt: Time in seconds since last frame.
        """
        if self.current_state.quit:
            self.quit = True
            return

        if self.current_state.done:
            self.change_state(self.current_state.next_state)

        input_state = self.input_manager.get_input_state()
        self.current_state.update(self.screen.get_rect(), dt, input_state)
        self.current_state.draw(self.screen, dt)

    async def main(self):
        """Main loop for entire program.

        async is used for pygbag (web) compatibility."""

        while not self.quit:
            dt = self.clock.tick(self.fps) / 1000.0
            self.handle_events()
            self.update(dt)
            pg.display.update()
            await asyncio.sleep(0)

            if self.show_fps:
                fps = self.clock.get_fps()
                pg.display.set_caption(f"{self.caption} - {fps:.2f} FPS")
