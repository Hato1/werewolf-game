"""Run the program.

Asyncio is used for Pygbag (web) compatibility."""

import asyncio
import sys
import types
from pathlib import Path

import pygame as pg

# Hack for Pygbag to ensure the my_game package is correctly recognized.
if "my_game" not in sys.modules:
    pkg = types.ModuleType("my_game")
    pkg.__path__ = [str(Path(__file__).parent)]
    sys.modules["my_game"] = pkg

import my_game.initialise_pygame  # noqa: F401
from my_game.constants import DEFAULT_CAPTION, SCREEN_SIZE
from my_game.core.gl_renderer import GLRenderer
from my_game.core.logger import LogLevel, get_logger, initialize_logger
from my_game.core.state_manager import StateManager
from my_game.examples.bullet_hell import registry as bullet_hell
from my_game.werewolf import registry as werewolf

logger = get_logger(__name__)

# TODO: Allow selecting which game to run via command line arguments or configuration.
GAMES = [bullet_hell, werewolf]
DEFAULT_GAME = werewolf


async def main():
    """Run the program."""
    initialize_logger(LogLevel.INFO)
    # Initialization
    pg.init()

    screen = pg.display.set_mode(
        [SCREEN_SIZE[0], SCREEN_SIZE[1]],
        pg.OPENGL | pg.DOUBLEBUF,
    )
    # screen = pg.display.set_mode(SCREEN_SIZE, pg.SCALED)
    gl_renderer = GLRenderer()
    assert screen is not None, "Pygame display surface not initialized."
    pg.display.set_caption(DEFAULT_CAPTION)

    state_manager = StateManager(
        screen,
        gl_renderer,
        DEFAULT_GAME.STATE_REGISTRY,
        DEFAULT_GAME.input_manager,
        DEFAULT_CAPTION,
    )

    # Run main loop.
    await state_manager.main()

    pg.quit()


def run() -> None:
    """Synchronous entry point for the console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Program interrupted by user.")


if __name__ == "__main__":
    run()
