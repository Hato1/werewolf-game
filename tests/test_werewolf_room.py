import pygame as pg
import pytest

from my_game.constants import SCREEN_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.werewolf.assets import Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.registry import STATE_REGISTRY
from my_game.werewolf.room import rooms
from my_game.werewolf.room.loaders import CharacterData, RoomData
from my_game.werewolf.room.models import Character, Prop, Room
from my_game.werewolf.state_data import WerewolfState
from my_game.werewolf.states.main_menu import MainMenu
from my_game.werewolf.states.room_state import RoomState
from my_game.werewolf.states.room_test import RoomTest


def test_room_draws_visible_props_at_their_positions() -> None:
    surface = pg.Surface((8, 8))
    sprite = pg.Surface((2, 2))
    sprite.fill(pg.Color("red"))
    prop = Prop(
        name="test",
        description="A test prop.",
        sprite=sprite,
        position=(3, 4),
        visible=True,
        clickable=True,
        hotspot=None,
        scale=1.0,
        size=None,
        parallax=0.0,
        depth=0,
        baseline=0,
    )
    room = Room("test", "A test room.", props=[prop], hotspots=[], characters=[])

    room.draw(Renderer(surface, None))

    assert surface.get_at((3, 4)) == pg.Color("red")
    assert surface.get_at((0, 0)) == pg.Color("black")


def test_hidden_props_are_not_drawn() -> None:
    surface = pg.Surface((8, 8))
    sprite = pg.Surface((2, 2))
    sprite.fill(pg.Color("red"))
    prop = Prop(
        name="test",
        description="A test prop.",
        sprite=sprite,
        position=(0, 0),
        visible=False,
        clickable=False,
        hotspot=None,
        scale=1.0,
        size=None,
        parallax=0.0,
        depth=0,
        baseline=0,
    )
    room = Room("test", "A test room.", props=[prop], hotspots=[], characters=[])

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


def test_graveyard_chains_click_changes_to_church_cemetery() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    room_state = RoomState(rooms.INN)
    graveyard_chains = room_state.room.props[1]

    room_state.handle_event(
        {Action.MOUSE_SELECT},
        pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=graveyard_chains.rect.center),
    )

    assert room_state.room.name == rooms.CHURCH_CEMETARY.name


def test_player_moves_with_held_input_and_animates() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    room_state = RoomState(rooms.INN)
    player = room_state.player
    bounds = pg.Rect(0, 0, *SCREEN_SIZE)
    start = player.position.copy()

    assert len(player.walk_frames) == 10
    room_state.update(bounds, 0.5, InputState(frozenset({Action.LEFT}), {}))

    assert player.walking
    assert player.facing_left
    assert player.position.x == start.x - player.speed * 0.5
    assert player.position.y == start.y
    assert player.frame_index == 5

    room_state.update(bounds, 0.0, InputState(frozenset(), {}))
    assert not player.walking
    assert player.frame_index == 0


def test_player_stays_within_bounds() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    room_state = RoomState(rooms.INN)
    bounds = pg.Rect(0, 0, *SCREEN_SIZE)

    room_state.update(bounds, 100.0, InputState(frozenset({Action.RIGHT, Action.DOWN}), {}))

    assert room_state.player.position == pg.Vector2(bounds.right, bounds.bottom)


def test_player_is_a_character() -> None:
    pg.init()
    pg.display.set_mode((1, 1))

    assert isinstance(RoomState(rooms.INN).player, Character)


def make_npc(
    position: tuple[int, int], path: tuple[tuple[int, int], ...], *, speed: float, loop: bool = False
) -> Character:
    pg.init()
    pg.display.set_mode((1, 1))
    data = CharacterData(
        name="npc",
        description="An NPC.",
        image=Images.PLAYER_IDLE,
        position=position,
        walk_image=Images.PLAYER_WALK,
        speed=speed,
        path=path,
        loop=loop,
    )
    return Character.from_character_data(data)


def test_character_follows_path_and_stops_on_waypoints() -> None:
    bounds: pg.Rect = pg.Rect(0, 0, *SCREEN_SIZE)
    idle: InputState = InputState(frozenset(), {})
    npc = make_npc((0, 100), ((100, 100), (100, 150)), speed=100)

    npc.update(bounds, 0.5, idle)
    assert npc.walking
    assert npc.position == pg.Vector2(50, 100)

    npc.update(bounds, 0.75, idle)
    assert npc.position == pg.Vector2(100, 100)

    npc.update(bounds, 1.0, idle)
    assert npc.position == pg.Vector2(100, 150)

    npc.update(bounds, 1.0, idle)
    assert not npc.walking
    assert npc.position == pg.Vector2(100, 150)


def test_character_path_can_loop() -> None:
    bounds = pg.Rect(0, 0, *SCREEN_SIZE)
    idle: InputState = InputState(frozenset(), {})
    npc = make_npc((0, 0), ((100, 0), (0, 0)), speed=100, loop=True)

    for _ in range(4):
        npc.update(bounds, 1.0, idle)

    assert npc.position == pg.Vector2(0, 0)
    assert npc.path_index == 2


def test_room_updates_its_characters() -> None:
    npc = make_npc((0, 0), ((10, 0),), speed=10)
    room = Room("test", "A test room.", characters=[npc])

    room.update(pg.Rect(0, 0, *SCREEN_SIZE), 1.0, InputState(frozenset(), {}))

    assert npc.position == pg.Vector2(10, 0)


def test_room_builds_characters_from_room_data() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    npc = CharacterData("npc", "An NPC.", Images.PLAYER_IDLE, (5, 6))

    room = Room.from_room_data(RoomData("char room", "A room with a character.", characters=(npc,)), overwrite=True)

    assert room.characters[0].name == npc.name
    assert room.characters[0].position == pg.Vector2(5, 6)


def test_character_scale_applies_to_all_frames() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    base_data = CharacterData("npc", "An NPC.", Images.PLAYER_IDLE, (0, 0), walk_image=Images.PLAYER_WALK)
    scaled_data = CharacterData("npc", "An NPC.", Images.PLAYER_IDLE, (0, 0), walk_image=Images.PLAYER_WALK, scale=2)
    base = Character.from_character_data(base_data)
    scaled = Character.from_character_data(scaled_data)

    width, height = base.idle_frames[0].get_size()
    assert scaled.idle_frames[0].get_size() == (width * 2, height * 2)
    assert scaled.walk_frames[0].get_size() == (width * 2, height * 2)
    assert len(scaled.walk_frames) == len(base.walk_frames)
