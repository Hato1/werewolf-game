import pygame as pg
import pytest

from my_game.constants import SCREEN_SIZE
from my_game.werewolf.assets import Images, Rooms
from my_game.werewolf.room_data import PropData, RoomData, build_room, load_room, room_from_json, room_to_json


def test_bundled_room_file_round_trips() -> None:
    data = room_from_json(Rooms.TEST_ROOM.load())

    assert room_from_json(room_to_json(data)) == data


def test_room_from_json_converts_lists_to_tuples() -> None:
    data = room_from_json(Rooms.TEST_ROOM.load())

    assert data.props[0].size == SCREEN_SIZE
    assert data.props[1].position == (771, 379)


@pytest.mark.parametrize(
    "text",
    [
        '{"name": "r", "description": "d", "bogus": 1}',
        '{"name": "r", "description": "d", "props": [{"name": "p", "description": "d", "image": "a.png", "bogus": 1}]}',
    ],
)
def test_room_from_json_rejects_unknown_keys(text: str) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        room_from_json(text)


def test_load_room_builds_props_from_data() -> None:
    pg.init()
    pg.display.set_mode((1, 1))

    room = load_room(Rooms.TEST_ROOM)
    background, studio = room.props

    assert room.name == "Test Room"
    assert background.sprite.get_size() == SCREEN_SIZE
    assert not background.clickable
    assert studio.position == (771, 379)
    assert studio.sprite.get_size() == (141, 161)
    assert studio.clickable


def test_build_room_applies_prop_flags() -> None:
    pg.init()
    pg.display.set_mode((1, 1))
    data = RoomData(
        "r", "d", [PropData("p", "d", Images.STUDIO, height=3, parallax=0.5, visible=False, clickable=False)]
    )

    prop = build_room(data).props[0]

    assert (prop.height, prop.parallax, prop.visible, prop.clickable) == (3, 0.5, False, False)


def test_unknown_image_is_rejected() -> None:
    text = '{"name": "r", "description": "d", "props": [{"name": "p", "description": "d", "image": "nope.png"}]}'
    with pytest.raises(ValueError, match=r"nope\.png"):
        room_from_json(text)
