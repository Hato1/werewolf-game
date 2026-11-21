"""Callable drawing interface that routes surfaces to the active render backend."""

import sys

import pygame as pg

from my_game.constants import SCREEN_SIZE
from my_game.core.gl_renderer import GLRenderer
from my_game.core.input_manager import InputManager
from my_game.core.logger import get_logger

logger = get_logger(__name__)


def set_opengl_flags():
    # Set OpenGL context attributes for Pygame before creating the window.
    # Without this the OpenGL context may not be created with the desired version and profile.
    # And on some platforms, failing to set these attributes may result in an incompatible OpenGL context.
    pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)
    pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
    pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
    pg.display.gl_set_attribute(pg.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)


def get_available_scales() -> list[int]:
    """Get list of available resolution scales that fit in the user's display."""
    if sys.platform == "emscripten":
        return [1]

    try:
        # TODO: Don't default to the first display size blindly, consider all available displays.
        display_info = pg.display.get_desktop_sizes()[0]
    except pg.error:
        display_info = (3840, 2160)
        logger.exception(f"Failed to get display info. Defaulting to {display_info}.")

    max_width = display_info[0]
    max_height = display_info[1]

    base_width = SCREEN_SIZE[0]
    base_height = SCREEN_SIZE[1]

    available_scales = []
    scale = 0
    while True:
        scale += 1
        scaled_width = base_width * scale
        scaled_height = base_height * scale
        if scaled_width <= max_width and scaled_height <= max_height:
            available_scales.append(scale)
        else:
            break

    return available_scales if available_scales else [1]


def suggest_resolution_scale():
    """Suggest a sane resolution scale based on available display scales."""
    scales = get_available_scales()
    if len(scales) > 2:  # noqa: PLR2004
        return scales[-2]
    return scales[-1]


class Renderer:
    def __init__(self, input_manager: InputManager, *, open_gl: bool, scale_factor: int, fullscreen: bool) -> None:
        self.options = 0
        self.windowed_scale_factor = scale_factor
        self.scale_factor = scale_factor
        self.input_manager = input_manager
        self.fullscreen = fullscreen

        pg.init()

        if open_gl and sys.platform != "emscripten":
            set_opengl_flags()
            self.options |= pg.OPENGL | pg.DOUBLEBUF
        if self.fullscreen and sys.platform != "emscripten":
            self.options |= pg.FULLSCREEN
            self.scale_factor = get_available_scales()[-1]
        self.screen = self.make_screen()
        self.input_manager.set_screen_scale_factor(scale_factor)

        self.surface = pg.Surface(SCREEN_SIZE)
        self.gl_renderer = GLRenderer() if open_gl else None

    @property
    def rect(self) -> pg.Rect:
        return self.surface.get_rect()

    def make_screen(self) -> pg.Surface:
        scaled_screen_size = (SCREEN_SIZE[0] * self.scale_factor, SCREEN_SIZE[1] * self.scale_factor)
        screen = pg.display.set_mode(scaled_screen_size, self.options)
        return screen

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.options |= pg.FULLSCREEN
            new_scale_factor = get_available_scales()[-1]
        else:
            self.options &= ~pg.FULLSCREEN
            new_scale_factor = self.windowed_scale_factor
        self.set_scale_factor(new_scale_factor, entering_fullscreen=self.fullscreen)

    def set_scale_factor(self, scale_factor: int, *, entering_fullscreen: bool = False) -> None:
        """Change the resolution scale and recreate the screen.

        Args:
            scale_factor: New scale factor for resolution.
        """
        if not entering_fullscreen:
            self.windowed_scale_factor = scale_factor

            if self.fullscreen:
                logger.warning("Cannot change windowed scale factor while in fullscreen mode.")
                return

        self.scale_factor = scale_factor
        new_width = SCREEN_SIZE[0] * scale_factor
        new_height = SCREEN_SIZE[1] * scale_factor
        self.screen = self.make_screen()
        self.input_manager.set_screen_scale_factor(scale_factor)
        if self.gl_renderer is not None:
            # Recreate GLRenderer and set viewport to known size
            self.gl_renderer = GLRenderer()
            # Explicitly set viewport with calculated dimensions
            self.gl_renderer.ctx.viewport = (0, 0, new_width, new_height)

    def fill(self, color: pg.Color | str) -> None:
        self.surface.fill(color)
        if self.gl_renderer is not None:
            self.gl_renderer.blit_to_lit(self.surface, self.rect)

    def fit(self, surface: pg.Surface) -> pg.Surface:
        if self.gl_renderer is not None:
            return self.gl_renderer.resize_surface_to_fit(surface)
        return pg.transform.scale(surface, self.surface.get_size())

    def update(self) -> None:
        surf = self.surface.copy()
        surf = pg.transform.scale_by(surf, self.scale_factor)
        self.screen.blit(surf, (0, 0))
        if self.gl_renderer:
            self.gl_renderer.update()
        else:
            pg.display.update()
        pg.display.flip()

    def __call__(
        self,
        surface: pg.Surface,
        rect: pg.Rect | None = None,
        *,
        unlit: bool = False,
        fit: bool = False,
        draw_mode: int = 0,
    ) -> None:
        """Draws the given surface to the target rectangle, using the appropriate render backend.

        Args:
            surface (pg.Surface): The surface to draw.
            rect (pg.Rect | None): The target rectangle. If None, uses the surface's rect.
            unlit (bool): If True, draws to the unlit buffer when using GLRenderer.
            fit (bool): If True, scales the surface to fit the target rectangle.
            draw_mode (int): additional layers to draw to for lighting purposes.
        """
        if fit:
            surface = self.fit(surface)
        target_rect = rect if rect is not None else surface.get_rect()

        draw_normal = 2
        draw_mask = 1

        if self.gl_renderer is None:
            # surface, target_rect = self.scale(surface, target_rect)
            self.surface.blit(surface, target_rect)
        elif draw_mode == draw_mask:
            self.gl_renderer.blit_to_light_mask(surface, target_rect)
        elif draw_mode == draw_normal:
            self.gl_renderer.blit_to_normals(surface, target_rect)
        elif unlit:
            self.gl_renderer.blit_to_unlit(surface, target_rect)
        else:
            self.gl_renderer.blit_to_lit(surface, target_rect)
        # reminder about drawing to the outlined layer!
        # use self.gl_renderer.queue_outline_render_object(self.gl_renderer.create_outline_render_object(surface, intensity,z_index, offset, pixel_size))
        # to draw a surface at a position with outline, z index, and other variables
        # the queue is cleared every frame so you need to queue the render object each frame!
