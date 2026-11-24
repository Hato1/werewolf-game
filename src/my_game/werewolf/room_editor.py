"""Room editor UI for the werewolf game.

Type ignore statements are used for the following unavoidable issues:
- Lambda captures in callbacks: Mypy cannot infer types through default arguments in lambdas
- Dict unpacking with Any values: Needed when spreading dynamic field changes
- Optional value indexing: Occurs with optional list items from form state
"""

import argparse
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
from tkinter import Event, Misc, TclError
from tkinter.constants import LEFT, NW, TOP
from typing import Any, Literal, NamedTuple, TypeVar, cast, get_args, get_origin

from customtkinter import (
    CTk,
    CTkButton,
    CTkCanvas,
    CTkEntry,
    CTkFont,
    CTkFrame,
    CTkImage,
    CTkLabel,
    CTkOptionMenu,
    CTkScrollableFrame,
    CTkSegmentedButton,
    CTkSwitch,
    CTkTabview,
    CTkToplevel,
    DrawEngine,
    ScalingTracker,
    ThemeManager,
    set_appearance_mode,
    set_default_color_theme,
    set_widget_scaling,
)
from PIL import Image, ImageTk

from my_game.core.logger import get_logger
from my_game.werewolf.assets import Images
from my_game.werewolf.interactions import editor_data as interaction_editor_data
from my_game.werewolf.interactions.definitions import Condition, Effect, InteractionData, Verb
from my_game.werewolf.room import rooms
from my_game.werewolf.room.editor_data import named_values, update_room_source
from my_game.werewolf.room.loaders import CharacterData, NamedPointData, PropData, RegionData, RoomData

logger = get_logger(__name__)

# Type variables for better type safety
ItemT = TypeVar("ItemT", PropData, CharacterData, RegionData, NamedPointData)
TYPES = PropData | CharacterData | RegionData | NamedPointData

parser = argparse.ArgumentParser()
parser.add_argument("scale", type=int, nargs="?", help="Scale the room viewport by this value", default=2)
args = parser.parse_args()

DEFAULT_THEME = "dark-blue"
NATIVE_WINDOW_RESOLUTION = (480, 208)
MULTIPLIER = args.scale
SCALED_WINDOW_RESOLUTION = (NATIVE_WINDOW_RESOLUTION[0] * MULTIPLIER, NATIVE_WINDOW_RESOLUTION[1] * MULTIPLIER)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOMS_FILE = PROJECT_ROOT / "src/my_game/werewolf/room/rooms.py"


def run() -> None:
    set_appearance_mode("Dark")
    set_default_color_theme(DEFAULT_THEME)
    DrawEngine.preferred_drawing_method = "polygon_shapes"

    new_instance: bool = True
    while new_instance:
        app = RoomEditor()
        app.mainloop()
        new_instance = app.new_instance_requested


def _ruff_command(rooms_file: Path, args: tuple[str, ...]) -> list[str] | None:
    """Build a Ruff command using the project runner when available."""
    if shutil.which("uv") is not None:
        return ["uv", "run", "ruff", *args, str(rooms_file.relative_to(PROJECT_ROOT))]
    if (ruff := shutil.which("ruff")) is not None:
        return [ruff, *args, str(rooms_file)]
    return None


def _run_ruff_fix(rooms_file: Path) -> None:
    """Apply Ruff's safe fixes and formatting to rooms.py after saving."""
    for args in (("check", "--fix"), ("format",)):
        command = _ruff_command(rooms_file, args)
        if command is None:
            logger.warning("✗ Ruff not found; skipped ruff %s", " ".join(args))
            return

        try:
            result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        except (OSError, subprocess.SubprocessError) as error:
            logger.warning("✗ Could not run ruff %s: %s", " ".join(args), error)
            return

        if result.returncode != 0:
            output = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            logger.warning("✗ Ruff %s failed on %s: %s", " ".join(args), rooms_file, output)
            return

    logger.warning("✓ Ruff fixed and formatted %s", rooms_file)


@dataclass
class AppState:
    room_data: dict[str, RoomData]
    current_room_name: str
    selected: TYPES | None = None
    selected_index: int | None = None

    @property
    def current_room(self) -> RoomData:
        return self.room_data[self.current_room_name]


class LeftSidebar(CTkFrame):
    LOGO_SIZE = (100, 100)
    LOGO_PATH = Images.STUDIO_LIGHT.get_path()

    def __init__(
        self,
        master: CTk,
        width: int,
        on_theme_change: Callable[[str], None] | None = None,
        on_scaling_change: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, width=width, corner_radius=0)

        self.on_theme_change = on_theme_change or (lambda x: None)
        self.on_scaling_change = on_scaling_change or (lambda x: None)

        logo_image = CTkImage(Image.open(self.LOGO_PATH).convert("RGBA"), size=self.LOGO_SIZE)
        self.logo = CTkLabel(self, image=logo_image, text="")
        self.logo_label = CTkLabel(self, text="Room Editor", font=CTkFont(size=20, weight="bold"))
        # Theme selection for the UI
        self.theme_label = CTkLabel(self, text="Theme:", anchor="w")
        self.theme_optionmenu = CTkOptionMenu(self, values=ThemeManager._built_in_themes, command=self.on_theme_change)
        self.theme_optionmenu.set(ThemeManager._currently_loaded_theme or DEFAULT_THEME)
        # Scaling options for the UI
        self.scaling_label = CTkLabel(self, text="UI Scaling:", anchor="w")
        self.scaling_optionmenu = CTkOptionMenu(
            self, values=["50%", "100%", "150%", "200%"], command=self.on_scaling_change
        )
        widget_scaling = round(ScalingTracker.widget_scaling * 100)
        self.scaling_optionmenu.set(f"{widget_scaling}%")
        # Skip confirmation dialog toggle
        self.skip_confirmation_label = CTkLabel(self, text="Skip Confirmation:", anchor="w")
        self.skip_confirmation_switch = CTkSwitch(self, text="")

        self.logo.pack(side="top", fill="x", padx=5, pady=5)
        self.logo_label.pack(side="top", fill="x", padx=0, pady=0)
        self.theme_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.theme_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))
        self.scaling_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.scaling_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))
        self.skip_confirmation_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.skip_confirmation_switch.pack(side="top", fill="x", padx=20, pady=(0, 10))


class RoomViewport(CTkFrame):
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        master: RoomEditor,
        app_state: AppState,
        on_room_change: Callable[[str], None],
        on_save: Callable[[], None],
        on_selection_change: Callable[[], None],
        on_add_room: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.app_state = app_state
        self.on_selection_change = on_selection_change

        self.photo_images: list[ImageTk.PhotoImage] = []  # Keep references to prevent garbage collection
        self.drag_start: tuple[int, int] | None = None
        self.drag_start_image_position: tuple[int, int] | None = None

        # Region creation state
        self.creating_region = False
        self.region_vertices: list[tuple[int, int]] = []
        self.dragging_vertex: tuple[int, int] | None = None
        self.selected_region_index: int | None = None

        ### Room Viewport ###
        self.room_top_menu = CTkFrame(self)
        self.room_select_label = CTkLabel(self.room_top_menu, text="Room select:", anchor="w")
        self.room_select_menu = CTkOptionMenu(
            self.room_top_menu, dynamic_resizing=False, values=list(self.app_state.room_data), command=on_room_change
        )
        self.add_room_button = CTkButton(
            self.room_top_menu, text="Add Room", command=on_add_room or (lambda: None), width=40
        )
        self.save_button = CTkButton(
            self.room_top_menu, text="SAVE ALL CHANGES", command=on_save, fg_color="darkred", hover_color="red"
        )

        self.room_top_menu.pack(side=TOP, fill="x")
        self.room_select_label.pack(side=LEFT, padx=(20, 0), pady=(10, 10))
        self.room_select_menu.pack(side=LEFT, padx=20, pady=(10, 10))
        self.add_room_button.pack(side=LEFT, padx=(0, 10), pady=(10, 10))
        self.save_button.pack(side=LEFT, padx=20, pady=(10, 10))

        self.room_canvas = CTkCanvas(
            self,
            width=SCALED_WINDOW_RESOLUTION[0],
            height=SCALED_WINDOW_RESOLUTION[1],
            bd=0,
            highlightthickness=0,
        )
        self.room_canvas.pack(side=LEFT, anchor="nw")
        self.room_canvas.bind("<Button-1>", self._on_canvas_press)
        self.room_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.room_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.room_canvas.bind("<Up>", self._on_arrow_key)
        self.room_canvas.bind("<Down>", self._on_arrow_key)
        self.room_canvas.bind("<Left>", self._on_arrow_key)
        self.room_canvas.bind("<Right>", self._on_arrow_key)
        self.room_canvas.focus_set()

        self.draw_room(app_state.current_room)

    def get_current_room_name(self) -> str:
        return self.room_select_menu.get()

    def _update_selected_position(self, new_position: tuple[int, int]) -> None:
        """Update the position of the currently selected prop/character/point and persist changes."""
        old_item = self.app_state.selected
        if old_item is None or isinstance(old_item, RegionData):
            return

        current_room = self.app_state.current_room

        updated_item = replace(old_item, position=new_position)
        self.app_state.selected = updated_item

        if isinstance(old_item, PropData):
            new_props = tuple(p if p != old_item else cast(PropData, updated_item) for p in current_room.props)
            updated_room = replace(current_room, props=new_props)
        elif isinstance(old_item, CharacterData):
            new_characters = tuple(
                c if c != old_item else cast(CharacterData, updated_item) for c in current_room.characters
            )
            updated_room = replace(current_room, characters=new_characters)
        elif isinstance(old_item, NamedPointData):
            new_points = tuple(
                pt if pt != old_item else cast(NamedPointData, updated_item) for pt in current_room.points
            )
            updated_room = replace(current_room, points=new_points)
        else:
            logger.error("Unsupported item type for updating position: %s", type(old_item))
            return

        room_name = self.room_select_menu.get()
        self.app_state.room_data[room_name] = updated_room
        self.draw_room(updated_room)
        # Only refresh form if not currently dragging to avoid lag
        if self.drag_start is None:
            self.on_selection_change()

    def _on_canvas_press(self, event: Event) -> None:
        """Handle canvas mouse press - add vertex if creating region, otherwise record drag start."""
        if self.creating_region:
            # Add vertex to region
            canvas_x = event.x
            canvas_y = event.y
            # Convert from canvas coordinates to room coordinates
            room_x = round(canvas_x / MULTIPLIER)
            room_y = round(canvas_y / MULTIPLIER)
            self.region_vertices.append((room_x, room_y))
            self.draw_room(self.app_state.current_room)
            self._draw_region_creation()
            return

        if self.app_state.selected is None:
            return

        self.drag_start = (event.x, event.y)

        selected = self.app_state.selected
        if isinstance(selected, (PropData, CharacterData, NamedPointData)):
            self.drag_start_image_position = selected.position

    def _on_canvas_drag(self, event: Event) -> None:
        """Handle canvas mouse drag - update prop position in real-time."""
        if self.drag_start is None or self.drag_start_image_position is None:
            return

        event_x: int = event.x
        event_y: int = event.y

        delta_x = round((event_x - self.drag_start[0]) / MULTIPLIER)
        delta_y = round((event_y - self.drag_start[1]) / MULTIPLIER)

        new_x = self.drag_start_image_position[0] + delta_x
        new_y = self.drag_start_image_position[1] + delta_y

        self._update_selected_position((new_x, new_y))

    def _on_canvas_release(self, event: Event) -> None:
        """Handle canvas mouse release - finalize drag."""
        self.drag_start = None
        self.drag_start_image_position = None
        # Refresh form after drag is complete
        self.on_selection_change()

    def _on_arrow_key(self, event: Event) -> None:
        """Handle arrow key press - nudge selected prop by 1 pixel."""
        old_item = self.app_state.selected
        if old_item is None or isinstance(old_item, RegionData):
            return

        keysym: str = event.keysym
        delta_x = 0
        delta_y = 0

        if keysym == "Up":
            delta_y = -1
        elif keysym == "Down":
            delta_y = 1
        elif keysym == "Left":
            delta_x = -1
        elif keysym == "Right":
            delta_x = 1

        new_position = (old_item.position[0] + delta_x, old_item.position[1] + delta_y)
        self._update_selected_position(new_position)

    def get_prop_image(self, prop: PropData | CharacterData) -> ImageTk.PhotoImage:
        image = Image.open(prop.image.get_path())
        size = prop.size or (int(image.size[0] * prop.scale), int(image.size[1] * prop.scale))
        scaled_size = (size[0] * MULTIPLIER, size[1] * MULTIPLIER)
        return ImageTk.PhotoImage(image.resize(scaled_size))

    def draw_room(self, room: RoomData) -> None:
        """Draw room content in depth order using scaled canvas coordinates."""
        self.room_canvas.delete("all")
        self.photo_images.clear()

        objects = sorted(room.props + room.characters, key=lambda item: item.depth, reverse=True)

        for obj in objects:
            image = self.get_prop_image(obj)
            self.photo_images.append(image)
            corrected_position = (obj.position[0] * MULTIPLIER, obj.position[1] * MULTIPLIER)
            self.room_canvas.create_image(
                *corrected_position,
                image=image,
                anchor=NW,
                # tags=("content", f"props:{index}"),
            )

        for region in room.regions:
            polygon = [(x * MULTIPLIER, y * MULTIPLIER) for x, y in region.polygon]
            self.room_canvas.create_polygon(
                *sum(polygon, ()),
                outline="#8cff66",
                fill="",
                width=int(1 * MULTIPLIER),
            )

        for point in room.points:
            corrected_position = (point.position[0] * MULTIPLIER, point.position[1] * MULTIPLIER)
            radius = int(5 * MULTIPLIER)
            self.room_canvas.create_oval(
                corrected_position[0] - radius,
                corrected_position[1] - radius,
                corrected_position[0] + radius,
                corrected_position[1] + radius,
                fill="#ff55dd",
                outline="",
            )

        if isinstance(self.app_state.selected, (PropData, CharacterData)):
            selected_item = self.app_state.selected
            image = self.get_prop_image(selected_item)
            corrected_position = (selected_item.position[0] * MULTIPLIER, selected_item.position[1] * MULTIPLIER)
            self.room_canvas.create_rectangle(
                *corrected_position,
                (corrected_position[0] + image.width()),
                (corrected_position[1] + image.height()),
                outline="#ffcc00",
                width=int(1 * MULTIPLIER),
            )
        elif isinstance(self.app_state.selected, NamedPointData):
            selected_point = self.app_state.selected
            corrected_position = (selected_point.position[0] * MULTIPLIER, selected_point.position[1] * MULTIPLIER)
            radius = int(5 * MULTIPLIER)
            self.room_canvas.create_oval(
                corrected_position[0] - radius,
                corrected_position[1] - radius,
                corrected_position[0] + radius,
                corrected_position[1] + radius,
                fill="",
                outline="#ffcc00",
                width=int(2 * MULTIPLIER),
            )

    def start_region_creation(self) -> None:
        """Start creating a new region by clicking vertices."""
        self.creating_region = True
        self.region_vertices = []

    def finish_region_creation(self) -> None:
        """Finish creating the region and add it to the room."""
        min_vertices = 3
        if len(self.region_vertices) < min_vertices:
            logger.warning("Region must have at least 3 vertices")
            return

        # Convert vertices list to tuple
        polygon = tuple(self.region_vertices)

        # Create a new region
        new_region = RegionData(
            id=f"region_{len(self.app_state.current_room.regions) + 1}",
            description="",
            polygon=polygon,
        )

        # Add to current room
        current_room = self.app_state.current_room
        updated_room = replace(current_room, regions=(*current_room.regions, new_region))
        self.app_state.room_data[self.app_state.current_room_name] = updated_room

        # Reset state
        self.creating_region = False
        self.region_vertices = []

        # Redraw and refresh UI
        self.draw_room(updated_room)
        if isinstance(self.master, RoomEditor):
            self.master.main_tabview.refresh_tree(updated_room)

    def _draw_region_creation(self) -> None:
        """Draw the region being created with vertices and preview lines."""
        if not self.creating_region or not self.region_vertices:
            return

        min_vertices_for_line = 2

        # Draw lines connecting vertices
        for i in range(len(self.region_vertices) - 1):
            x1, y1 = self.region_vertices[i]
            x2, y2 = self.region_vertices[i + 1]
            self.room_canvas.create_line(
                x1 * MULTIPLIER,
                y1 * MULTIPLIER,
                x2 * MULTIPLIER,
                y2 * MULTIPLIER,
                fill="#ffcc00",
                width=int(2 * MULTIPLIER),
            )

        # Draw vertices as circles
        for x, y in self.region_vertices:
            canvas_x = x * MULTIPLIER
            canvas_y = y * MULTIPLIER
            radius = int(5 * MULTIPLIER)
            self.room_canvas.create_oval(
                canvas_x - radius,
                canvas_y - radius,
                canvas_x + radius,
                canvas_y + radius,
                fill="#ffcc00",
                outline="white",
                width=int(2 * MULTIPLIER),
            )

        # Draw line back to first vertex if at least 2 vertices
        if len(self.region_vertices) >= min_vertices_for_line:
            x1, y1 = self.region_vertices[-1]
            x2, y2 = self.region_vertices[0]
            self.room_canvas.create_line(
                x1 * MULTIPLIER,
                y1 * MULTIPLIER,
                x2 * MULTIPLIER,
                y2 * MULTIPLIER,
                fill="#ffcc00",
                width=int(2 * MULTIPLIER),
                dash=(4, 4),  # Dashed line
            )


class TabData(NamedTuple):
    """Container for tab UI components and data accessor."""

    scrollable_frame: CTkScrollableFrame
    selector_button: CTkSegmentedButton
    get_items: Callable[[RoomData], Sequence]
    add_button: CTkButton | None = None
    delete_button: CTkButton | None = None


class MainTabview(CTkTabview):
    BUTTON_HEIGHT = 30

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        master: RoomEditor,
        app_state: AppState,
        on_select: Callable[[str, Callable[[RoomData], Sequence]], None],
        on_tab_change: Callable[[], None],
        on_add_item: Callable[[str], None],
        on_delete_item: Callable[[str], None],
        on_draw_region: Callable[[], None] | None = None,
        on_finish_region: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, command=on_tab_change)
        self.app_state = app_state
        self.on_add_item = on_add_item
        self.on_delete_item = on_delete_item
        self.on_draw_region = on_draw_region
        self.on_finish_region = on_finish_region

        self.tabs: dict[str, TabData] = {}

        self._add_tab("Props", on_select, lambda room_data: room_data.props)
        self._add_tab("Characters", on_select, lambda room_data: room_data.characters)
        self._add_tab("Regions", on_select, lambda room_data: room_data.regions, is_regions_tab=True)
        self._add_tab("Points", on_select, lambda room_data: room_data.points)

        self.refresh_tree(self.app_state.current_room)

    def _add_tab(
        self,
        label: str,
        on_select: Callable[[str, Callable[[RoomData], Sequence]], None],
        get_items: Callable[[RoomData], Sequence],
        *,
        is_regions_tab: bool = False,
    ) -> None:
        """Add a tab with a scrollable frame, segmented button selector, add and delete buttons."""
        frame = self.add(label)

        # Create a button frame for action buttons
        button_frame = CTkFrame(frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        # Region-specific buttons
        if is_regions_tab:
            add_button = CTkButton(
                button_frame,
                text="Draw Region",
                command=self.on_draw_region,
                height=28,
            )
            add_button.pack(side="left", fill="x", expand=True, padx=(2, 0))

            finish_button = CTkButton(
                button_frame,
                text="Finish",
                command=self.on_finish_region,
                height=28,
            )
            finish_button.pack(side="left", fill="x", expand=True, padx=(2, 0))
        else:
            # Add button
            add_button = CTkButton(
                button_frame,
                text=f"Add {label.removesuffix('s')}",
                command=lambda tab_name=label: self.on_add_item(tab_name),  # type: ignore[misc]
                height=28,
            )
            add_button.pack(side="left", fill="x", expand=True, padx=(0, 2))

        # Delete button
        delete_button = CTkButton(
            button_frame,
            text=f"Delete {label.removesuffix('s')}",
            command=lambda tab_name=label: self.on_delete_item(tab_name),  # type: ignore[misc]
            height=28,
        )
        delete_button.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Scrollable frame with selector
        scrollable = CTkScrollableFrame(frame)

        # Create a specialized callback using the generic handler with this tab's get_items
        callback = lambda item_name: on_select(item_name, get_items)

        selector = CTkSegmentedButton(
            scrollable,
            orientation="vertical",
            dynamic_resizing=False,
            command=callback,
        )

        scrollable.pack(fill="both", expand=True)
        selector.pack(fill="x")

        self.tabs[label] = TabData(scrollable, selector, get_items, add_button, delete_button)

    def refresh_tree(self, room: RoomData) -> None:
        """Update all tab titles and selectors with current room data."""
        for tab_data in self.tabs.values():
            ids = [item.id for item in tab_data.get_items(room)]

            cmd = tab_data.selector_button._command
            for child in tab_data.scrollable_frame.winfo_children():
                child.destroy()

            selector = CTkSegmentedButton(
                tab_data.scrollable_frame,
                orientation="vertical",
                values=ids,
                command=cmd,
            )
            selector.pack(fill="x")

    def clear_selection(self) -> None:
        """Clear selection from all tabs."""
        for tab_data in self.tabs.values():
            tab_data.selector_button.set("")


DefinitionKind = Literal["condition", "effect"]


def _definition_types(kind: DefinitionKind) -> tuple[type[Condition | Effect], ...]:
    """Return the selectable definition classes for a kind."""
    if kind == "condition":
        return interaction_editor_data.CONDITION_TYPES
    return interaction_editor_data.EFFECT_TYPES


class DefinitionWidget(CTkFrame):
    """Edit one condition or effect definition using dataclass-driven fields."""

    def __init__(
        self,
        master: CTkFrame,
        kind: DefinitionKind,
        value: Condition | Effect | dict[str, Any] | None = None,
        room_ids: Sequence[str] = (),
    ) -> None:
        super().__init__(master)
        self.kind: DefinitionKind = kind
        self.room_ids = tuple(room_ids)
        self.field_widgets: dict[str, object] = {}
        self.type_menu: CTkOptionMenu
        self._rebuild(value)

    def _rebuild(self, value: Condition | Effect | dict[str, Any] | None) -> None:
        """Rebuild widgets for the currently selected definition type."""
        for child in self.winfo_children():
            cast(Any, child).destroy()
        self.field_widgets.clear()

        types = _definition_types(self.kind)
        names = tuple(definition_type.__name__ for definition_type in types)
        if isinstance(value, dict):
            selected_type = str(value.get("type", names[0]))
        elif value is not None:
            selected_type = type(value).__name__
        else:
            selected_type = names[0]
        if selected_type not in names:
            selected_type = names[0]

        self.type_menu = CTkOptionMenu(self, values=list(names), command=self._on_type_change)
        self.type_menu.set(selected_type)
        self.type_menu.pack(side="left")

        self.fields_frame = CTkFrame(self)
        self.fields_frame.pack(side="left", fill="x", expand=True)

        definition_type = interaction_editor_data.DEFINITION_REGISTRY[selected_type]
        if isinstance(value, dict):
            values = value
        elif value is not None:
            values = interaction_editor_data.definition_to_dict(value)
        else:
            values = {}
        for field_info in fields(cast(Any, definition_type)):
            field_row = CTkFrame(self.fields_frame)
            field_row.pack(fill="x", pady=1)
            CTkLabel(field_row, text=field_info.name, width=80, anchor="w").pack(side="left")
            widget = self._make_field_widget(field_row, field_info.name, field_info.type, values.get(field_info.name))
            cast(Any, widget).pack(side="left", fill="x", expand=True)
            self.field_widgets[field_info.name] = widget

    def _on_type_change(self, value: str) -> None:
        """Rebuild fields for the definition type chosen in the dropdown."""
        self._rebuild({"type": value})

    def _make_field_widget(self, master: CTkFrame, field_name: str, field_type: Any, current: Any) -> Misc:
        """Create a widget appropriate for one definition field."""
        if field_type is bool:
            widget = CTkSwitch(master, text="")
            widget.select() if current else widget.deselect()
            return widget

        if field_name == "room_id" and self.room_ids:
            room_widget = CTkOptionMenu(master, values=list(self.room_ids))
            room_widget.set(str(current) if current in self.room_ids else self.room_ids[0])
            return room_widget

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            enum_widget = CTkOptionMenu(master, values=[member.name for member in field_type])
            enum_widget.set(str(current) if current is not None else next(iter(field_type)).name)
            return enum_widget

        if field_type is Condition or (isinstance(field_type, type) and issubclass(field_type, Condition)):
            return DefinitionWidget(master, "condition", current, self.room_ids)

        origin = get_origin(field_type)
        if origin is tuple:
            item_type = next(iter(get_args(field_type)), None)
            if item_type is Condition or (isinstance(item_type, type) and issubclass(item_type, Condition)):
                current_definitions = current if isinstance(current, list) else []
                return DefinitionListWidget(master, "condition", current_definitions, self.room_ids)

        entry = CTkEntry(master)
        if current is not None:
            entry.insert(0, str(current))
        return entry

    def get_value(self) -> dict[str, Any]:
        """Return the widget-friendly dictionary represented by this row."""
        result: dict[str, Any] = {"type": self.type_menu.get()}
        for name, widget in self.field_widgets.items():
            if isinstance(widget, CTkSwitch):
                result[name] = bool(widget.get())
            elif isinstance(widget, (CTkOptionMenu, CTkEntry)):
                result[name] = widget.get()
            elif isinstance(widget, (DefinitionWidget, DefinitionListWidget)):
                result[name] = widget.get_value()
        return result


class DefinitionListWidget(CTkFrame):
    """Edit an ordered list of conditions or effects."""

    def __init__(
        self,
        master: CTkFrame | CTkScrollableFrame,
        kind: DefinitionKind,
        values: Sequence[dict[str, Any]] = (),
        room_ids: Sequence[str] = (),
    ) -> None:
        super().__init__(master)
        self.kind: DefinitionKind = kind
        self.room_ids = tuple(room_ids)
        self.rows: list[DefinitionWidget] = []

        self.rows_frame = CTkFrame(self)
        self.rows_frame.pack(fill="x")
        for value in values:
            self._add_row(value)

        self.add_button = CTkButton(
            self,
            text=f"Add {'condition' if kind == 'condition' else 'effect'}",
            command=self._add_row,
        )
        self.add_button.pack(fill="x", pady=(3, 0))

    def _add_row(self, value: dict[str, Any] | None = None) -> None:
        """Append an editable definition row."""
        row_frame = CTkFrame(self.rows_frame)
        row_frame.pack(fill="x", pady=2)

        definition_widget = DefinitionWidget(row_frame, self.kind, value, self.room_ids)
        definition_widget.pack(side="left", fill="x", expand=True)

        remove_button = CTkButton(
            row_frame,
            text="X",
            width=28,
            command=lambda: self._remove_row(row_frame, definition_widget),  # type: ignore[misc]
        )
        remove_button.pack(side="right")
        self.rows.append(definition_widget)

    def _remove_row(self, row_frame: CTkFrame, definition_widget: DefinitionWidget) -> None:
        """Remove a definition row."""
        self.rows.remove(definition_widget)
        row_frame.destroy()

    def get_value(self) -> list[dict[str, Any]]:
        """Return all rows as widget-friendly dictionaries."""
        return [row.get_value() for row in self.rows]


class InteractionEditorDialog(CTkToplevel):
    """Modal editor for a single interaction definition."""

    def __init__(
        self,
        master: Misc,
        interaction: InteractionData | None = None,
        room_ids: Sequence[str] = (),
    ) -> None:
        super().__init__(master)
        self.title("Edit Interaction" if interaction is not None else "Add Interaction")
        self.geometry("720x680")
        self.transient(cast(Any, master))
        self.grab_set()
        self.room_ids = tuple(room_ids)
        self.result: InteractionData | None = None

        data: dict[str, Any] = (
            interaction_editor_data.interaction_to_dict(interaction)
            if interaction is not None
            else {"verb": Verb.INTERACT.name, "priority": 0, "once": False, "conditions": [], "effects": []}
        )

        content = CTkScrollableFrame(self)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        verb_frame = CTkFrame(content)
        verb_frame.pack(fill="x", pady=3)
        CTkLabel(verb_frame, text="Verb", width=80, anchor="w").pack(side="left")
        self.verb_menu = CTkOptionMenu(verb_frame, values=[verb.name for verb in Verb])
        self.verb_menu.set(str(data["verb"]))
        self.verb_menu.pack(side="left")

        priority_frame = CTkFrame(content)
        priority_frame.pack(fill="x", pady=3)
        CTkLabel(priority_frame, text="Priority", width=80, anchor="w").pack(side="left")
        self.priority_entry = CTkEntry(priority_frame)
        self.priority_entry.insert(0, str(data["priority"]))
        self.priority_entry.pack(side="left", fill="x", expand=True)

        once_frame = CTkFrame(content)
        once_frame.pack(fill="x", pady=3)
        CTkLabel(once_frame, text="Once", width=80, anchor="w").pack(side="left")
        self.once_switch = CTkSwitch(once_frame, text="")
        self.once_switch.select() if data["once"] else self.once_switch.deselect()
        self.once_switch.pack(side="left")

        CTkLabel(content, text="Conditions (all must pass)", font=CTkFont(size=12, weight="bold")).pack(
            anchor="w", pady=(10, 2)
        )
        self.conditions_widget = DefinitionListWidget(content, "condition", data["conditions"], self.room_ids)
        self.conditions_widget.pack(fill="x")

        CTkLabel(content, text="Effects", font=CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 2))
        self.effects_widget = DefinitionListWidget(content, "effect", data["effects"], self.room_ids)
        self.effects_widget.pack(fill="x")

        buttons = CTkFrame(content)
        buttons.pack(fill="x", pady=(10, 0))
        CTkButton(buttons, text="Save", command=self._on_save).pack(side="left", padx=(0, 5))
        CTkButton(buttons, text="Cancel", command=self.destroy).pack(side="left")

    def get_value_dict(self) -> dict[str, Any]:
        """Return the dialog state as a widget-friendly dictionary."""
        return {
            "verb": self.verb_menu.get(),
            "priority": self.priority_entry.get(),
            "once": bool(self.once_switch.get()),
            "conditions": self.conditions_widget.get_value(),
            "effects": self.effects_widget.get_value(),
        }

    def _on_save(self) -> None:
        """Validate and store the edited interaction before closing."""
        try:
            self.result = interaction_editor_data.interaction_from_dict(self.get_value_dict())
        except (KeyError, TypeError, ValueError) as error:
            logger.warning("Invalid interaction definition: %s", error)
            return
        self.destroy()


class ObjectForm(CTkFrame):
    COLOR_COMPONENTS = 3
    POINT_LENGTH = 2

    def __init__(self, parent: CTk, app_state: AppState) -> None:
        super().__init__(parent)
        self.app_state = app_state

        # Title label
        self.title_label = CTkLabel(self, text="", font=CTkFont(size=14, weight="bold"))
        self.title_label.pack(anchor="w", padx=10, pady=(0, 0))

        # Scrollable frame for form fields
        self.scrollable_frame = CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Store field widgets for easy access
        self.field_widgets: dict[str, object] = {}
        # Store image button widgets separately for updating labels
        self.image_buttons: dict[str, CTkButton] = {}

        # Keep reference to prevent garbage collection
        self._thumbnail_images: list[CTkImage] = []

        self._refresh_form()

    def _is_point_type(self, field_type: object) -> bool:
        """Check if a type is a Point type (tuple[int, int])."""
        return (
            hasattr(field_type, "__origin__")
            and getattr(field_type, "__origin__", None) is tuple
            and len(getattr(field_type, "__args__", [])) == self.POINT_LENGTH
        )

    def _get_display_value(self, value: object) -> str:
        """Convert a field value to a display string."""
        # Handle NormalisedColor
        color_tuple_len = 3
        if (
            isinstance(value, (tuple, list))
            and len(value) == color_tuple_len
            and all(isinstance(x, float) for x in value)
        ):
            return f"{value[0]:.2f}, {value[1]:.2f}, {value[2]:.2f}"
        elif isinstance(value, (tuple, list)):
            if isinstance(value, tuple) and len(value) == self.POINT_LENGTH and all(isinstance(x, int) for x in value):
                # Point/position tuple like (10, 20)
                x, y = value
                return f"{x}, {y}"
            elif isinstance(value, (tuple, list)) and all(
                isinstance(item, (tuple, list)) and len(item) == self.POINT_LENGTH for item in value
            ):
                # Polygon: tuple of points like ((10, 10), (100, 10), (100, 100))
                points_str = "; ".join(f"{x}, {y}" for x, y in value)
                return points_str
            return str(value)
        elif isinstance(value, bool):
            return str(value)
        return str(value)

    def _get_parsed_value(self, field_type: object, value: str) -> object:  # noqa: PLR0911
        """Helper to get the parsed value for a given type."""
        # Check for NormalisedColor type
        if field_type is tuple and getattr(field_type, "__args__", None) == (float, float, float):
            return self._parse_normalised_color(value)

        # Check for int type
        if field_type is int or (isinstance(field_type, type) and issubclass(field_type, int)):
            return int(value)

        # Check for float type
        if field_type is float or (isinstance(field_type, type) and issubclass(field_type, float)):
            return float(value)

        # Check for bool type
        if field_type is bool or (isinstance(field_type, type) and issubclass(field_type, bool)):
            return value.lower() in ("true", "1", "yes", "on")

        # Handle generic types (tuple, Union, Optional, etc.)
        origin = getattr(field_type, "__origin__", None)

        # Handle tuple types (points and polygons)
        if origin is tuple:
            return self._parse_tuple_type(field_type, value)

        # Handle Union types (e.g., int | str)
        if origin is type(int | str):
            args = getattr(field_type, "__args__", ())
            for arg in args:
                if arg is not type(None):
                    return self._parse_input_value(arg, value)

        return value

    def _parse_normalised_color(self, value: str) -> tuple[float, float, float]:
        """Parse a NormalisedColor from a string in format 'r, g, b' with floats."""
        parts = [p.strip() for p in value.split(",")]
        if len(parts) != self.COLOR_COMPONENTS:
            msg = f"Expected {self.COLOR_COMPONENTS} color components (r, g, b), got {len(parts)}"
            raise ValueError(msg)
        try:
            r = float(parts[0])
            g = float(parts[1])
            b = float(parts[2])
            return (r, g, b)
        except ValueError as e:
            msg = f"Could not parse color values as floats: {e}"
            raise ValueError(msg) from e

    def _parse_tuple_type(self, field_type: object, value: str) -> tuple:
        """Parse a tuple type, handling both simple points and nested polygons."""
        # Check if this is a nested tuple (polygon) by looking at type args
        args = getattr(field_type, "__args__", ())

        # Check if it's tuple[tuple[int, int], ...] (polygon)
        if args and len(args) >= 1 and getattr(args[0], "__origin__", None) is tuple:
            # This is a polygon: tuple of tuples
            # Format: "10, 10; 100, 10; 100, 100"
            return self._parse_polygon_string(value)

        # Simple tuple like tuple[int, int] for a point
        parts = [p.strip() for p in value.split(",")]
        return tuple(int(p) for p in parts)

    def _parse_polygon_string(self, value: str) -> tuple:
        """Parse a polygon string in format '10, 10; 100, 10; 100, 100'."""
        point_coords = 2
        points: list[tuple] = []
        for point_raw in value.split(";"):
            point_text = point_raw.strip()
            if not point_text:
                continue
            coords = [int(c.strip()) for c in point_text.split(",")]
            if len(coords) == point_coords:
                points.append(tuple(coords))  # type: ignore[arg-type]
        return tuple(points)

    def _parse_input_value(self, field_type: object, value: str) -> object:
        """Parse string input based on the expected field type."""
        # Handle None/empty type
        if value.strip().lower() in ("none", "null", ""):
            return None
        return self._get_parsed_value(field_type, value)

    def _refresh_form(self) -> None:
        """Refresh the form with the current selected object."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.field_widgets.clear()
        self.image_buttons.clear()

        selected = self.app_state.selected
        if selected is None:
            # Show room metadata
            current_room = self.app_state.current_room
            self.title_label.configure(text=f"Room: {current_room.id}")
            self._add_field_widgets(current_room)
        else:
            # Show selected object attributes
            self.title_label.configure(text=f"{type(selected).__name__}: {selected.id}")
            self._add_field_widgets(selected)
            self._add_interactions_section(selected)

        save_button = CTkButton(
            self.scrollable_frame,
            text="Apply Changes",
            command=self._on_save_changes,
        )
        save_button.pack(fill="x", padx=5, pady=(10, 0))

    def _add_interactions_section(self, obj: TYPES) -> None:
        """Show the dedicated interaction list for the selected object."""
        section = CTkFrame(self.scrollable_frame)
        section.pack(fill="x", padx=5, pady=(10, 0))
        CTkLabel(section, text="Interactions", font=CTkFont(size=12, weight="bold")).pack(anchor="w")

        for index, interaction in enumerate(obj.interactions):
            row = CTkFrame(section)
            row.pack(fill="x", pady=2)
            CTkLabel(row, text=interaction_editor_data.interaction_label(interaction), anchor="w").pack(
                side="left", fill="x", expand=True
            )
            CTkButton(
                row,
                text="Edit",
                width=50,
                command=lambda item_index=index: self._edit_interaction(item_index),  # type: ignore[misc]
            ).pack(side="right", padx=(2, 0))
            CTkButton(
                row,
                text="Delete",
                width=50,
                command=lambda item_index=index: self._delete_interaction(item_index),  # type: ignore[misc]
            ).pack(side="right")

        CTkButton(section, text="Add Interaction", command=self._add_interaction).pack(fill="x", pady=(5, 0))

    def _room_ids(self) -> tuple[str, ...]:
        """Return stable room IDs available to `ChangeRoom` effects."""
        ids = (room.id or name for name, room in self.app_state.room_data.items())
        return tuple(sorted(dict.fromkeys(ids)))

    def _add_interaction(self) -> None:
        """Open the interaction editor and append a new definition."""
        selected = self.app_state.selected
        if selected is None:
            return
        dialog = InteractionEditorDialog(self.master, None, self._room_ids())
        dialog.wait_window()
        if dialog.result is None:
            return
        self._persist_interactions((*selected.interactions, dialog.result))

    def _edit_interaction(self, index: int) -> None:
        """Open the interaction editor for an existing definition."""
        selected = self.app_state.selected
        if selected is None or index >= len(selected.interactions):
            return
        dialog = InteractionEditorDialog(self.master, selected.interactions[index], self._room_ids())
        dialog.wait_window()
        if dialog.result is None:
            return
        interactions = tuple(
            dialog.result if item_index == index else interaction
            for item_index, interaction in enumerate(selected.interactions)
        )
        self._persist_interactions(interactions)

    def _delete_interaction(self, index: int) -> None:
        """Delete an interaction from the selected object."""
        selected = self.app_state.selected
        if selected is None or index >= len(selected.interactions):
            return
        interactions = tuple(
            interaction for item_index, interaction in enumerate(selected.interactions) if item_index != index
        )
        self._persist_interactions(interactions)

    def _persist_interactions(self, interactions: tuple[InteractionData, ...]) -> None:
        """Write interaction changes back into the selected object and room."""
        selected = self.app_state.selected
        if selected is None:
            return

        updated_object = cast(TYPES, replace(selected, interactions=interactions))
        current_room = self.app_state.current_room
        updated_room = self._update_room_with_object(selected, updated_object, current_room)
        if updated_room is None:
            return

        room_name = self.app_state.current_room_name
        self.app_state.room_data[room_name] = updated_room
        self.app_state.selected = updated_object
        self._redraw_viewport()
        if isinstance(self.master, RoomEditor):
            self.master.main_tabview.refresh_tree(updated_room)
        self._refresh_form()

    def _add_field_widgets(self, obj: RoomData | TYPES) -> None:
        """Add input widgets for all fields of the given object."""
        from dataclasses import fields

        if not hasattr(obj, "__dataclass_fields__"):
            return

        all_fields = list(fields(obj))

        # Skip collection fields when editing a room (props, characters, regions, etc.)
        # These are managed through the add/delete UI buttons. Interaction rules need a
        # dedicated editor, so they are read-only in the generic object form for now.
        non_editable_fields = {"interactions"}
        if isinstance(obj, RoomData):
            non_editable_fields |= {"props", "characters", "regions", "points", "walkable_areas"}
        force_image_if_none = {"image", "walk_image", "normal_image", "normal_walk_image"}

        # Create two-column layout
        columns_frame = CTkFrame(self.scrollable_frame)
        columns_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create left and right column frames
        left_column = CTkFrame(columns_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_column = CTkFrame(columns_frame)
        right_column.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Distribute fields between columns
        column_index = 0
        for field_info in all_fields:
            field_name = field_info.name

            # Skip non-editable fields
            if field_name in non_editable_fields:
                continue

            field_value = getattr(obj, field_name)

            # Choose column based on index (even -> left, odd -> right)
            column = left_column if column_index % 2 == 0 else right_column
            column_index += 1

            # Create a horizontal frame for label + widget
            field_frame = CTkFrame(column)
            field_frame.pack(fill="x", padx=0, pady=3)

            # Create label (left side)
            label = CTkLabel(
                field_frame,
                text=field_name,
                font=CTkFont(size=11),
                text_color="gray70",
                width=80,
                anchor="w",
            )
            label.pack(side="left", padx=(0, 5))

            # Create appropriate input widget (right side)
            widget: CTkSwitch | CTkEntry | CTkButton

            if isinstance(field_value, bool):
                # Boolean: use switch
                widget = CTkSwitch(
                    field_frame,
                    text="",
                    onvalue=True,
                    offvalue=False,
                )
                widget.select() if field_value else widget.deselect()
                self.field_widgets[field_name] = widget

            elif isinstance(field_value, Images) or (field_value is None and field_name in force_image_if_none):
                # Images enum: use button with picker
                display_text = getattr(field_value, "name", "Select Image")
                widget = CTkButton(
                    field_frame,
                    text=display_text,
                    command=lambda fn=field_name: self._show_image_picker(fn),  # type: ignore[misc]
                )
                self.field_widgets[field_name] = field_value
                self.image_buttons[field_name] = widget

            else:
                # Integer, Point, Polygon, or String: use entry
                widget = CTkEntry(field_frame)
                display_value = self._get_display_value(field_value)
                widget.insert(0, display_value)
                self.field_widgets[field_name] = widget

            widget.pack(side="right", fill="x", expand=True)

    def _update_room_with_object(
        self, selected: object, updated_object: object, current_room: RoomData
    ) -> RoomData | None:
        """Update room data with the modified object."""
        from typing import cast as typing_cast

        if isinstance(selected, PropData):
            new_props = tuple(p if p != selected else typing_cast(PropData, updated_object) for p in current_room.props)
            return replace(current_room, props=new_props)
        elif isinstance(selected, CharacterData):
            new_characters = tuple(
                c if c != selected else typing_cast(CharacterData, updated_object) for c in current_room.characters
            )
            return replace(current_room, characters=new_characters)
        elif isinstance(selected, NamedPointData):
            new_points = tuple(
                pt if pt != selected else typing_cast(NamedPointData, updated_object) for pt in current_room.points
            )
            return replace(current_room, points=new_points)
        elif isinstance(selected, RegionData):
            new_regions = tuple(
                r if r != selected else typing_cast(RegionData, updated_object) for r in current_room.regions
            )
            return replace(current_room, regions=new_regions)
        else:
            logger.error("Unsupported object type for update: %s", type(selected))
            return None

    def _show_image_picker(self, field_name: str) -> None:
        """Show a popup dialog to select an image from the Images enum with thumbnails."""
        # Get all Images enum values
        image_options = sorted([img for img in Images], key=lambda x: x.name)

        # Create a popup dialog with image preview
        popup = CTkToplevel(self.master)
        popup.title("Select Image")
        popup.geometry("2880x1800")

        # Create a scrollable frame for image options
        scroll_frame = CTkScrollableFrame(popup)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        selected_image: list[Images | None] = [None]
        thumbnail_size = (120, 120)
        columns = 10

        def select_image(img: Images) -> None:
            """Handle image selection."""
            selected_image[0] = img
            popup.destroy()

        # Create a grid of images (5 columns)
        for idx, img in enumerate(image_options):
            # Calculate row and column position
            row = idx // columns
            col = idx % columns

            # Create a frame for this image
            option_frame = CTkFrame(scroll_frame)
            option_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Try to load and display thumbnail
            try:
                # Load image directly from file path using PIL
                image_path = img.get_path()
                image_pil = Image.open(image_path)
                # Resize to thumbnail size (maintains aspect ratio)
                image_pil.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                # Convert to CTkImage for display
                ctk_image = CTkImage(light_image=image_pil, size=thumbnail_size)

                # Create a button with the thumbnail and name
                img_button = CTkButton(
                    option_frame,
                    text=img.name,
                    image=ctk_image,
                    compound="top",
                    command=lambda img_ref=img: select_image(img_ref),  # type: ignore[misc]
                    height=160,
                    width=140,
                )
                self._thumbnail_images.append(ctk_image)

                img_button.pack(fill="both", expand=True)
            except (OSError, ValueError, TypeError) as e:
                # Fallback to text button if image loading fails
                logger.warning("Failed to load thumbnail for %s: %s", img.name, e)
                btn = CTkButton(
                    option_frame,
                    text=img.name,
                    command=lambda img_ref=img: select_image(img_ref),  # type: ignore[misc]
                    height=160,
                    width=140,
                )
                btn.pack(fill="both", expand=True)

        # Configure grid columns to be equal width
        for col in range(columns):
            scroll_frame.grid_columnconfigure(col, weight=1)

        # Wait for the popup to close
        popup.wait_window()

        self._thumbnail_images = []

        # Update the field if an image was selected
        if selected_image[0] is not None:
            # Store the new image value
            self.field_widgets[field_name] = selected_image[0]  # type: ignore[index]
            # Update the button label to show the new selection
            if field_name in self.image_buttons:
                self.image_buttons[field_name].configure(text=selected_image[0].name)

    def _get_widget_value(self, widget: object, field_type: object) -> object:
        """Extract the value from a widget based on its type."""
        if isinstance(widget, CTkSwitch):
            return widget.get()
        elif isinstance(widget, Images):
            return widget
        elif isinstance(widget, CTkEntry):
            input_text = widget.get()
            return self._parse_input_value(field_type, input_text)
        return None

    def _redraw_viewport(self) -> None:
        """Redraw the room viewport to reflect changes."""
        parent = self.master
        if isinstance(parent, RoomEditor):
            parent.room_viewport.draw_room(self.app_state.current_room)

    def _on_save_changes(self) -> None:
        """Save changes from form back to the selected object or current room."""
        selected = self.app_state.selected

        # If nothing is selected, try to save room metadata
        if selected is None:
            self._save_room_changes()
        else:
            self._save_object_changes(selected)

    def _save_room_changes(self) -> None:
        """Save changes to the current room metadata."""
        current_room = self.app_state.current_room

        changes = self._collect_changes(current_room)
        if not changes:
            return

        # Update the room
        updated_room = replace(current_room, **changes)  # type: ignore[arg-type]
        room_name = self.app_state.current_room_name
        self.app_state.room_data[room_name] = updated_room
        self._redraw_viewport()
        self._refresh_form()

    def _save_object_changes(self, selected: TYPES) -> None:
        """Save changes to a selected object (prop, character, etc.)."""
        from dataclasses import replace

        changes = self._collect_changes(selected)
        if not changes:
            return

        # Update the selected object - cast to maintain type safety
        updated_object: TYPES
        if isinstance(selected, PropData):
            updated_object = cast(PropData, replace(selected, **changes))
        elif isinstance(selected, CharacterData):
            updated_object = cast(CharacterData, replace(selected, **changes))
        elif isinstance(selected, RegionData):
            updated_object = cast(RegionData, replace(selected, **changes))
        elif isinstance(selected, NamedPointData):
            updated_object = cast(NamedPointData, replace(selected, **changes))
        else:
            return

        self.app_state.selected = updated_object

        # Update the room data
        current_room = self.app_state.current_room
        updated_room = self._update_room_with_object(selected, updated_object, current_room)
        if updated_room is None:
            return

        # Persist changes
        room_name = self.app_state.current_room_name
        self.app_state.room_data[room_name] = updated_room
        self.app_state.selected = updated_object

        # Redraw the viewport to reflect changes
        self._redraw_viewport()
        if isinstance(self.master, RoomEditor):
            self.master.main_tabview.refresh_tree(current_room)

    def _collect_changes(self, obj: RoomData | TYPES) -> dict[str, Any]:
        """Collect changed fields from the form for the given object."""
        from dataclasses import fields as dataclass_fields

        changes: dict[str, Any] = {}
        for field_info in dataclass_fields(obj):
            field_name = field_info.name
            if field_name not in self.field_widgets:
                continue

            widget = self.field_widgets[field_name]
            field_type = field_info.type

            try:
                new_value = self._get_widget_value(widget, field_type)
                if new_value is None:
                    continue

                old_value = getattr(obj, field_name)
                if new_value != old_value:
                    changes[field_name] = new_value
            except (ValueError, TypeError) as e:
                logger.error("Error parsing field %s: %s", field_name, e)

        return changes


def maximize_window(app: CTk):
    try:
        # Windows & macOS
        app.state("zoomed")
    except TclError:
        # Linux (X11 / Wayland)
        app.attributes("-zoomed", True)  # noqa: FBT003


class RoomEditor(CTk):
    SPACING = 20
    DEFAULT_SCALING = "100%" if args.scale <= 2 else "200%"  # noqa: PLR2004

    LEFT_SIDEBAR_WIDTH = 140
    RIGHT_SIDEBAR_WIDTH = 140

    def __init__(self) -> None:
        super().__init__()

        # Set window size and scaling
        # default_width = int(self.LEFT_SIDEBAR_WIDTH + SCALED_WINDOW_RESOLUTION[0] + self.RIGHT_SIDEBAR_WIDTH + 300)
        # default_height = int(SCALED_WINDOW_RESOLUTION[1] * 1.9)
        # # default_width = int(self.winfo_screenwidth() * 0.8)
        # # default_height = int(self.winfo_screenheight() * 0.8)
        # self.geometry(f"{default_width}x{default_height}+0+0")
        self._change_scaling_event(self.DEFAULT_SCALING)
        maximize_window(self)

        # Load rooms
        room_data = named_values(rooms, RoomData)
        if not room_data:
            raise ValueError("No RoomData definitions were found in rooms.py.")

        room = next(iter(room_data))
        self.app_state = AppState(room_data, current_room_name=room)

        # configure window
        self.title("Room Editor")

        self.new_instance_requested: bool = False

        self.sidebar_frame = LeftSidebar(
            self,
            width=self.LEFT_SIDEBAR_WIDTH,
            on_theme_change=self._change_theme_event,
            on_scaling_change=self._change_scaling_event,
        )
        self.room_viewport = RoomViewport(
            self,
            self.app_state,
            on_room_change=self._change_room_event,
            on_save=self.on_save,
            on_selection_change=self.on_selection_change,
            on_add_room=self.on_add_room,
        )
        self.main_tabview = MainTabview(
            self,
            self.app_state,
            on_select=self.on_select_item,
            on_tab_change=self.on_tab_change,
            on_add_item=self.on_add_item,
            on_delete_item=self.on_delete_item,
            on_draw_region=self.on_draw_region,
            on_finish_region=self.on_finish_region,
        )
        self.object_form = ObjectForm(
            self,
            self.app_state,
        )

        self.sidebar_frame.pack(side="left", fill="y")
        self.main_tabview.pack(side="right", fill="both", expand=True, padx=0, pady=(0, 5))
        self.room_viewport.pack(side="top", expand=False)
        self.object_form.pack(side="bottom", fill="both", expand=True, padx=0, pady=(0, 5))

    @property
    def current_room(self) -> RoomData:
        return self.app_state.current_room

    def _open_ctktoplevel_event(self) -> None:
        toplevel = CTkToplevel(self)
        toplevel.geometry(f"{500}x{250}")
        toplevel.resizable(width=True, height=True)
        toplevel.title("CTkToplevel")

    def _change_scaling_event(self, new_scaling: str) -> None:
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        set_widget_scaling(new_scaling_float)
        # Updating the window scaling resizes the window accordingly.
        # set_window_scaling(new_scaling_float)

    def _change_theme_event(self, new_theme: str) -> None:
        set_default_color_theme(new_theme)
        self.new_instance_requested = True
        self.destroy()

    def _change_room_event(self, new_room: str) -> None:
        """Switch the preview and content tree to the chosen room."""
        self.app_state.current_room_name = new_room
        self.main_tabview.refresh_tree(self.current_room)

        self.main_tabview.clear_selection()
        self.app_state.selected_index = None
        self.app_state.selected = None
        self.room_viewport.draw_room(self.current_room)
        self.object_form._refresh_form()

    def on_tab_change(self) -> None:
        self.main_tabview.clear_selection()
        self.app_state.selected_index = None
        self.app_state.selected = None
        self.room_viewport.draw_room(self.current_room)
        self.object_form._refresh_form()

    def on_selection_change(self) -> None:
        self.object_form._refresh_form()

    def on_save(self) -> None:
        """Save changes made to room data back to rooms.py."""
        try:
            current_source = ROOMS_FILE.read_text()
            updated_source = update_room_source(current_source, self.app_state.room_data)
            ROOMS_FILE.write_text(updated_source)
            logger.warning(f"✓ Saved {len(self.app_state.room_data)} room(s) to {ROOMS_FILE}")
        except (OSError, ValueError, SyntaxError) as e:
            logger.warning(f"✗ Error saving rooms: {e}")
            return

        _run_ruff_fix(ROOMS_FILE)

    def on_select_item(self, item_id: str, get_items: Callable[[RoomData], Sequence]) -> None:
        """Generic item selection handler for props, characters, regions, and points."""
        items = get_items(self.current_room)
        for i, item in enumerate(items):
            if item.id == item_id:
                self.app_state.selected_index = i
                self.app_state.selected = item
                self.room_viewport.draw_room(self.current_room)
                self.object_form._refresh_form()
                break

    def on_add_item(self, tab_name: str) -> None:
        """Add a new item to the current room based on the active tab."""
        current_room = self.current_room
        current_index = len(getattr(current_room, self._get_collection_name(tab_name)))

        updated_room: RoomData
        if tab_name == "Props":
            new_item_prop = PropData(
                id=f"prop_{current_index}",
                description="New prop",
                image=Images.LANTERN_1,
                position=(240, 75),
            )
            self.app_state.selected = new_item_prop
            updated_room = replace(current_room, props=(*current_room.props, new_item_prop))
        elif tab_name == "Characters":
            new_item_char = CharacterData(
                id=f"character_{current_index}",
                description="New character",
                image=Images.MC_IDLE,
                position=(240, 75),
                walk_image=Images.MC_WALK,
            )
            self.app_state.selected = new_item_char
            updated_room = replace(current_room, characters=(*current_room.characters, new_item_char))
        elif tab_name == "Regions":
            new_item_region = RegionData(
                id=f"region_{current_index}",
                description="New region",
                polygon=((10, 10), (100, 10), (100, 100), (10, 100)),
            )
            self.app_state.selected = new_item_region
            updated_room = replace(current_room, regions=(*current_room.regions, new_item_region))
        elif tab_name == "Points":
            new_item_point = NamedPointData(
                id=f"point_{current_index}",
                description="New point",
                position=(240, 75),
            )
            self.app_state.selected = new_item_point
            updated_room = replace(current_room, points=(*current_room.points, new_item_point))
        else:
            logger.error(f"Unknown tab name: {tab_name}")
            return

        # Update app state
        self.app_state.room_data[self.app_state.current_room_name] = updated_room
        self.app_state.selected_index = current_index

        # Refresh UI
        self.main_tabview.refresh_tree(updated_room)
        self.room_viewport.draw_room(updated_room)
        self.object_form._refresh_form()

    def on_delete_item(self, tab_name: str) -> None:
        """Delete the selected item from the current room with confirmation."""
        if self.app_state.selected is None:
            return

        selected = self.app_state.selected
        item_name = selected.id if hasattr(selected, "id") else str(selected)

        # Show confirmation dialog unless skip confirmation is enabled
        skip_confirmation = self.sidebar_frame.skip_confirmation_switch.get()
        if not skip_confirmation:
            confirmed = self._show_confirmation_dialog(
                f"Delete '{item_name}'?",
                f"Are you sure you want to delete '{item_name}'?",
            )

            if not confirmed:
                return

        current_room = self.current_room
        updated_room: RoomData

        if tab_name == "Props":
            new_props = tuple(p for p in current_room.props if p != selected)
            updated_room = replace(current_room, props=new_props)
        elif tab_name == "Characters":
            new_chars = tuple(c for c in current_room.characters if c != selected)
            updated_room = replace(current_room, characters=new_chars)
        elif tab_name == "Regions":
            new_regions = tuple(r for r in current_room.regions if r != selected)
            updated_room = replace(current_room, regions=new_regions)
        elif tab_name == "Points":
            new_points = tuple(pt for pt in current_room.points if pt != selected)
            updated_room = replace(current_room, points=new_points)
        else:
            logger.error(f"Unknown tab name: {tab_name}")
            return

        # Update app state
        self.app_state.room_data[self.app_state.current_room_name] = updated_room
        self.app_state.selected = None
        self.app_state.selected_index = -1

        # Refresh UI
        self.main_tabview.refresh_tree(updated_room)
        self.room_viewport.draw_room(updated_room)
        self.object_form._refresh_form()

    def on_add_room(self) -> None:
        """Add a new room to the room data after prompting for a name."""
        # Show a dialog to get the room name from the user
        room_name = self._prompt_room_name()
        if room_name is None or not room_name.strip():
            return  # User cancelled or entered empty name

        room_name = room_name.strip()

        # Generate a valid Python identifier from the room name
        # Replace spaces and special characters with underscores
        var_name = "".join(c if c.isalnum() or c == "_" else "_" for c in room_name)
        # Ensure it starts with a letter or underscore
        if not var_name or not (var_name[0].isalpha() or var_name[0] == "_"):
            var_name = f"_{var_name}"
        # Make it uppercase for consistency with existing rooms
        var_name = var_name.upper()

        # Ensure uniqueness
        original_var_name = var_name
        counter = 1
        while var_name in self.app_state.room_data:
            var_name = f"{original_var_name}_{counter}"
            counter += 1

        # Create a new room with default values
        new_room = RoomData(id=room_name, description="")

        # Add to room data using the Python variable name as key
        self.app_state.room_data[var_name] = new_room

        # Update the room select dropdown
        self.room_viewport.room_select_menu.configure(values=list(self.app_state.room_data))

        # Switch to the new room
        self.room_viewport.room_select_menu.set(var_name)
        self._change_room_event(var_name)

    def _prompt_room_name(self) -> str | None:
        """Show a dialog to prompt for a room name. Returns the name or None if cancelled."""
        dialog = CTkToplevel(self)
        dialog.title("Create New Room")

        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() // 2) - 175
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        dialog.geometry(f"+{x}+{y}")

        result: list[str | None] = [None]

        # Prompt label
        prompt_label = CTkLabel(dialog, text="Enter room name:")
        prompt_label.pack(pady=(15, 5), padx=15)

        # Text entry
        name_entry = CTkEntry(dialog)
        name_entry.pack(pady=(5, 15), padx=15, fill="x")
        name_entry.focus()

        # Button frame
        button_frame = CTkFrame(dialog)
        button_frame.pack(pady=(0, 15), padx=15, fill="x")

        def on_ok() -> None:
            result[0] = name_entry.get()
            dialog.destroy()

        def on_cancel() -> None:
            result[0] = None
            dialog.destroy()

        ok_button = CTkButton(button_frame, text="OK", command=on_ok)
        ok_button.pack(side="left", fill="x", expand=True, padx=(0, 5))

        cancel_button = CTkButton(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Wait for dialog to close
        dialog.wait_window()

        return result[0]

    def _show_confirmation_dialog(self, title: str, message: str) -> bool:
        """Show a confirmation dialog with Yes/No buttons. Returns True if Yes is clicked."""
        dialog = CTkToplevel(self)
        dialog.title(title)

        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        dialog.geometry(f"+{x}+{y}")

        result: list[bool] = [False]

        # Message label
        message_label = CTkLabel(dialog, text=message, wraplength=280)
        message_label.pack(pady=(20, 20), padx=10)

        # Button frame
        button_frame = CTkFrame(dialog)
        button_frame.pack(pady=(0, 15), padx=10, fill="x")

        def on_yes() -> None:
            result[0] = True
            dialog.destroy()

        def on_no() -> None:
            result[0] = False
            dialog.destroy()

        yes_button = CTkButton(button_frame, text="Yes", command=on_yes)
        yes_button.pack(side="left", fill="x", expand=True, padx=(0, 5))

        no_button = CTkButton(button_frame, text="No", command=on_no)
        no_button.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Wait for dialog to close
        dialog.wait_window()

        return result[0]

    def on_draw_region(self) -> None:
        """Start region drawing mode by delegating to the viewport."""
        self.room_viewport.start_region_creation()

    def on_finish_region(self) -> None:
        """Finish drawing the region by delegating to the viewport."""
        self.room_viewport.finish_region_creation()
        # Refresh sidebar to show newly created region
        self.main_tabview.refresh_tree(self.current_room)
        self.object_form._refresh_form()

    @staticmethod
    def _get_collection_name(tab_name: str) -> str:
        """Map tab name to room data collection name."""
        if tab_name == "Props":
            return "props"
        elif tab_name == "Characters":
            return "characters"
        elif tab_name == "Regions":
            return "regions"
        elif tab_name == "Points":
            return "points"
        return ""


if __name__ == "__main__":
    run()
