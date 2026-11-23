"""Desktop editor for the werewolf game's declarative room definitions."""

import base64
import io
import json
import signal
import tkinter as tk
from dataclasses import fields, is_dataclass, replace
from functools import partial
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

import pygame as pg

from my_game.werewolf.assets import IMAGES_PATH, Images
from my_game.werewolf.room import characters, props, rooms
from my_game.werewolf.room.editor_data import (
    json_value,
    named_values,
    replace_room_contents,
    restore_value,
    update_room_source,
)
from my_game.werewolf.room.loaders import CharacterData, HotspotData, Polygon, PropData, RoomData

ROOMS_PATH = Path(__file__).parent / "room" / "rooms.py"
ROOM_VIEW_SIZE = (480, 208)
VIEW_SCALE = 2
VIEW_SIZE = (ROOM_VIEW_SIZE[0] * VIEW_SCALE, ROOM_VIEW_SIZE[1] * VIEW_SCALE)
POLYGON_DEFAULT = ((100, 100), (240, 100), (240, 200))
MIN_POLYGON_POINTS = 2

CONTENT_FIELDS = ("props", "characters", "hotspots", "regions", "points", "walkable_areas")


class RoomEditor:
    """Tkinter room editor with a live room preview and editable data fields."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Werewolf Room Editor")
        self.root.minsize(1360, 720)

        self.room_definitions = named_values(rooms, RoomData)
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
        """Return the editable definition for the currently selected room."""
        return self.room_data[self.room_key]

    def _build_ui(self) -> None:
        """Create the room preview, editor controls and status line."""
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
        """Create the room selector and save button."""
        header = ttk.Frame(self.root, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Room").pack(side=tk.LEFT)
        self.room_selector = ttk.Combobox(header, state="readonly", width=34)
        self.room_selector.pack(side=tk.LEFT, padx=(8, 14))
        self.room_selector.bind("<<ComboboxSelected>>", self._change_room)
        ttk.Button(header, text="New room", command=self._new_room).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(header, text="Save room definitions", command=self._save).pack(side=tk.LEFT)

    def _build_sidebar(self, body: ttk.Frame) -> None:
        """Create room fields, the content tree and the selected-item form."""
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
        """Switch the preview and content tree to the chosen room."""
        _ = _event
        key = self.room_selector.get()
        if key in self.room_data:
            self.room_key = key
            self.selection = None
            self._refresh_tree()
            self._draw_room()

    def _refresh_tree(self) -> None:
        """Rebuild the room properties and content tree from editable data."""
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
        """Populate the catalog with reusable prop and character definitions."""
        values: dict[str, PropData | CharacterData] = {
            **named_values(props, PropData),
            **named_values(characters, CharacterData),
        }
        self.catalog_items = values
        self.catalog["values"] = list(values)
        if values and not self.catalog.get():
            self.catalog.set(next(iter(values)))

    def _draw_room(self) -> None:
        """Draw room content in depth order using scaled canvas coordinates."""
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
        # for index, region in enumerate(self.room.regions):
        #     self._draw_polygon("regions", index, region, "#8cff66")
        for index, area in enumerate(self.room.walkable_areas):
            self._draw_polygon("walkable_areas", index, area, "#ffffff")
        # for index, point in enumerate(self.room.points):
        #     x, y = point[0] * VIEW_SCALE, point[1] * VIEW_SCALE
        #     self.canvas.create_oval(
        #         x - 5,
        #         y - 5,
        #         x + 5,
        #         y + 5,
        #         fill="#ff55dd",
        #         outline="",
        #         tags=("content", f"points:{index}"),
        #     )

    def _draw_polygon(self, kind: str, index: int, polygon: Polygon, color: str) -> None:
        """Draw a tagged geometry overlay in the scaled preview."""
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
        """Return the sprite dimensions in room coordinates."""
        width, height = self._image_size(image)
        return max(1, round(width * scale)), max(1, round(height * scale))

    def _get_photo(self, image: Images, size: tuple[int, int]) -> tk.PhotoImage:
        """Load and cache a Tk image scaled to the requested canvas dimensions."""
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
        """Select the topmost tagged item and begin dragging movable content."""
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
        """Move the selected prop or character in room-coordinate increments."""
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
        """Finish a drag and refresh the tree and form with the final position."""
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
        """Replace a movable item at its new position and redraw the preview."""
        values = list(getattr(self.room, kind))
        values[index] = replace(values[index], position=position)
        self.room_data[self.room_key] = replace_room_contents(self.room, kind, tuple(values))
        self._draw_room()

    def _tree_select(self, _event: tk.Event) -> None:
        """Update the preview and form when the tree selection changes."""
        _ = _event
        selection = self.tree.selection()
        if not selection or ":" not in selection[0]:
            self.selection = None
            self._refresh_form()
            return
        kind, index = selection[0].rsplit(":", 1)
        self._select_content(kind, int(index))

    def _select_content(self, kind: str, index: int) -> None:
        """Synchronize the selection without retriggering the tree callback."""
        self.selection = (kind, index)
        item_id = f"{kind}:{index}"
        if self.tree.selection() != (item_id,):
            self.tree.selection_set(item_id)
        self._refresh_form()
        self._draw_room()

    def _refresh_form(self) -> None:
        """Build property controls appropriate to the selected content type."""
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
                raw = json_value(current) if data_field.name == "hotspot" else current
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
        """Represent a field value for a single-line text input."""
        if isinstance(value, Images):
            return value.name
        if isinstance(value, tuple):
            return json.dumps(json_value(value))
        if value is None:
            return "null"
        return str(value)

    def _apply_room_fields(self) -> None:
        """Apply the room name and description without changing its contents."""
        self.room_data[self.room_key] = replace(
            self.room,
            name=self.room_name.get(),
            description=self.room_description.get(),
        )
        self._refresh_tree()
        self._draw_room()

    def _apply_content_fields(self) -> None:
        """Parse and apply the selected item's form values to the editable room."""
        if self.selection is None:
            return
        kind, index = self.selection
        values = list(getattr(self.room, kind))
        current = values[index]
        if is_dataclass(current) and not isinstance(current, (CharacterData, HotspotData, PropData)):
            raise TypeError(f"Unsupported room content type: {type(current).__name__}")
        try:
            if not isinstance(current, (CharacterData, HotspotData, PropData)):
                values[index] = restore_value(self.form_vars["coordinates"].get(), current, "coordinates")
            else:
                changes: dict[str, Any] = {}
                field_names = {field.name for field in fields(current)}
                for name, variable in self.form_vars.items():
                    if name in field_names:
                        original = getattr(current, name)
                        raw = variable.get()
                        changes[name] = raw if isinstance(original, bool) else restore_value(raw, original, name)
                for name, text in self.form_texts.items():
                    raw = text.get("1.0", tk.END).strip()
                    changes[name] = restore_value(raw, getattr(current, name), name)
                values[index] = replace(current, **changes)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Invalid room data", str(error), parent=self.root)
            return
        self.room_data[self.room_key] = replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self.tree.selection_set(f"{kind}:{index}")
        self._refresh_form()
        self._draw_room()

    def _add_catalog_item(self, kind: str) -> None:
        """Add the selected reusable prop or character definition."""
        name = self.catalog.get()
        item = self.catalog_items.get(name)
        expected = PropData if kind == "props" else CharacterData
        if not isinstance(item, expected):
            messagebox.showinfo("Choose a catalog item", f"Select a {kind[:-1]} definition first.", parent=self.root)
            return
        values = list(getattr(self.room, kind))
        values.append(item)
        self.room_data[self.room_key] = replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self._select_content(kind, len(values) - 1)

    def _add_geometry(self, kind: str) -> None:
        """Add an editable hotspot, point, region or walkable area."""
        values = list(getattr(self.room, kind))
        if kind == "hotspots":
            values.append(HotspotData(name="New hotspot", description="", polygon=POLYGON_DEFAULT))
        elif kind == "points":
            values.append((ROOM_VIEW_SIZE[0] // 2, ROOM_VIEW_SIZE[1] // 2))
        else:
            values.append(POLYGON_DEFAULT)
        self.room_data[self.room_key] = replace_room_contents(self.room, kind, tuple(values))
        self._refresh_tree()
        self._select_content(kind, len(values) - 1)

    def _delete_selected(self) -> None:
        """Remove the selected content from the current room."""
        if self.selection is None:
            return
        kind, index = self.selection
        values = list(getattr(self.room, kind))
        del values[index]
        self.room_data[self.room_key] = replace_room_contents(self.room, kind, tuple(values))
        self.selection = None
        self._refresh_tree()
        self._refresh_form()
        self._draw_room()

    def _new_room(self) -> None:
        """Create a new empty room with a user-provided name and variable name."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Room")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Room name (displayed in editor):").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=10
        )
        name_var = tk.StringVar(value="New Room")
        ttk.Entry(dialog, textvariable=name_var, width=40).grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5
        )

        ttk.Label(dialog, text="Variable name (Python identifier):").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 0)
        )
        var_name = tk.StringVar(value="NEW_ROOM")
        ttk.Entry(dialog, textvariable=var_name, width=40).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5
        )

        ttk.Label(dialog, text="Description:").grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 0))
        description_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=description_var, width=40).grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5
        )

        def create() -> None:
            """Create the room if the form is valid."""
            name = name_var.get().strip()
            var_name_str = var_name.get().strip()
            description = description_var.get().strip()

            if not name:
                messagebox.showerror("Invalid room name", "Room name cannot be empty.", parent=dialog)
                return
            if not var_name_str:
                messagebox.showerror("Invalid variable name", "Variable name cannot be empty.", parent=dialog)
                return
            if not var_name_str.isidentifier():
                messagebox.showerror(
                    "Invalid variable name", "Variable name must be a valid Python identifier.", parent=dialog
                )
                return
            if var_name_str in self.room_data:
                messagebox.showerror(
                    "Room already exists", f"A room named '{var_name_str}' already exists.", parent=dialog
                )
                return

            new_room = RoomData(name=name, description=description)
            self.room_data[var_name_str] = new_room
            self.room_key = var_name_str
            self.selection = None
            self._refresh_room_selector()
            self._refresh_tree()
            self._draw_room()
            self.status.set(f"Created new room '{var_name_str}'. Remember to save your changes.")
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=2, sticky=tk.E, padx=10, pady=10)
        ttk.Button(button_frame, text="Create", command=create).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=2)

        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

    def _save(self) -> None:
        """Write changed room definitions to the room module."""
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
