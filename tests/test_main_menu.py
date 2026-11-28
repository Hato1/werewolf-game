"""Tests for the mouse-driven main menu parallax."""

from typing import Any, cast

import pygame as pg
import pytest

from my_game.constants import SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.werewolf.assets import Images
from my_game.werewolf.states.main_menu import MainMenu


@pytest.fixture(autouse=True)
def _pygame_display() -> None:
    pg.init()
    pg.display.set_mode((1, 1))


def _input_state() -> InputState:
    return InputState(frozenset(), {})


def _draw_calls(menu: MainMenu) -> list[tuple[pg.Surface, pg.Rect, dict[str, Any]]]:
    calls: list[tuple[pg.Surface, pg.Rect, dict[str, Any]]] = []

    def renderer(surface: pg.Surface, rect: pg.Rect | None = None, **kwargs: Any) -> None:
        target = rect.copy() if rect is not None else surface.get_rect().copy()
        calls.append((surface, target, kwargs))

    menu.draw(cast(Renderer, renderer), 0.0)
    return calls


def test_mouse_position_sets_parallax_target() -> None:
    menu = MainMenu()
    assert menu.parallax == pg.Vector2(0, 0)

    right_event = pg.event.Event(pg.MOUSEMOTION, pos=(SCREEN_SIZE[0], SCREEN_SIZE[1] // 2))
    menu.handle_event(set(), right_event)
    assert menu.parallax_target == pg.Vector2(-1.0, 0.0)

    left_event = pg.event.Event(pg.MOUSEMOTION, pos=(0, 0))
    menu.handle_event(set(), left_event)
    assert menu.parallax_target == pg.Vector2(1.0, 1.0)


def test_parallax_eases_towards_target() -> None:
    menu = MainMenu()
    menu.handle_event(set(), pg.event.Event(pg.MOUSEMOTION, pos=(SCREEN_SIZE[0], SCREEN_SIZE[1] // 2)))

    menu.update(0.1, _input_state())

    assert menu.parallax.x == pytest.approx(-0.6)
    assert menu.parallax.y == pytest.approx(0.0)


def test_layers_shift_by_their_depth() -> None:
    menu = MainMenu()
    menu.parallax.update(-1.0, 0.0)
    calls = _draw_calls(menu)

    for image, depth in MainMenu.PARALLAX_LAYERS:
        rect = next(rect for surface, rect, _ in calls if surface is menu.parallax_surfaces[image])
        assert rect.centerx == pytest.approx(SCREEN_SIZE[0] / 2 - depth, abs=1)


def test_parallax_layers_cover_screen_at_every_extreme() -> None:
    menu = MainMenu()
    screen = pg.Rect((0, 0), SCREEN_SIZE)

    for x, y in ((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)):
        menu.parallax.update(x, y)
        for image, depth in MainMenu.PARALLAX_LAYERS:
            rect = menu._parallax_rect(menu.parallax_surfaces[image], depth)
            assert rect.contains(screen)


def test_clouds_use_parallax_and_still_cover_screen() -> None:
    menu = MainMenu()
    screen = pg.Rect((0, 0), SCREEN_SIZE)

    for x, y in ((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)):
        menu.parallax.update(x, y)
        menu.update(0.0, _input_state())
        cloud_rects = [rect for surface, rect, _ in _draw_calls(menu) if surface is menu.clouds]

        assert len(cloud_rects) == 2
        assert cloud_rects[0].union(cloud_rects[1]).contains(screen)
        assert cloud_rects[0].y == round(y * MainMenu.CLOUD_PARALLAX - menu.cloud_margin)


def test_clouds_stay_between_moon_and_mountains() -> None:
    menu = MainMenu()
    surfaces = [surface for surface, _, _ in _draw_calls(menu)]

    moon_index = surfaces.index(menu.parallax_surfaces[Images.BACKGROUND_FULLMOON])
    clouds_index = surfaces.index(menu.clouds)
    mountains_index = surfaces.index(menu.parallax_surfaces[Images.BG_GEO2])
    assert moon_index < clouds_index < mountains_index


def test_plaque_and_buttons_move_together() -> None:
    menu = MainMenu()
    menu.parallax.update(1.0, -1.0)
    calls = _draw_calls(menu)

    plaque_rect = next(rect for surface, rect, _ in calls if surface is menu.plaque)
    expected_x = round(350 + MainMenu.PLAQUE_PARALLAX[0])
    expected_y = round(-MainMenu.PLAQUE_PARALLAX[1])
    assert plaque_rect.topleft == (expected_x, expected_y)
    assert all(button.rect.topleft == (expected_x, expected_y) for button in menu.buttons)
