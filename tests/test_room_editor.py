import ast
import signal
import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

from my_game.werewolf import room_editor
from my_game.werewolf.assets import Images
from my_game.werewolf.room import rooms
from my_game.werewolf.room.loaders import HotspotData, RoomData
from my_game.werewolf.room_editor import RoomEditor, _restore_value, update_room_source


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


def test_restore_value_parses_polygon_coordinates_as_tuples() -> None:
    assert _restore_value("[[1, 2], [3, 4]]", ((0, 0),), "polygon") == ((1, 2), (3, 4))


def test_restore_value_parses_embedded_hotspots() -> None:
    hotspot = _restore_value(
        '{"name": "Door", "description": "A door.", "polygon": [[1, 2], [3, 4]]}',
        None,
        "hotspot",
    )

    assert hotspot.name == "Door"
    assert hotspot.polygon == ((1, 2), (3, 4))


def test_restore_value_handles_optional_room_fields() -> None:
    assert _restore_value("null", None, "size") is None
    assert _restore_value("[640, 360]", None, "size") == (640, 360)
    assert _restore_value("PLAYER_WALK", None, "walk_image") is Images.PLAYER_WALK


def test_restore_value_updates_existing_hotspots() -> None:
    original = HotspotData("Old", "Old hotspot.")
    updated = _restore_value(
        '{"name": "New", "description": "Updated.", "polygon": [[10, 20], [30, 40]]}',
        original,
        "hotspot",
    )

    assert updated.name == "New"
    assert updated.polygon == ((10, 20), (30, 40))


def test_drag_updates_selected_content_position() -> None:
    editor = SimpleNamespace(
        selection=("props", 1),
        drag_origin=(10, 20),
        drag_position=(100, 150),
        _set_content_position=Mock(),
    )

    RoomEditor._canvas_drag(cast(RoomEditor, editor), cast(tk.Event, SimpleNamespace(x=20, y=25)))

    editor._set_content_position.assert_called_once_with("props", 1, (110, 155))


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
