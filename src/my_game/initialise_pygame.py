import sys

import pygame as pg

from my_game.constants import SCREEN_SIZE

pg.init()

# pg.init() doesn't start the controller subsystem; without it no CONTROLLERDEVICEADDED events are sent.
# The pygbag (web) build has no pygame._sdl2.controller, so skip controllers there.
# Importlib is required to dynamically import the controller module only on non-web platforms.
# https://pygame-web.github.io/wiki/pygbag/#adding-modules
if sys.platform != "emscripten":
    import importlib

    pg_controller = importlib.import_module("pygame._sdl2.controller")
    pg_controller.init()

# Start hidden so assets can be loaded before the window is shown.
# And it prevents window flickering on some platforms.
pg.display.set_mode(SCREEN_SIZE, pg.SCALED | pg.HIDDEN | pg.RESIZABLE)
