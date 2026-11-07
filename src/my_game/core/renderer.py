"""Callable drawing interface that routes surfaces to the active render backend."""

import pygame as pg

from my_game.core.gl_renderer import GLRenderer


class Renderer:
    def __init__(self, surface: pg.Surface, gl_renderer: GLRenderer | None) -> None:
        self.surface = surface
        self.gl_renderer = gl_renderer

    @property
    def rect(self) -> pg.Rect:
        return self.surface.get_rect()

    def fill(self, color: pg.Color | str) -> None:
        self.surface.fill(color)
        if self.gl_renderer is not None:
            self.gl_renderer.blit_to_lit(self.surface, self.rect)

    def fit(self, surface: pg.Surface) -> pg.Surface:
        if self.gl_renderer is not None:
            return self.gl_renderer.resize_surface_to_fit(surface)
        return pg.transform.scale(surface, self.surface.get_size())

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
            self.surface.blit(surface, target_rect)
        elif draw_mode == draw_mask:
            self.gl_renderer.blit_to_light_mask(surface, target_rect)
        elif draw_mode == draw_normal:
            self.gl_renderer.blit_to_normals(surface, target_rect)
        elif unlit:
            self.gl_renderer.blit_to_unlit(surface, target_rect)
        else:
            self.gl_renderer.blit_to_lit(surface, target_rect)
