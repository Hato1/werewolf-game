from collections.abc import Callable
from dataclasses import replace
from tkinter.constants import LEFT, NW, TOP

from customtkinter import (
    CTk,
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
from my_game.werewolf.room.editor_data import named_values
from my_game.werewolf.room.loaders import PropData, RoomData

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
    def __init__(self, master: RoomEditor, on_room_change: Callable[[str], None]) -> None:
        super().__init__(master)

        self.photo_images: list[ImageTk.PhotoImage] = []  # Keep references to prevent garbage collection
        self.selected_prop_index: int | None = None
        self.drag_start: tuple[int, int] | None = None
        self.drag_start_prop_position: tuple[float, float] | None = None

        ### Room Viewport ###
        self.room_top_menu = CTkFrame(self)
        self.room_select_label = CTkLabel(self.room_top_menu, text="Room select:", anchor="w")
        self.room_select_menu = CTkOptionMenu(
            self.room_top_menu, dynamic_resizing=False, values=list(master.room_data), command=on_room_change
        )

        self.room_top_menu.pack(side=TOP, fill="x")
        self.room_select_label.pack(side=LEFT, padx=(20, 0), pady=(10, 10))
        self.room_select_menu.pack(side=LEFT, padx=20, pady=(10, 10))

        self.room_canvas = CTkCanvas(
            self,
            width=SCALED_WINDOW_RESOLUTION[0],
            height=SCALED_WINDOW_RESOLUTION[1],
        )
        self.room_canvas.pack(side=LEFT, anchor="nw")
        self.room_canvas.bind("<Button-1>", self._on_canvas_press)
        self.room_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.room_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self.draw_room(master.current_room)

    def get_current_room_name(self) -> str:
        return self.room_select_menu.get()

    def _on_canvas_press(self, event: object) -> None:
        """Handle canvas mouse press - record drag start position."""
        if self.selected_prop_index is None:
            return

        current_room = self.master.current_room  # type: ignore[attr-defined]
        if self.selected_prop_index >= len(current_room.props):
            return

        self.drag_start = (event.x, event.y)  # type: ignore[attr-defined]
        prop = current_room.props[self.selected_prop_index]
        self.drag_start_prop_position = prop.position

    def _on_canvas_drag(self, event: object) -> None:
        """Handle canvas mouse drag - update prop position in real-time."""
        if self.drag_start is None or self.drag_start_prop_position is None or self.selected_prop_index is None:
            return

        current_room = self.master.current_room  # type: ignore[attr-defined]
        if self.selected_prop_index >= len(current_room.props):
            return

        event_x: int = event.x  # type: ignore[attr-defined]
        event_y: int = event.y  # type: ignore[attr-defined]

        delta_x = round((event_x - self.drag_start[0]) / MULTIPLIER)
        delta_y = round((event_y - self.drag_start[1]) / MULTIPLIER)

        new_x = self.drag_start_prop_position[0] + delta_x
        new_y = self.drag_start_prop_position[1] + delta_y

        old_prop = current_room.props[self.selected_prop_index]
        new_prop = replace(old_prop, position=(new_x, new_y))

        new_props = (
            *current_room.props[: self.selected_prop_index],
            new_prop,
            *current_room.props[self.selected_prop_index + 1 :],
        )

        updated_room = replace(current_room, props=new_props)
        room_name = self.room_select_menu.get()
        self.master.room_data[room_name] = updated_room  # type: ignore[attr-defined]

        self.draw_room(updated_room)

    def _on_canvas_release(self, event: object) -> None:
        """Handle canvas mouse release - finalize drag."""
        self.drag_start = None
        self.drag_start_prop_position = None

    def get_prop_image(self, prop: PropData) -> ImageTk.PhotoImage:
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

        for index, prop in enumerate(props):
            image = self.get_prop_image(prop)
            self.photo_images.append(image)
            corrected_position = (prop.position[0] * MULTIPLIER, prop.position[1] * MULTIPLIER)
            self.room_canvas.create_image(
                *corrected_position,
                image=image,
                anchor=NW,
                # tags=("content", f"props:{index}"),
            )
            print("added image", index, "at position", prop.position)
            # if self.selection == ("props", index):
            #     self.room_canvas.create_rectangle(
            #         self._canvas_scale(prop.position[0]),
            #         self._canvas_scale(prop.position[1]),
            #         self._canvas_scale(prop.position[0] + prop.size[0]),
            #         self._canvas_scale(prop.position[1] + prop.size[1]),
            #         outline="#ffcc00",
            #         width=int(2 * self.scale),
            #     )

        # for index, character in enumerate(characters):
        #     size = self._scaled_size(character.image, character.scale)
        #     photo_size = (self._canvas_scale(size[0]), self._canvas_scale(size[1]))
        #     photo = self._get_photo(character.image, photo_size)
        #     self.room_canvas.create_image(
        #         (self._canvas_scale(character.position[0]), self._canvas_scale(character.position[1])),
        #         image=photo,
        #         anchor=tk.S,
        #         tags=("content", f"characters:{index}"),
        #     )
        #     if self.selection == ("characters", index):
        #         rect = self.room_canvas.bbox(f"characters:{index}")
        #         if rect is None:
        #             rect = (
        #                 self._canvas_scale(character.position[0] - size[0] // 2),
        #                 self._canvas_scale(character.position[1] - size[1]),
        #                 self._canvas_scale(character.position[0] + size[0] // 2),
        #                 self._canvas_scale(character.position[1]),
        #             )
        #         self.room_canvas.create_rectangle(rect, outline="#ffcc00", width=int(2 * self.scale))

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


class MainTabview(CTkTabview):
    def __init__(self, master: RoomEditor, on_prop_select: Callable[[str], None]) -> None:
        super().__init__(master)

        # Props tab
        props = [p.name for p in master.current_room.props]
        self.prop_frame = self.add(f"Props ({len(props)})")
        self.scrollable_frame = CTkScrollableFrame(self.prop_frame)
        self.prop_selector = CTkSegmentedButton(
            self.scrollable_frame,
            values=props,
            orientation="vertical",
            command=on_prop_select,
        )

        self.scrollable_frame.pack(fill="both", expand=True)
        self.prop_selector.pack(fill="both", expand=True)

        # Character tab
        characters = [c.name for c in master.current_room.characters]
        self.character_frame = self.add(f"Characters ({len(characters)})")
        self.scrollable_character_frame = CTkScrollableFrame(self.character_frame)
        self.character_selector = CTkSegmentedButton(
            self.scrollable_character_frame, values=characters, orientation="vertical"
        )

        self.scrollable_character_frame.pack(fill="both", expand=True)
        self.character_selector.pack(fill="both", expand=True)


class RoomEditor(CTk):
    SPACING = 20
    DEFAULT_SCALING = "200%"

    LEFT_SIDEBAR_WIDTH = 140
    RIGHT_SIDEBAR_WIDTH = 140

    def __init__(self) -> None:
        super().__init__()
        default_width = int(self.LEFT_SIDEBAR_WIDTH + SCALED_WINDOW_RESOLUTION[0] + self.RIGHT_SIDEBAR_WIDTH + 1000)
        default_height = int(SCALED_WINDOW_RESOLUTION[1] * 1.5)
        self.geometry(f"{default_width}x{default_height}")
        self._change_scaling_event(self.DEFAULT_SCALING)

        # Load rooms
        self.room_data = named_values(rooms, RoomData)
        if not self.room_data:
            raise ValueError("No RoomData definitions were found in rooms.py.")
        self._default_room = next(iter(self.room_data.values()))

        # configure window
        self.title("Room Editor")

        self.new_instance_requested: bool = False

        ### create left sidebar frame with widgets ###
        self.sidebar_frame = LeftSidebar(
            self,
            width=self.LEFT_SIDEBAR_WIDTH,
            on_theme_change=self._change_theme_event,
            on_scaling_change=self._change_scaling_event,
        )
        self.room_viewport = RoomViewport(self, on_room_change=self._change_room_event)
        self.main_tabview = MainTabview(self, on_prop_select=self.prop_select_event)

        self.sidebar_frame.pack(side="left", fill="y")
        self.room_viewport.pack(side="left", fill="both", expand=False)
        self.main_tabview.pack(side="right", fill="both", expand=True, padx=0, pady=(0, 5))

    @property
    def current_room(self) -> RoomData:
        if hasattr(self, "room_viewport"):
            return self.room_data[self.room_viewport.get_current_room_name()]
        else:
            return self._default_room

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
        # self._refresh_tree()
        self.room_viewport.draw_room(self.room_data[new_room])

    def prop_select_event(self, selected_prop: str) -> None:
        current_room = self.current_room
        for i, prop in enumerate(current_room.props):
            if prop.name == selected_prop:
                self.room_viewport.selected_prop_index = i
                break
