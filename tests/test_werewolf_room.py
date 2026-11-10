import pygame as pg
import pytest

from my_game.constants import SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.werewolf.inputs import Action
from my_game.werewolf.registry import STATE_REGISTRY
from my_game.werewolf.room.models import Prop, Room
from my_game.werewolf.state_data import WerewolfState
from my_game.werewolf.states.main_menu import MainMenu
from my_game.werewolf.states.room_test import RoomTest


def test_room_draws_visible_props_at_their_positions() -> None:
    surface = pg.Surface((8, 8))
    sprite = pg.Surface((2, 2))
    sprite.fill(pg.Color("red"))
    prop = Prop("test", "A test prop.", sprite)
    prop.position = (3, 4)
    room = Room("test", "A test room.", [prop], [], [])

    room.draw(Renderer(surface, None))

    assert surface.get_at((3, 4)) == pg.Color("red")
    assert surface.get_at((0, 0)) == pg.Color("black")


def test_hidden_props_are_not_drawn() -> None:
    surface = pg.Surface((8, 8))
    sprite = pg.Surface((2, 2))
    sprite.fill(pg.Color("red"))
    prop = Prop("test", "A test prop.", sprite)
    prop.hide()
    room = Room("test", "A test room.", [prop], [], [])

    room.draw(Renderer(surface, None))

    assert surface.get_at((0, 0)) == pg.Color("black")


def test_main_menu_opens_registered_test_room() -> None:
    pg.init()
    pg.display.set_mode((1, 1))

    menu = MainMenu()
    room_state = RoomTest()

    assert menu.buttons[0].next_state is WerewolfState.TEST_ROOM
    assert STATE_REGISTRY.factories[WerewolfState.TEST_ROOM] is RoomTest
    assert room_state.room.props[0].sprite.get_size() == SCREEN_SIZE

    room_state.handle_event({Action.UI_CANCEL}, pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE))

    assert room_state.done
    assert room_state.next_state is WerewolfState.MAIN_MENU


def test_studio_prop_click_shows_description_for_three_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    room_state = RoomTest()
    studio = room_state.room.props[1]
    ticks = 1_000
    monkeypatch.setattr(pg.time, "get_ticks", lambda: ticks)

    room_state.handle_event(
        {Action.MOUSE_SELECT},
        pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=studio.rect.center),
    )

    assert room_state.message_surface is not None
    assert room_state.message_expires_at == ticks + room_state.MESSAGE_DURATION_MS

    ticks += room_state.MESSAGE_DURATION_MS - 1
    room_state.update(pg.Rect(0, 0, *SCREEN_SIZE), 0, InputState(frozenset(), {}))
    assert room_state.message_surface is not None

    ticks += 1
    room_state.update(pg.Rect(0, 0, *SCREEN_SIZE), 0, InputState(frozenset(), {}))
    assert room_state.message_surface is None
