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
from my_game.core.state_manager import StateManager
from my_game.examples.bullet_hell import registry as bullet_hell


async def main():
    """Run the program."""

    # Initialization
    pg.init()
    screen = pg.display.set_mode(SCREEN_SIZE, pg.SCALED)
    assert screen is not None, "Pygame display surface not initialized."
    pg.display.set_caption(DEFAULT_CAPTION)

    state_manager = StateManager(
        screen,
        bullet_hell.STATE_REGISTRY,
        bullet_hell.input_manager,
        DEFAULT_CAPTION,
    )

    # Run main loop.
    await state_manager.main()

    pg.quit()


def run() -> None:
    """Synchronous entry point for the console script."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
