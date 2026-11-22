import ast
import importlib.util
import signal
import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, call

import pytest

from my_game.werewolf import room_editor
from my_game.werewolf.assets import Images
from my_game.werewolf.room import characters, rooms
from my_game.werewolf.room.editor_data import restore_value, update_room_source
from my_game.werewolf.room.loaders import HotspotData, RoomData
from my_game.werewolf.room_editor import RoomEditor


def test_update_room_source_replaces_multiple_rooms_and_preserves_other_source() -> None:
    source = '''"""Room definitions."""

from my_game.werewolf.room import props
from my_game.werewolf.room.loaders import RoomData

FIRST = RoomData(name="First", description="Before", props=(props.BACKGROUND,))
SECOND = RoomData(name="Second", description="Before")
UNCHANGED = "keep me"
'''
    first = replace(rooms.TEST_ROOM, description="Edited test room.")
    second = replace(rooms.INN, description="Edited inn.")

    updated = update_room_source(source, {"FIRST": first, "SECOND": second})
    tree = ast.parse(updated)
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert ast.unparse(assignments["FIRST"]).startswith("RoomData(")
    assert ast.unparse(assignments["SECOND"]).startswith("RoomData(")
    assert ast.unparse(assignments["UNCHANGED"]) == "'keep me'"
    assert "Edited test room." in updated
    assert "Edited inn." in updated


def test_update_room_source_appends_new_room_assignment() -> None:
    source = '"""Room definitions."""\n'
    room_data = RoomData(name="New room", description="Created in editor.")

    updated = update_room_source(source, {"NEW_ROOM": room_data})
    tree = ast.parse(updated)

    assert any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "NEW_ROOM" for target in node.targets)
        for node in tree.body
    )


def test_generated_room_source_round_trips_all_content(tmp_path: Path) -> None:
    hotspot = HotspotData("Door", "A door.", ((1, 2), (3, 4), (5, 6)))
    prop = replace(rooms.INN.props[1], position=(25, 30), hotspot=hotspot)
    room_data = RoomData(
        name="Edited room",
        description="A room with editor content.",
        props=(prop,),
        hotspots=(hotspot,),
        characters=(characters.PLAYER,),
        regions=(((10, 20), (30, 40), (50, 60)),),
        points=((70, 80),),
        walkable_areas=(((0, 0), (100, 0), (100, 100)),),
    )
    path = tmp_path / "edited_rooms.py"
    path.write_text(update_room_source('"""Rooms."""\n', {"EDITED_ROOM": room_data}), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("edited_rooms", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.EDITED_ROOM == room_data


def test_restore_value_parses_polygon_coordinates_as_tuples() -> None:
    assert restore_value("[[1, 2], [3, 4]]", ((0, 0),), "polygon") == ((1, 2), (3, 4))


def test_restore_value_parses_embedded_hotspots() -> None:
    hotspot = restore_value(
        '{"name": "Door", "description": "A door.", "polygon": [[1, 2], [3, 4]]}',
        None,
        "hotspot",
    )

    assert hotspot.name == "Door"
    assert hotspot.polygon == ((1, 2), (3, 4))


def test_restore_value_handles_optional_room_fields() -> None:
    assert restore_value("null", None, "size") is None
    assert restore_value("[640, 360]", None, "size") == (640, 360)
    assert restore_value("PLAYER_WALK", None, "walk_image") is Images.PLAYER_WALK


def test_restore_value_updates_existing_hotspots() -> None:
    original = HotspotData("Old", "Old hotspot.")
    updated = restore_value(
        '{"name": "New", "description": "Updated.", "polygon": [[10, 20], [30, 40]]}',
        original,
        "hotspot",
    )

    assert updated.name == "New"
    assert updated.polygon == ((10, 20), (30, 40))


@pytest.mark.parametrize(("mouse", "expected"), [((20, 26), (105, 153)), ((0, 14), (95, 147))])
def test_drag_updates_selected_content_position(mouse: tuple[int, int], expected: tuple[int, int]) -> None:
    editor = SimpleNamespace(
        selection=("props", 1),
        drag_origin=(10, 20),
        drag_position=(100, 150),
        _set_content_position=Mock(),
    )

    RoomEditor._canvas_drag(cast(RoomEditor, editor), cast(tk.Event, SimpleNamespace(x=mouse[0], y=mouse[1])))

    editor._set_content_position.assert_called_once_with("props", 1, expected)


def test_preview_canvas_uses_room_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    editor = RoomEditor.__new__(RoomEditor)
    editor.root = Mock(spec=tk.Tk)
    monkeypatch.setattr(editor, "_build_header", Mock())
    monkeypatch.setattr(editor, "_build_sidebar", Mock())
    canvas = Mock()
    monkeypatch.setattr(room_editor.tk, "Canvas", canvas)
    monkeypatch.setattr(room_editor.tk, "StringVar", Mock())
    monkeypatch.setattr(room_editor.ttk, "Frame", Mock())
    monkeypatch.setattr(room_editor.ttk, "Label", Mock())

    editor._build_ui()

    assert canvas.call_args.kwargs["width"] == 960
    assert canvas.call_args.kwargs["height"] == 416


@pytest.mark.parametrize("kind", ["points", "hotspots", "regions", "walkable_areas"])
def test_new_geometry_is_inside_room(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    editor = RoomEditor.__new__(RoomEditor)
    editor.room_key = "TEST"
    editor.room_data = {"TEST": RoomData(name="Test", description="")}
    monkeypatch.setattr(editor, "_refresh_tree", Mock())
    monkeypatch.setattr(editor, "_select_content", Mock())

    editor._add_geometry(kind)

    content = getattr(editor.room, kind)[0]
    points = (content,) if kind == "points" else content.polygon if isinstance(content, HotspotData) else content
    assert all(0 <= x < 480 and 0 <= y < 208 for x, y in points)
    if kind == "points":
        assert content == (240, 104)


@pytest.mark.parametrize("kind", ["points", "props"])
def test_apply_content_fields_updates_room(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    editor = RoomEditor.__new__(RoomEditor)
    editor.room_key = "TEST"
    prop = rooms.INN.props[1]
    editor.room_data = {"TEST": RoomData(name="Test", description="", points=((10, 20),), props=(prop,))}
    editor.selection = (kind, 0)
    field_name = "coordinates" if kind == "points" else "position"
    editor.form_vars = {field_name: Mock(get=Mock(return_value="[40, 50]"))}
    editor.form_texts = {}
    editor.tree = Mock(spec=room_editor.ttk.Treeview)
    monkeypatch.setattr(editor, "_refresh_tree", Mock())
    monkeypatch.setattr(editor, "_refresh_form", Mock())
    monkeypatch.setattr(editor, "_draw_room", Mock())

    editor._apply_content_fields()

    assert editor.room.points == (((40, 50) if kind == "points" else (10, 20)),)
    assert editor.room.props[0].position == ((40, 50) if kind == "props" else prop.position)


def test_preview_scales_content_and_overlays(monkeypatch: pytest.MonkeyPatch) -> None:
    editor = RoomEditor.__new__(RoomEditor)
    editor.room_key = "TEST"
    prop = replace(rooms.INN.props[1], position=(30, 40), size=(10, 20))
    character = replace(characters.PLAYER, position=(120, 150))
    editor.room_data = {
        "TEST": RoomData(
            name="Test",
            description="",
            props=(prop,),
            characters=(character,),
            hotspots=(HotspotData("Door", "", ((10, 20), (30, 40), (50, 60))),),
            points=((100, 150),),
        )
    }
    editor.selection = ("props", 0)
    editor.canvas = Mock(spec=tk.Canvas)
    photo = object()
    get_photo = Mock(return_value=photo)
    monkeypatch.setattr(editor, "_scaled_size", Mock(return_value=(8, 12)))
    monkeypatch.setattr(editor, "_get_photo", get_photo)

    editor._draw_room()

    assert editor.canvas.create_image.call_args_list == [
        call((60, 80), image=photo, anchor=tk.NW, tags=("content", "props:0")),
        call((240, 300), image=photo, anchor=tk.S, tags=("content", "characters:0")),
    ]
    assert get_photo.call_args_list == [call(prop.image, (20, 40)), call(character.image, (16, 24))]
    editor.canvas.create_rectangle.assert_called_once_with(60, 80, 80, 120, outline="#ffcc00", width=2)
    editor.canvas.create_polygon.assert_called_once_with(
        ((20, 40), (60, 80), (100, 120)),
        outline="#00d8ff",
        fill="",
        width=2,
        tags=("content", "hotspots:0"),
    )
    editor.canvas.create_oval.assert_called_once_with(
        195, 295, 205, 305, fill="#ff55dd", outline="", tags=("content", "points:0")
    )


def test_release_uses_room_coordinates() -> None:
    prop = replace(rooms.INN.props[1], position=(100, 150))
    editor = SimpleNamespace(
        selection=("props", 0),
        drag_origin=(10, 20),
        drag_position=prop.position,
        room=RoomData(name="Test", description="", props=(prop,)),
        tree=Mock(),
        _set_content_position=Mock(),
        _refresh_tree=Mock(),
        _refresh_form=Mock(),
    )

    RoomEditor._canvas_release(cast(RoomEditor, editor), cast(tk.Event, SimpleNamespace(x=30, y=10)))

    editor._set_content_position.assert_called_once_with("props", 0, (110, 145))


def test_selecting_canvas_content_does_not_reselect_same_tree_item() -> None:
    tree = Mock()
    tree.selection.return_value = ("props:0",)
    editor = SimpleNamespace(
        selection=None,
        tree=tree,
        _refresh_form=Mock(),
        _draw_room=Mock(),
    )

    RoomEditor._select_content(cast(RoomEditor, editor), "props", 0)

    tree.selection_set.assert_not_called()
    editor._refresh_form.assert_called_once()
    editor._draw_room.assert_called_once()


def test_first_sigint_closes_the_editor(monkeypatch) -> None:
    class Root:
        def __init__(self) -> None:
            self.callbacks: list[Callable[[], None]] = []
            self.destroyed = False

        def after(self, _delay, callback) -> None:
            self.callbacks.append(callback)

        def protocol(self, *_args) -> None: ...

        def bind(self, *_args) -> None: ...

        def mainloop(self) -> None:
            signal_handlers[0](signal.SIGINT, None)
            self.callbacks.pop(0)()

        def destroy(self) -> None:
            self.destroyed = True

    root = Root()
    signal_handlers: list[Callable[..., None]] = []
    monkeypatch.setattr(room_editor.tk, "Tk", lambda: root)
    monkeypatch.setattr(room_editor, "RoomEditor", lambda _root: None)
    monkeypatch.setattr(room_editor.signal, "getsignal", lambda _signal: "previous")
    monkeypatch.setattr(room_editor.signal, "signal", lambda _signal, handler: signal_handlers.append(handler))

    room_editor.run()

    assert root.destroyed
