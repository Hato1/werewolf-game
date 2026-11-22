"""Desktop editor for the werewolf game's declarative room definitions."""

import ast
import base64
import io
import json
import re
import signal
import tkinter as tk
from collections.abc import Callable
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from functools import partial
from pathlib import Path
from tkinter import messagebox, ttk
from types import ModuleType
from typing import Any

import pygame as pg

from my_game.werewolf.assets import IMAGES_PATH, Images
from my_game.werewolf.room import characters, props, rooms
from my_game.werewolf.room.loaders import CharacterData, HotspotData, Polygon, PropData, RoomData

ROOMS_PATH = Path(__file__).parent / "room" / "rooms.py"
ROOM_VIEW_SIZE = (480, 208)
VIEW_SCALE = 2
VIEW_SIZE = (ROOM_VIEW_SIZE[0] * VIEW_SCALE, ROOM_VIEW_SIZE[1] * VIEW_SCALE)
POLYGON_DEFAULT = ((100, 100), (240, 100), (240, 200))
MIN_POLYGON_POINTS = 2

CONTENT_FIELDS = ("props", "characters", "hotspots", "regions", "points", "walkable_areas")


def _named_values(module: ModuleType, value_type: type) -> dict[str, Any]:
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and isinstance(value, value_type)
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _catalog_reference(value: Any) -> str | None:
    for module_name, module in (("props", props), ("characters", characters)):
        for name, catalog_item in vars(module).items():
            if isinstance(catalog_item, type(value)) and catalog_item == value:
                return f"{module_name}.{name}"
    return None


def _python_expression(value: Any, indent: int = 0, *, use_catalog: bool = True) -> str:
    if use_catalog and (reference := _catalog_reference(value)) is not None:
        return reference
    if isinstance(value, Images):
        return f"Images.{value.name}"
    if is_dataclass(value):
        padding = " " * (indent + 4)
        arguments = [
            f"{padding}{field.name}={_python_expression(getattr(value, field.name), indent + 4)},"
            for field in fields(value)
        ]
        return f"{type(value).__name__}(\n" + "\n".join(arguments) + f"\n{' ' * indent})"
    if isinstance(value, tuple):
        if not value:
            return "()"
        elements = ", ".join(_python_expression(item, indent) for item in value)
        return f"({elements}{',' if len(value) == 1 else ''})"
    return repr(value)


def _set_import(source: str, module_name: str, names: set[str]) -> str:
    tree = ast.parse(source)
    import_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == module_name and node.level == 0
        ),
        None,
    )
    lines = source.splitlines()
    import_line = f"from {module_name} import {', '.join(sorted(names))}"
    if import_node is not None:
        end_line = import_node.end_lineno or import_node.lineno
        lines[import_node.lineno - 1 : end_line] = [import_line]
        return "\n".join(lines) + "\n"

    insert_at = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insert_at = tree.body[0].end_lineno or tree.body[0].lineno
    lines.insert(insert_at, import_line)
    return "\n".join(lines) + "\n"


def _find_room_assignments(tree: ast.Module) -> dict[str, ast.stmt]:
    assignments: dict[str, ast.stmt] = {}
    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node
    return assignments


def update_room_source(source: str, updates: dict[str, RoomData]) -> str:
    """Replace selected room assignments while preserving the rest of rooms.py."""
    tree = ast.parse(source)
    assignments = _find_room_assignments(tree)
    lines = source.splitlines()
    replacements: list[tuple[int, int, list[str]]] = []
    additions: list[str] = []
    for name, room_data in updates.items():
        statement = f"{name} = {_python_expression(room_data, use_catalog=False)}"
        if name in assignments:
            node = assignments[name]
            replacements.append((node.lineno - 1, node.end_lineno or node.lineno, statement.splitlines()))
        else:
            additions.extend(["", statement])
    for start, end, statement_lines in sorted(replacements, reverse=True):
        lines[start:end] = statement_lines
    lines.extend(additions)
    updated = "\n".join(lines).rstrip() + "\n"

    if "Images." in updated:
        updated = _set_import(updated, "my_game.werewolf.assets", {"Images"})

    used_types = {
        data_type.__name__
        for data_type in (CharacterData, HotspotData, PropData, RoomData)
        if re.search(rf"\b{data_type.__name__}\(", updated)
    }
    if used_types:
        updated = _set_import(updated, "my_game.werewolf.room.loaders", used_types)

    if "characters." in updated:
        updated = _set_import(
            updated, "my_game.werewolf.room", {"characters", "props"} if "props." in updated else {"characters"}
        )
    elif "props." not in updated:
        updated = re.sub(r"^from my_game\.werewolf\.room import props\s*\n", "", updated, flags=re.MULTILINE)

    ast.parse(updated)
    return updated


def _restore_boolean(raw_value: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError("Enter true or false.")
    return normalized == "true"


def _restore_tuple(raw_value: str) -> tuple[Any, ...]:
    def tuples(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(tuples(item) for item in value)
        return value

    return tuples(json.loads(raw_value))


def _restore_hotspot(raw_value: str) -> HotspotData | None:
    value = json.loads(raw_value)
    if value is None:
        return None
    return HotspotData(
        name=value["name"],
        description=value["description"],
        polygon=tuple(tuple(point) for point in value.get("polygon", ())),
    )


def _restore_optional(raw_value: str, field_name: str) -> Any:
    normalized = raw_value.strip()
    if normalized.lower() in {"null", "none"}:
        return None
    if field_name in {"size", "path", "position", "polygon"}:
        return _restore_tuple(raw_value)
    if field_name in {"image", "walk_image"}:
        return Images[normalized]
    raise ValueError(f"Unsupported field value for {field_name}.")


def _restore_value(raw_value: str, current: Any, field_name: str) -> Any:
    if isinstance(current, Images):
        return Images[raw_value.strip()]
    if isinstance(current, tuple):
        return _restore_tuple(raw_value)
    if field_name == "hotspot":
        return _restore_hotspot(raw_value)
    if current is None:
        return _restore_optional(raw_value, field_name)
    converters: dict[type, Callable[[str], Any]] = {
        bool: _restore_boolean,
        int: int,
        float: float,
        str: str,
    }
    converter = converters.get(type(current))
    if converter is None:
        raise ValueError(f"Unsupported field value for {field_name}.")
    return converter(raw_value)


def _replace_room_contents(room: RoomData, kind: str, values: tuple[Any, ...]) -> RoomData:
    if kind == "props":
        return replace(room, props=values)
    if kind == "characters":
        return replace(room, characters=values)
    if kind == "hotspots":
        return replace(room, hotspots=values)
    if kind == "regions":
        return replace(room, regions=values)
    if kind == "points":
        return replace(room, points=values)
    if kind == "walkable_areas":
        return replace(room, walkable_areas=values)
    raise ValueError(f"Unknown room content field: {kind}")


class RoomEditor:
    """Tkinter room editor with a live room preview and editable data fields."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Werewolf Room Editor")
        self.root.minsize(1360, 720)

        self.room_definitions = _named_values(rooms, RoomData)
        if not self.room_definitions:
            raise ValueError("No RoomData definitions were found in rooms.py.")
        self.original_definitions = dict(self.room_definitions)
        self.room_data = dict(self.room_definitions)
        self.room_key = next(iter(self.room_data))
        self.selection: tuple[str, int] | None = None
        self.drag_origin: tuple[int, int] | None = None
        self.drag_position: tuple[int, int] | None = None
        self.image_cache: dict[tuple[Images, tuple[int, int]], tk.PhotoImage] = {}
        self.form_vars: dict[str, tk.Variable] = {}
        self.form_texts: dict[str, tk.Text] = {}
        self.room_selector: ttk.Combobox
        self.room_name: tk.StringVar
        self.room_description: tk.StringVar
        self.tree: ttk.Treeview
        self.catalog: ttk.Combobox
        self.catalog_items: dict[str, PropData | CharacterData] = {}
        self.form_canvas: tk.Canvas
        self.form_frame: ttk.Frame
        self.form_window: int
        self.status: tk.StringVar

        self._build_ui()
        self._refresh_room_selector()
        self._refresh_tree()
        self._draw_room()

    @property
    def room(self) -> RoomData:
        return self.room_data[self.room_key]

    def _build_ui(self) -> None:
        self._build_header()
        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(
            body, width=VIEW_SIZE[0], height=VIEW_SIZE[1], background="#252525", highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT, anchor=tk.NW)
        self.canvas.bind("<Button-1>", self._canvas_press)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)
        self._build_sidebar(body)
        self.status = tk.StringVar(value="Drag props or characters in the preview to reposition them.")
        ttk.Label(self.root, textvariable=self.status, anchor=tk.W, padding=(8, 0, 8, 8)).pack(fill=tk.X)

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Room").pack(side=tk.LEFT)
        self.room_selector = ttk.Combobox(header, state="readonly", width=34)
        self.room_selector.pack(side=tk.LEFT, padx=(8, 14))
        self.room_selector.bind("<<ComboboxSelected>>", self._change_room)
        ttk.Button(header, text="Save room definitions", command=self._save).pack(side=tk.LEFT)

    def _build_sidebar(self, body: ttk.Frame) -> None:
        sidebar = ttk.Frame(body, padding=(12, 0, 0, 0), width=380)
        sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sidebar.pack_propagate(flag=False)
        ttk.Label(sidebar, text="Room properties").pack(anchor=tk.W)
        room_form = ttk.Frame(sidebar)
        room_form.pack(fill=tk.X, pady=(4, 8))
        self.room_name = tk.StringVar()
        self.room_description = tk.StringVar()
        ttk.Label(room_form, text="Name").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(room_form, textvariable=self.room_name).grid(row=0, column=1, sticky=tk.EW, padx=4)
        ttk.Label(room_form, text="Description").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(room_form, textvariable=self.room_description).grid(row=1, column=1, sticky=tk.EW, padx=4)
        ttk.Button(room_form, text="Apply", command=self._apply_room_fields).grid(row=0, column=2, rowspan=2, padx=4)
        room_form.columnconfigure(1, weight=1)

        self.tree = ttk.Treeview(sidebar, show="tree", height=11, selectmode="browse")
        self.tree.pack(fill=tk.X)
        self.tree.bind("<<TreeviewSelect>>", self._tree_select)
        actions = ttk.Frame(sidebar)
        actions.pack(fill=tk.X, pady=6)
        self.catalog = ttk.Combobox(actions, state="readonly")
        self.catalog.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(actions, text="Add prop", command=lambda: self._add_catalog_item("props")).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text="Add character", command=lambda: self._add_catalog_item("characters")).pack(
            side=tk.LEFT, padx=2
        )
        tools = ttk.Frame(sidebar)
        tools.pack(fill=tk.X, pady=(0, 6))
        for label, kind in (
            ("Region", "regions"),
            ("Hotspot", "hotspots"),
            ("Point", "points"),
            ("Walkable area", "walkable_areas"),
        ):
            ttk.Button(
                tools,
                text=f"Add {label}",
                command=partial(self._add_geometry, kind),
            ).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(tools, text="Delete selected", command=self._delete_selected).pack(side=tk.RIGHT)

        ttk.Label(sidebar, text="Selected content properties").pack(anchor=tk.W, pady=(2, 0))
        form_container = ttk.Frame(sidebar)
        form_container.pack(fill=tk.BOTH, expand=True)
        self.form_canvas = tk.Canvas(form_container, highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(form_container, orient=tk.VERTICAL, command=self.form_canvas.yview)
        self.form_canvas.configure(yscrollcommand=form_scrollbar.set)
        self.form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.form_frame = ttk.Frame(self.form_canvas)
        self.form_window = self.form_canvas.create_window((0, 0), window=self.form_frame, anchor=tk.NW)
        self.form_frame.bind("<Configure>", self._resize_form_scroll)
        self.form_canvas.bind("<Configure>", self._resize_form_width)
        ttk.Button(sidebar, text="Apply content changes", command=self._apply_content_fields).pack(
            anchor=tk.E, pady=(5, 0)
        )

    def _resize_form_scroll(self, _event: tk.Event) -> None:
        _ = _event
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

    def _resize_form_width(self, event: tk.Event) -> None:
        self.form_canvas.itemconfigure(self.form_window, width=event.width)

    def _refresh_room_selector(self) -> None:
        self.room_selector["values"] = list(self.room_data)
        self.room_selector.set(self.room_key)

    def _change_room(self, _event: tk.Event) -> None:
        _ = _event
        key = self.room_selector.get()
        if key in self.room_data:
            self.room_key = key
            self.selection = None
            self._refresh_tree()
            self._draw_room()

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.room_name.set(self.room.name)
        self.room_description.set(self.room.description)
        for kind in CONTENT_FIELDS:
            parent = self.tree.insert("", tk.END, iid=kind, text=f"{kind.replace('_', ' ').title()}")
            for index, value in enumerate(getattr(self.room, kind)):
                label = getattr(value, "name", None) or str(value)
                self.tree.insert(parent, tk.END, iid=f"{kind}:{index}", text=f"{index}: {label}")
            self.tree.item(parent, open=True)
        self._refresh_catalog()

    def _refresh_catalog(self) -> None:
        values = {**_named_values(props, PropData), **_named_values(characters, CharacterData)}
        self.catalog_items = values
        self.catalog["values"] = list(values)
        if values and not self.catalog.get():
            self.catalog.set(next(iter(values)))

    def _draw_room(self) -> None:
        self.canvas.delete("all")
        for index, prop in sorted(enumerate(self.room.props), key=lambda item: item[1].depth, reverse=True):
            size = prop.size or self._scaled_size(prop.image, prop.scale)
            photo = self._get_photo(prop.image, (size[0] * VIEW_SCALE, size[1] * VIEW_SCALE))
            self.canvas.create_image(
                (prop.position[0] * VIEW_SCALE, prop.position[1] * VIEW_SCALE),
                image=photo,
                anchor=tk.NW,
                tags=("content", f"props:{index}"),
            )
            if self.selection == ("props", index):
                self.canvas.create_rectangle(
                    prop.position[0] * VIEW_SCALE,
                    prop.position[1] * VIEW_SCALE,
                    (prop.position[0] + size[0]) * VIEW_SCALE,
                    (prop.position[1] + size[1]) * VIEW_SCALE,
                    outline="#ffcc00",
                    width=2,
                )

        for index, character in enumerate(self.room.characters):
            size = self._scaled_size(character.image, character.scale)
            photo = self._get_photo(character.image, (size[0] * VIEW_SCALE, size[1] * VIEW_SCALE))
            self.canvas.create_image(
                (character.position[0] * VIEW_SCALE, character.position[1] * VIEW_SCALE),
                image=photo,
                anchor=tk.S,
                tags=("content", f"characters:{index}"),
            )
            if self.selection == ("characters", index):
                rect = self.canvas.bbox(f"characters:{index}")
                if rect is None:
                    rect = (
                        character.position[0] * VIEW_SCALE - size[0] * VIEW_SCALE // 2,
                        (character.position[1] - size[1]) * VIEW_SCALE,
                        character.position[0] * VIEW_SCALE + size[0] * VIEW_SCALE // 2,
                        character.position[1] * VIEW_SCALE,
                    )
                self.canvas.create_rectangle(rect, outline="#ffcc00", width=2)

        for index, hotspot in enumerate(self.room.hotspots):
            self._draw_polygon("hotspots", index, hotspot.polygon, "#00d8ff")
        for index, region in enumerate(self.room.regions):
            self._draw_polygon("regions", index, region, "#8cff66")
        for index, area in enumerate(self.room.walkable_areas):
            self._draw_polygon("walkable_areas", index, area, "#ffffff")
        for index, point in enumerate(self.room.points):
            x, y = point[0] * VIEW_SCALE, point[1] * VIEW_SCALE
            self.canvas.create_oval(
                x - 5,
                y - 5,
                x + 5,
                y + 5,
                fill="#ff55dd",
                outline="",
                tags=("content", f"points:{index}"),
            )

    def _draw_polygon(self, kind: str, index: int, polygon: Polygon, color: str) -> None:
        if len(polygon) < MIN_POLYGON_POINTS:
            return
        self.canvas.create_polygon(
            tuple((x * VIEW_SCALE, y * VIEW_SCALE) for x, y in polygon),
            outline=color,
            fill="",
            width=2,
            tags=("content", f"{kind}:{index}"),
        )

    def _image_size(self, image: Images) -> tuple[int, int]:
        return pg.image.load(str(IMAGES_PATH / image.value)).get_size()

    def _scaled_size(self, image: Images, scale: float) -> tuple[int, int]:
        width, height = self._image_size(image)
        return max(1, round(width * scale)), max(1, round(height * scale))

    def _get_photo(self, image: Images, size: tuple[int, int]) -> tk.PhotoImage:
        key = image, size
        if key not in self.image_cache:
            surface = pg.image.load(str(IMAGES_PATH / image.value))
            scaled = pg.transform.smoothscale(surface, size)
            output = io.BytesIO()
            pg.image.save(scaled, output, "room-editor-preview.png")
            png_data = base64.b64encode(output.getvalue())
            self.image_cache[key] = tk.PhotoImage(data=png_data, format="png")
        return self.image_cache[key]

    def _canvas_press(self, event: tk.Event) -> None:
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for canvas_item in reversed(overlapping):
            for tag in self.canvas.gettags(canvas_item):
                kind = next((name for name in CONTENT_FIELDS if tag.startswith(f"{name}:")), None)
                if kind is not None:
                    index = int(tag.removeprefix(f"{kind}:"))
                    self._select_content(kind, index)
                    if kind in {"props", "characters"}:
                        self.drag_origin = (event.x, event.y)
                        self.drag_position = getattr(self.room, kind)[index].position
                    return
        self.selection = None
        self.drag_origin = None
        self._refresh_form()
        self._draw_room()

    def _canvas_drag(self, event: tk.Event) -> None:
        if self.selection is None or self.drag_origin is None or self.drag_position is None:
            return
        kind, index = self.selection
        if kind not in {"props", "characters"}:
            return
        delta_x = round((event.x - self.drag_origin[0]) / VIEW_SCALE)
        delta_y = round((event.y - self.drag_origin[1]) / VIEW_SCALE)
        target = self.drag_position[0] + delta_x, self.drag_position[1] + delta_y
        self._set_content_position(kind, index, target)

    def _canvas_release(self, event: tk.Event) -> None:
        if self.selection is not None:
            kind, index = self.selection
            if kind in {"props", "characters"} and self.drag_origin is not None and self.drag_position is not None:
                target = (
                    self.drag_position[0] + round((event.x - self.drag_origin[0]) / VIEW_SCALE),
                    self.drag_position[1] + round((event.y - self.drag_origin[1]) / VIEW_SCALE),
                )
                if target != getattr(self.room, kind)[index].position:
                    self._set_content_position(kind, index, target)
            self._refresh_tree()
            self.tree.selection_set(f"{self.selection[0]}:{self.selection[1]}")
            self._refresh_form()
        self.drag_origin = None
        self.drag_position = None

    def _set_content_position(self, kind: str, index: int, position: tuple[int, int]) -> None:
        values = list(getattr(self.room, kind))
        values[index] = replace(values[index], position=position)
        self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
        self._draw_room()

    def _tree_select(self, _event: tk.Event) -> None:
        _ = _event
        selection = self.tree.selection()
        if not selection or ":" not in selection[0]:
            self.selection = None
            self._refresh_form()
            return
        kind, index = selection[0].rsplit(":", 1)
        self._select_content(kind, int(index))

    def _select_content(self, kind: str, index: int) -> None:
        self.selection = (kind, index)
        item_id = f"{kind}:{index}"
        if self.tree.selection() != (item_id,):
            self.tree.selection_set(item_id)
        self._refresh_form()
        self._draw_room()

    def _refresh_form(self) -> None:
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.form_vars.clear()
        self.form_texts.clear()
        if self.selection is None:
            return
        kind, index = self.selection
        value = getattr(self.room, kind)[index]
        for row, data_field in enumerate(fields(value) if is_dataclass(value) else []):
            current = getattr(value, data_field.name)
            ttk.Label(self.form_frame, text=data_field.name).grid(row=row, column=0, sticky=tk.NW, padx=(0, 6), pady=2)
            if isinstance(current, bool):
                boolean_var = tk.BooleanVar(value=current)
                ttk.Checkbutton(self.form_frame, variable=boolean_var).grid(row=row, column=1, sticky=tk.W, pady=2)
                self.form_vars[data_field.name] = boolean_var
            elif isinstance(current, Images):
                image_var = tk.StringVar(value=current.name)
                ttk.Combobox(
                    self.form_frame,
                    textvariable=image_var,
                    values=[image.name for image in Images],
                    state="readonly",
                ).grid(row=row, column=1, sticky=tk.EW, pady=2)
                self.form_vars[data_field.name] = image_var
            elif data_field.name in {"description", "hotspot"}:
                text = tk.Text(self.form_frame, width=24, height=3, wrap=tk.WORD)
                raw = _json_value(current) if data_field.name == "hotspot" else current
                text.insert("1.0", json.dumps(raw) if data_field.name == "hotspot" else str(raw))
                text.grid(row=row, column=1, sticky=tk.EW, pady=2)
                self.form_texts[data_field.name] = text
            else:
                field_var = tk.StringVar(value=self._field_text(current))
                ttk.Entry(self.form_frame, textvariable=field_var).grid(row=row, column=1, sticky=tk.EW, pady=2)
                self.form_vars[data_field.name] = field_var
        if isinstance(value, tuple):
            coordinate_var = tk.StringVar(value=self._field_text(value))
            ttk.Label(self.form_frame, text="coordinates").grid(row=0, column=0, sticky=tk.NW, padx=(0, 6), pady=2)
            ttk.Entry(self.form_frame, textvariable=coordinate_var).grid(row=0, column=1, sticky=tk.EW, pady=2)
            self.form_vars["coordinates"] = coordinate_var
        self.form_frame.columnconfigure(1, weight=1)

    @staticmethod
    def _field_text(value: Any) -> str:
        if isinstance(value, Images):
            return value.name
        if isinstance(value, tuple):
            return json.dumps(_json_value(value))
        if value is None:
            return "null"
        return str(value)

    def _apply_room_fields(self) -> None:
        self.room_data[self.room_key] = replace(
            self.room,
            name=self.room_name.get(),
            description=self.room_description.get(),
        )
        self._refresh_tree()
        self._draw_room()

    def _apply_content_fields(self) -> None:
        if self.selection is None:
            return
        kind, index = self.selection
        values = list(getattr(self.room, kind))
        current = values[index]
        changes: dict[str, Any] = {}
        if not is_dataclass(current):
            try:
                values[index] = _restore_value(self.form_vars["coordinates"].get(), current, "coordinates")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                messagebox.showerror("Invalid room data", str(error), parent=self.root)
                return
            self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
            self._refresh_tree()
            self.tree.selection_set(f"{kind}:{index}")
            self._refresh_form()
            self._draw_room()
            return
        if not isinstance(current, (CharacterData, HotspotData, PropData)):
            raise TypeError(f"Unsupported room content type: {type(current).__name__}")
        try:
            for name, variable in self.form_vars.items():
                if name in {field.name for field in fields(current)}:
                    original = getattr(current, name)
                    raw = variable.get()
                    changes[name] = raw if isinstance(original, bool) else _restore_value(raw, original, name)
            for name, text in self.form_texts.items():
                raw = text.get("1.0", tk.END).strip()
                changes[name] = _restore_value(raw, getattr(current, name), name)
            values[index] = replace(current, **changes)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Invalid room data", str(error), parent=self.root)
            return
        self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self.tree.selection_set(f"{kind}:{index}")
        self._refresh_form()
        self._draw_room()

    def _add_catalog_item(self, kind: str) -> None:
        name = self.catalog.get()
        item = self.catalog_items.get(name)
        expected = PropData if kind == "props" else CharacterData
        if not isinstance(item, expected):
            messagebox.showinfo("Choose a catalog item", f"Select a {kind[:-1]} definition first.", parent=self.root)
            return
        values = list(getattr(self.room, kind))
        values.append(item)
        self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self._select_content(kind, len(values) - 1)

    def _add_geometry(self, kind: str) -> None:
        values = list(getattr(self.room, kind))
        if kind == "hotspots":
            values.append(HotspotData(name="New hotspot", description="", polygon=POLYGON_DEFAULT))
        elif kind == "points":
            values.append((ROOM_VIEW_SIZE[0] // 2, ROOM_VIEW_SIZE[1] // 2))
        else:
            values.append(POLYGON_DEFAULT)
        self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self._select_content(kind, len(values) - 1)

    def _delete_selected(self) -> None:
        if self.selection is None:
            return
        kind, index = self.selection
        values = list(getattr(self.room, kind))
        del values[index]
        self.room_data[self.room_key] = _replace_room_contents(self.room, kind, tuple(values))
        self.selection = None
        self._refresh_tree()
        self._refresh_form()
        self._draw_room()

    def _save(self) -> None:
        updates = {name: data for name, data in self.room_data.items() if data != self.original_definitions.get(name)}
        if not updates:
            self.status.set("No changes to save.")
            return
        try:
            source = ROOMS_PATH.read_text(encoding="utf-8")
            updated_source = update_room_source(source, updates)
            ROOMS_PATH.write_text(updated_source, encoding="utf-8")
        except (OSError, SyntaxError, ValueError) as error:
            messagebox.showerror("Could not save room definitions", str(error), parent=self.root)
            return
        self.original_definitions.update(updates)
        self.status.set(f"Saved {len(updates)} room definition(s) to {ROOMS_PATH.name}.")


def run() -> None:
    """Launch the room editor."""
    root = tk.Tk()
    interrupted = False
    closed = False
    previous_sigint_handler = signal.getsignal(signal.SIGINT)

    def close_root() -> None:
        nonlocal closed
        if not closed:
            closed = True
            root.destroy()

    def request_shutdown(*signal_args: Any) -> None:
        nonlocal interrupted
        interrupted = bool(signal_args)

    def check_shutdown() -> None:
        if interrupted:
            close_root()
        else:
            root.after(100, check_shutdown)

    signal.signal(signal.SIGINT, request_shutdown)
    root.protocol("WM_DELETE_WINDOW", close_root)
    root.after(100, check_shutdown)
    try:
        RoomEditor(root)
        root.mainloop()
    finally:
        close_root()
        signal.signal(signal.SIGINT, previous_sigint_handler)


if __name__ == "__main__":
    run()
