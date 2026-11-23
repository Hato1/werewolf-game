from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import Event
from tkinter.constants import LEFT, NW, TOP
from typing import NamedTuple

from customtkinter import (
    CTk,
    CTkButton,
    CTkCanvas,
    CTkFont,
    CTkFrame,
    CTkImage,
    CTkInputDialog,
    CTkLabel,
    CTkOptionMenu,
    CTkScrollableFrame,
    CTkSegmentedButton,
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

from my_game.werewolf.room import rooms
from my_game.werewolf.room.editor_data import named_values, update_room_source
from my_game.werewolf.room.loaders import CharacterData, PropData, RoomData

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
    selected_prop_index: int | None = None

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
    ) -> None:
        super().__init__(master)
        self.app_state = app_state

        self.photo_images: list[ImageTk.PhotoImage] = []  # Keep references to prevent garbage collection
        self.drag_start: tuple[int, int] | None = None
        self.drag_start_prop_position: tuple[int, int] | None = None

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

    def _on_canvas_press(self, event: Event) -> None:
        """Handle canvas mouse press - record drag start position."""
        if self.app_state.selected_prop_index is None:
            return

        current_room = self.app_state.current_room
        if self.app_state.selected_prop_index >= len(current_room.props):
            return

        self.drag_start = (event.x, event.y)
        prop = current_room.props[self.app_state.selected_prop_index]
        self.drag_start_prop_position = prop.position

    def _on_canvas_drag(self, event: Event) -> None:
        """Handle canvas mouse drag - update prop position in real-time."""
        if (
            self.drag_start is None
            or self.drag_start_prop_position is None
            or self.app_state.selected_prop_index is None
        ):
            return

        current_room = self.app_state.current_room
        if self.app_state.selected_prop_index >= len(current_room.props):
            return

        event_x: int = event.x
        event_y: int = event.y

        delta_x = round((event_x - self.drag_start[0]) / MULTIPLIER)
        delta_y = round((event_y - self.drag_start[1]) / MULTIPLIER)

        new_x = self.drag_start_prop_position[0] + delta_x
        new_y = self.drag_start_prop_position[1] + delta_y

        old_prop = current_room.props[self.app_state.selected_prop_index]
        new_prop = replace(old_prop, position=(new_x, new_y))

        new_props = (
            *current_room.props[: self.app_state.selected_prop_index],
            new_prop,
            *current_room.props[self.app_state.selected_prop_index + 1 :],
        )

        updated_room = replace(current_room, props=new_props)
        room_name = self.room_select_menu.get()
        self.app_state.room_data[room_name] = updated_room

        self.draw_room(updated_room)

    def _on_canvas_release(self, event: Event) -> None:
        """Handle canvas mouse release - finalize drag."""
        self.drag_start = None
        self.drag_start_prop_position = None

    def _on_arrow_key(self, event: Event) -> None:
        """Handle arrow key press - nudge selected prop by 1 pixel."""
        if self.app_state.selected_prop_index is None:
            return

        current_room = self.app_state.current_room
        if self.app_state.selected_prop_index >= len(current_room.props):
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

        old_prop = current_room.props[self.app_state.selected_prop_index]
        new_position = (old_prop.position[0] + delta_x, old_prop.position[1] + delta_y)
        new_prop = replace(old_prop, position=new_position)

        new_props = (
            *current_room.props[: self.app_state.selected_prop_index],
            new_prop,
            *current_room.props[self.app_state.selected_prop_index + 1 :],
        )

        updated_room = replace(current_room, props=new_props)
        room_name = self.room_select_menu.get()
        self.app_state.room_data[room_name] = updated_room

        self.draw_room(updated_room)

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
        # characters = sorted(room.characters, key=lambda item: item.depth, reverse=True)

        selected_rectangle = None

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

        for character in room.characters:
            image = self.get_prop_image(character)
            self.photo_images.append(image)
            corrected_position = (character.position[0] * MULTIPLIER, character.position[1] * MULTIPLIER)
            self.room_canvas.create_image(
                *corrected_position,
                image=image,
                anchor=NW,
                # tags=("content", f"characters:{index}"),
            )

        if self.app_state.selected_prop_index is not None:
            prop = room.props[self.app_state.selected_prop_index]
            image = self.get_prop_image(prop)
            corrected_position = (prop.position[0] * MULTIPLIER, prop.position[1] * MULTIPLIER)
            selected_rectangle = (
                *corrected_position,
                (corrected_position[0] + image.width()),
                (corrected_position[1] + image.height()),
            )

        if selected_rectangle:
            self.room_canvas.create_rectangle(
                *selected_rectangle,
                outline="#ffcc00",
                width=int(1 * MULTIPLIER),
            )

        # for index, hotspot in enumerate(room.hotspots):
        #     self._draw_polygon("hotspots", index, hotspot.polygon, "#00d8ff")
        # for index, region in enumerate(room.regions):
        #     self._draw_polygon("regions", index, region, "#8cff66")
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
        on_prop_select: Callable[[str], None],
        on_tab_change: Callable[[], None],
    ) -> None:
        super().__init__(master, command=on_tab_change)
        self.app_state = app_state

        self.tabs: dict[str, TabData] = {}

        self._add_tab("Props", on_prop_select, lambda room_data: room_data.props)
        self._add_tab("Character", None, lambda room_data: room_data.characters)
        self._add_tab("Regions", None, lambda room_data: room_data.regions)
        self._add_tab("Points", None, lambda room_data: room_data.points)

        self.refresh_tree(self.app_state.current_room)

    def _add_tab(
        self,
        label: str,
        command: Callable[[str], None] | None,
        get_items: Callable[[RoomData], Sequence],
    ) -> None:
        """Add a tab with a scrollable frame and segmented button selector."""
        frame = self.add(label)
        scrollable = CTkScrollableFrame(frame)
        selector = CTkSegmentedButton(
            scrollable,
            orientation="vertical",
            dynamic_resizing=False,
            command=command,
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

            tab_data.selector_button.configure(values=names, height=len(names) * self.BUTTON_HEIGHT)

    def clear_selection(self) -> None:
        """Clear selection from all tabs."""
        for tab_data in self.tabs.values():
            tab_data.selector_button.set("")


class RoomEditor(CTk):
    SPACING = 20
    DEFAULT_SCALING = "200%"

    LEFT_SIDEBAR_WIDTH = 140
    RIGHT_SIDEBAR_WIDTH = 140

    def __init__(self) -> None:
        super().__init__()

        # Set window size and scaling
        default_width = int(self.LEFT_SIDEBAR_WIDTH + SCALED_WINDOW_RESOLUTION[0] + self.RIGHT_SIDEBAR_WIDTH + 1000)
        default_height = int(SCALED_WINDOW_RESOLUTION[1] * 1.5)
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
            self, self.app_state, on_room_change=self._change_room_event, on_save=self.on_save
        )
        self.main_tabview = MainTabview(
            self, self.app_state, on_prop_select=self.prop_select_event, on_tab_change=self.on_tab_change
        )

        self.sidebar_frame.pack(side="left", fill="y")
        self.room_viewport.pack(side="left", fill="both", expand=False)
        self.main_tabview.pack(side="right", fill="both", expand=True, padx=0, pady=(0, 5))

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
        self.app_state.selected_prop_index = None
        self.room_viewport.draw_room(self.current_room)

    def on_tab_change(self) -> None:
        self.main_tabview.clear_selection()
        self.app_state.selected_prop_index = None
        self.room_viewport.draw_room(self.current_room)

    def on_save(self) -> None:
        """Save changes made to room data back to rooms.py."""
        rooms_file = Path("src/my_game/werewolf/room/rooms.py")

        try:
            current_source = rooms_file.read_text()
            updated_source = update_room_source(current_source, self.app_state.room_data)
            rooms_file.write_text(updated_source)
            print(f"✓ Saved {len(self.app_state.room_data)} room(s) to {rooms_file}")
        except (OSError, ValueError, SyntaxError) as e:
            print(f"✗ Error saving rooms: {e}")

    def prop_select_event(self, selected_prop: str) -> None:
        current_room = self.current_room
        for i, prop in enumerate(current_room.props):
            if prop.name == selected_prop:
                self.app_state.selected_prop_index = i
                self.room_viewport.draw_room(current_room)
                break
