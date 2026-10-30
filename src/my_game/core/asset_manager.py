"""Generic loaders for package resources used by Pygame."""

from importlib.resources import as_file
from importlib.resources.abc import Traversable

import pygame as pg


def _require_asset(resource: Traversable) -> None:
    if not resource.is_file():
        raise FileNotFoundError(f"Asset resource does not exist: {resource}")


def load_image(resource: Traversable) -> pg.Surface:
    """Load an image resource as a converted Pygame surface."""
    _require_asset(resource)
    with as_file(resource) as path:
        return pg.image.load(path).convert_alpha()


def load_sound(resource: Traversable) -> pg.Sound:
    """Load a sound-effect resource as a Pygame sound."""
    _require_asset(resource)
    with as_file(resource) as path:
        return pg.Sound(path)


def load_font(resource: Traversable, size: int = 20) -> pg.Font:
    """Load a font resource at the requested point size."""
    _require_asset(resource)
    with as_file(resource) as path:
        return pg.font.Font(path, size)


def read_text(resource: Traversable, encoding: str = "utf-8") -> str:
    """Read a text resource while its package-resource handle is valid."""
    _require_asset(resource)
    return resource.read_text(encoding=encoding)
