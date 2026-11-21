"""Run the program.
Asyncio is used for Pygbag (web) compatibility."""

import asyncio
import sys
import types
from pathlib import Path

import pygame as pg

# Hack for Pygbag to ensure the my_game package is correctly recognized.
if sys.platform == "emscripten" and "my_game" not in sys.modules:
    pkg = types.ModuleType("my_game")
    pkg.__path__ = [str(Path(__file__).parent)]
    sys.modules["my_game"] = pkg

import my_game.initialise_pygame  # noqa: F401
from my_game.constants import SCREEN_SIZE
from my_game.core.logger import LogLevel, get_logger, initialize_logger
from my_game.core.state_manager import StateManager
from my_game.examples.bullet_hell import registry as bullet_hell
from my_game.werewolf import registry as werewolf
from my_game.werewolf.states.options_menu import Settings, get_available_scales

OPTIONS_FILE = Path("settings.json")

initialize_logger(LogLevel.INFO)
logger = get_logger(__name__)

# TODO: Allow configuration via command line arguments or something.
GAMES = [bullet_hell, werewolf]
DEFAULT_GAME = werewolf


def pygame_init(*, lighting: bool, resolution_scale: int, fullscreen: bool):
    # Initialization
    pg.init()

    # Apply resolution scale
    scaled_screen_size = (SCREEN_SIZE[0] * resolution_scale, SCREEN_SIZE[1] * resolution_scale)

    if lighting:
        # Set OpenGL context attributes for Pygame before creating the window.
        # Without this the OpenGL context may not be created with the desired version and profile.
        # And on some platforms, failing to set these attributes may result in an incompatible OpenGL context.
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)
        options = pg.OPENGL | pg.DOUBLEBUF
    elif sys.platform == "emscripten":
        options = 0
    else:
        options = 0

    if fullscreen and sys.platform != "emscripten":
        options |= pg.FULLSCREEN

    screen = pg.display.set_mode(scaled_screen_size, options)
    assert screen is not None, "Pygame display surface not initialized."
    return screen


async def main():
    """Run the program."""
    initialize_logger(LogLevel.INFO)

    settings = Settings.from_persistent_storage()

    if settings.fullscreen and sys.platform != "emscripten":
        resolution_scale = get_available_scales()[-1]
    else:
        resolution_scale = settings.resolution_scale

    screen = pygame_init(
        lighting=settings.lighting,
        resolution_scale=resolution_scale,
        fullscreen=settings.fullscreen,
    )

    state_manager = StateManager(
        screen,
        DEFAULT_GAME.STATE_REGISTRY,
        DEFAULT_GAME.input_manager,
        open_gl=settings.lighting,
        scale_factor=resolution_scale,
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
