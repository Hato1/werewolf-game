from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import Event
from tkinter.constants import LEFT, NW, TOP
from typing import NamedTuple, cast

from customtkinter import (
    CTk,
    CTkButton,
    CTkCanvas,
    CTkEntry,
    CTkFont,
    CTkFrame,
    CTkImage,
    CTkInputDialog,
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
from my_game.werewolf.room import rooms
from my_game.werewolf.room.editor_data import named_values, update_room_source
from my_game.werewolf.room.loaders import CharacterData, NamedPointData, PropData, RegionData, RoomData

logger = get_logger(__name__)

DEFAULT_THEME = "dark-blue"
NATIVE_WINDOW_RESOLUTION = (480, 208)
MULTIPLIER = 5  # Adjust this if you want to scale the room canvas size
SCALED_WINDOW_RESOLUTION = (NATIVE_WINDOW_RESOLUTION[0] * MULTIPLIER, NATIVE_WINDOW_RESOLUTION[1] * MULTIPLIER)


def run() -> None:
    set_appearance_mode("Dark")
    set_default_color_theme(DEFAULT_THEME)
    DrawEngine.preferred_drawing_method = "polygon_shapes"

    new_instance: bool = True
    while new_instance:
        app = RoomEditor()
        app.mainloop()
        new_instance = app.new_instance_requested


@dataclass
class AppState:
    room_data: dict[str, RoomData]
    current_room_name: str
    selected: PropData | CharacterData | RegionData | NamedPointData | None = None
    selected_index: int | None = None

    @property
    def current_room(self) -> RoomData:
        return self.room_data[self.current_room_name]


class LeftSidebar(CTkFrame):
    LOGO_SIZE = (100, 100)
    LOGO_PATH = "src/my_game/werewolf/assets/textures/studio-light.png"

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
        self.scaling_optionmenu = CTkOptionMenu(self, values=["100%", "150%", "200%"], command=self.on_scaling_change)
        widget_scaling = round(ScalingTracker.widget_scaling * 100)
        self.scaling_optionmenu.set(f"{widget_scaling}%")

        self.logo.pack(side="top", fill="x", padx=5, pady=5)
        self.logo_label.pack(side="top", fill="x", padx=0, pady=0)
        self.theme_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.theme_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))
        self.scaling_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.scaling_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))


class RoomViewport(CTkFrame):
    def __init__(
        self,
        master: RoomEditor,
        app_state: AppState,
        on_room_change: Callable[[str], None],
        on_save: Callable[[], None],
        on_selection_change: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.app_state = app_state
        self.on_selection_change = on_selection_change

        self.photo_images: list[ImageTk.PhotoImage] = []  # Keep references to prevent garbage collection
        self.drag_start: tuple[int, int] | None = None
        self.drag_start_image_position: tuple[int, int] | None = None

        ### Room Viewport ###
        self.room_top_menu = CTkFrame(self)
        self.room_select_label = CTkLabel(self.room_top_menu, text="Room select:", anchor="w")
        self.room_select_menu = CTkOptionMenu(
            self.room_top_menu, dynamic_resizing=False, values=list(self.app_state.room_data), command=on_room_change
        )
        self.save_button = CTkButton(
            self.room_top_menu, text="SAVE ALL CHANGES", command=on_save, fg_color="darkred", hover_color="red"
        )

        self.room_top_menu.pack(side=TOP, fill="x")
        self.room_select_label.pack(side=LEFT, padx=(20, 0), pady=(10, 10))
        self.room_select_menu.pack(side=LEFT, padx=20, pady=(10, 10))
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
        """Handle canvas mouse press - record drag start position."""
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

        props = sorted(room.props, key=lambda item: item.depth, reverse=True)
        characters = sorted(room.characters, key=lambda item: item.depth, reverse=True)

        for prop in props:
            image = self.get_prop_image(prop)
            self.photo_images.append(image)
            corrected_position = (prop.position[0] * MULTIPLIER, prop.position[1] * MULTIPLIER)
            self.room_canvas.create_image(
                *corrected_position,
                image=image,
                anchor=NW,
                # tags=("content", f"props:{index}"),
            )

        for character in characters:
            image = self.get_prop_image(character)
            self.photo_images.append(image)
            corrected_position = (character.position[0] * MULTIPLIER, character.position[1] * MULTIPLIER)
            self.room_canvas.create_image(
                *corrected_position,
                image=image,
                anchor=NW,
                # tags=("content", f"characters:{index}"),
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

        # for index, hotspot in enumerate(room.hotspots):
        #     self._draw_polygon("hotspots", index, hotspot.polygon, "#00d8ff")

        # for index, area in enumerate(room.walkable_areas):
        #     self._draw_polygon("walkable_areas", index, area, "#ffffff")
        # for index, point in enumerate(room.points):
        #     x, y = self._canvas_scale(point[0]), self._canvas_scale(point[1])
        #     radius = int(5 * self.scale)
        #     self.room_canvas.create_oval(
        #         x - radius,
        #         y - radius,
        #         x + radius,
        #         y + radius,
        #         fill="#ff55dd",
        #         outline="",
        #         tags=("content", f"points:{index}"),
        #     )


class TabData(NamedTuple):
    """Container for tab UI components and data accessor."""

    scrollable_frame: CTkScrollableFrame
    selector_button: CTkSegmentedButton
    get_items: Callable[[RoomData], Sequence]


class MainTabview(CTkTabview):
    BUTTON_HEIGHT = 30

    def __init__(
        self,
        master: RoomEditor,
        app_state: AppState,
        on_select: Callable[[str, Callable[[RoomData], Sequence]], None],
        on_tab_change: Callable[[], None],
    ) -> None:
        super().__init__(master, command=on_tab_change)
        self.app_state = app_state

        self.tabs: dict[str, TabData] = {}

        self._add_tab("Props", on_select, lambda room_data: room_data.props)
        self._add_tab("Character", on_select, lambda room_data: room_data.characters)
        self._add_tab("Regions", on_select, lambda room_data: room_data.regions)
        self._add_tab("Points", on_select, lambda room_data: room_data.points)

        self.refresh_tree(self.app_state.current_room)

    def _add_tab(
        self,
        label: str,
        on_select: Callable[[str, Callable[[RoomData], Sequence]], None],
        get_items: Callable[[RoomData], Sequence],
    ) -> None:
        """Add a tab with a scrollable frame and segmented button selector."""
        frame = self.add(label)
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
        selector.pack(fill="both", expand=True)

        self.tabs[label] = TabData(scrollable, selector, get_items)

    def refresh_tree(self, room: RoomData) -> None:
        """Update all tab titles and selectors with current room data."""
        for tab_index, (tab_name, tab_data) in enumerate(self.tabs.items()):
            names = [item.name for item in tab_data.get_items(room)]

            old_title = self.get(tab_index)
            new_title = f"{tab_name} ({len(names)})"
            if old_title != new_title:
                self.rename(old_title, new_title)
                # Fix bug where selected tab looks unselected when its title changes
                self.set(self.get())

            tab_data.selector_button.configure(values=names, height=len(names) * self.BUTTON_HEIGHT)

    def clear_selection(self) -> None:
        """Clear selection from all tabs."""
        for tab_data in self.tabs.values():
            tab_data.selector_button.set("")


class ObjectForm(CTkFrame):
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

        self._refresh_form()

    def _is_point_type(self, field_type: object) -> bool:
        """Check if a type is a Point type (tuple[int, int])."""
        point_length = 2
        return (
            hasattr(field_type, "__origin__")
            and getattr(field_type, "__origin__", None) is tuple
            and len(getattr(field_type, "__args__", [])) == point_length
        )

    def _get_display_value(self, value: object) -> str:
        """Convert a field value to a display string."""
        point_length = 2
        if isinstance(value, (tuple, list)):
            if isinstance(value, tuple) and len(value) == point_length and all(isinstance(x, int) for x in value):
                # Point/position tuple
                x, y = value
                return f"{x}, {y}"
            return str(value)
        elif isinstance(value, bool):
            return str(value)
        return str(value)

    def _get_parsed_value(self, field_type: object, value: str) -> object:
        """Helper to get the parsed value for a given type."""
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
        if origin is tuple:
            # Handle tuple types like tuple[int, int]
            parts = [p.strip() for p in value.split(",")]
            return tuple(int(p) for p in parts)

        if origin is type(int | str):  # Union in Python 3.10+
            # Try to parse with the first non-None type
            args = getattr(field_type, "__args__", ())
            for arg in args:
                if arg is not type(None):
                    return self._parse_input_value(arg, value)

        return value

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

        selected = self.app_state.selected
        if selected is None:
            # Show room metadata
            current_room = self.app_state.current_room
            self.title_label.configure(text=f"Room: {current_room.name}")
            self._add_field_widgets(current_room)
        else:
            # Show selected object attributes
            self.title_label.configure(text=f"{type(selected).__name__}: {selected.name}")
            self._add_field_widgets(selected)

    def _add_field_widgets(self, obj: RoomData | PropData | CharacterData | RegionData | NamedPointData) -> None:
        """Add input widgets for all fields of the given object."""
        from dataclasses import fields

        if not hasattr(obj, "__dataclass_fields__"):
            return

        all_fields = list(fields(obj))

        # Create two-column layout
        columns_frame = CTkFrame(self.scrollable_frame)
        columns_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create left and right column frames
        left_column = CTkFrame(columns_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_column = CTkFrame(columns_frame)
        right_column.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Distribute fields between columns
        for idx, field_info in enumerate(all_fields):
            field_name = field_info.name
            field_value = getattr(obj, field_name)

            # Choose column based on index (even -> left, odd -> right)
            column = left_column if idx % 2 == 0 else right_column

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
            widget: CTkSwitch | CTkEntry
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

            else:
                # Integer, Point, or String: use entry
                widget = CTkEntry(field_frame)
                display_value = self._get_display_value(field_value)
                widget.insert(0, display_value)
                self.field_widgets[field_name] = widget

            widget.pack(side="right", fill="x", expand=True)

        # Save button
        save_button = CTkButton(
            self.scrollable_frame,
            text="Apply Changes",
            command=self._on_save_changes,
        )
        save_button.pack(fill="x", padx=5, pady=(10, 0))

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

    def _redraw_viewport(self) -> None:
        """Redraw the room viewport to reflect changes."""
        parent = self.master
        if isinstance(parent, RoomEditor):
            parent.room_viewport.draw_room(self.app_state.current_room)

    def _on_save_changes(self) -> None:
        """Save changes from form back to the selected object."""
        from dataclasses import fields, replace

        selected = self.app_state.selected
        if selected is None or not hasattr(selected, "__dataclass_fields__"):
            return

        changes: dict[str, object] = {}
        for field_info in fields(selected):  # type: ignore[arg-type]
            field_name = field_info.name
            if field_name not in self.field_widgets:
                continue

            widget = self.field_widgets[field_name]
            field_type = field_info.type

            try:
                if isinstance(widget, CTkSwitch):
                    new_value: object = widget.get()
                elif isinstance(widget, CTkEntry):
                    input_text = widget.get()
                    new_value = self._parse_input_value(field_type, input_text)
                else:
                    continue

                old_value = getattr(selected, field_name)
                if new_value != old_value:
                    changes[field_name] = new_value
            except (ValueError, TypeError) as e:
                logger.error("Error parsing field %s: %s", field_name, e)

        if not changes:
            return

        # Update the selected object
        updated_object = replace(selected, **changes)  # type: ignore[arg-type]
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


class RoomEditor(CTk):
    SPACING = 20
    DEFAULT_SCALING = "200%"

    LEFT_SIDEBAR_WIDTH = 140
    RIGHT_SIDEBAR_WIDTH = 140

    def __init__(self) -> None:
        super().__init__()

        # Set window size and scaling
        default_width = int(self.LEFT_SIDEBAR_WIDTH + SCALED_WINDOW_RESOLUTION[0] + self.RIGHT_SIDEBAR_WIDTH + 800)
        default_height = int(SCALED_WINDOW_RESOLUTION[1] * 1.9)
        self.geometry(f"{default_width}x{default_height}")
        self._change_scaling_event(self.DEFAULT_SCALING)

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
        )
        self.main_tabview = MainTabview(
            self,
            self.app_state,
            on_select=self.on_select_item,
            on_tab_change=self.on_tab_change,
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

    def _open_input_dialog_event(self) -> None:
        dialog = CTkInputDialog(title="CTkInputDialog", text="Description of requested input")
        dialog.get_input()

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
        rooms_file = Path("src/my_game/werewolf/room/rooms.py")

        try:
            current_source = rooms_file.read_text()
            updated_source = update_room_source(current_source, self.app_state.room_data)
            rooms_file.write_text(updated_source)
            logger.warning(f"✓ Saved {len(self.app_state.room_data)} room(s) to {rooms_file}")
        except (OSError, ValueError, SyntaxError) as e:
            logger.warning(f"✗ Error saving rooms: {e}")

    def on_select_item(self, item_name: str, get_items: Callable[[RoomData], Sequence]) -> None:
        """Generic item selection handler for props, characters, regions, and points."""
        items = get_items(self.current_room)
        for i, item in enumerate(items):
            if item.name == item_name:
                self.app_state.selected_index = i
                self.app_state.selected = item
                self.room_viewport.draw_room(self.current_room)
                self.object_form._refresh_form()
                break
