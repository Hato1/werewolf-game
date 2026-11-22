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
    set_window_scaling,
)
from PIL import Image, ImageTk

from my_game.werewolf.assets import Images
from my_game.werewolf.room import rooms
from my_game.werewolf.room.editor_data import named_values
from my_game.werewolf.room.loaders import PropData, RoomData


def run() -> None:
    set_appearance_mode("Dark")
    set_default_color_theme("dark-blue")
    DrawEngine.preferred_drawing_method = "polygon_shapes"

    new_instance: bool = True
    while new_instance:
        app = RoomEditor()
        app.mainloop()
        new_instance = app.new_instance_requested


class RoomEditor(CTk):
    SPACING = 20
    DEFAULT_SCALING = "200%"
    LOGO_SIZE = (100, 100)
    LOGO_PATH = "src/my_game/werewolf/assets/textures/studio-light.png"

    NATIVE_WINDOW_RESOLUTION = (480, 208)
    MULTIPLIER = 5  # Adjust this if you want to scale the room canvas size

    def __init__(self) -> None:
        super().__init__()
        self._change_scaling_event(self.DEFAULT_SCALING)

        # Load rooms
        self.room_data = named_values(rooms, RoomData)
        if not self.room_data:
            raise ValueError("No RoomData definitions were found in rooms.py.")
        current_room = next(iter(self.room_data.values()))

        # configure window
        self.title("Room Editor")

        self.new_instance_requested: bool = False
        self.photo_images: list[ImageTk.PhotoImage] = []  # Keep references to prevent garbage collection

        ### create left sidebar frame with widgets ###
        self.sidebar_frame = CTkFrame(self, width=140, corner_radius=0)
        logo_image = CTkImage(Image.open(self.LOGO_PATH).convert("RGBA"), size=self.LOGO_SIZE)
        self.logo = CTkLabel(self.sidebar_frame, image=logo_image, text="")
        self.logo_label = CTkLabel(self.sidebar_frame, text="Room Editor", font=CTkFont(size=20, weight="bold"))
        # Theme selection for the UI
        self.theme_label = CTkLabel(self.sidebar_frame, text="Theme:", anchor="w")
        self.theme_optionmenu = CTkOptionMenu(
            self.sidebar_frame, values=ThemeManager._built_in_themes, command=self._change_theme_event
        )
        # Scaling options for the UI
        self.scaling_label = CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_optionmenu = CTkOptionMenu(
            self.sidebar_frame, values=["100%", "150%", "200%"], command=self._change_scaling_event
        )
        widget_scaling = round(ScalingTracker.widget_scaling * 100)
        self.scaling_optionmenu.set(f"{widget_scaling}%")

        self.sidebar_frame.pack(side="left", fill="y")
        self.logo.pack(side="top", fill="x", padx=5, pady=5)
        self.logo_label.pack(side="top", fill="x", padx=0, pady=0)
        self.theme_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.theme_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))
        self.scaling_label.pack(side="top", fill="x", padx=20, pady=(10, 0))
        self.scaling_optionmenu.pack(side="top", fill="x", padx=20, pady=(0, 10))

        ### create main tabview ###
        self.main_tabview = CTkTabview(self)
        self.main_tabview.pack(side="right", fill="both", expand=True, padx=0, pady=(0, 5))

        # Props tab
        props = [p.name for p in current_room.props]
        self.prop_frame = self.main_tabview.add(f"Props ({len(props)})")
        self.scrollable_frame = CTkScrollableFrame(self.prop_frame)
        self.prop_selector = CTkSegmentedButton(self.scrollable_frame, values=props, orientation="vertical")

        self.scrollable_frame.pack(fill="both", expand=True)
        self.prop_selector.pack(fill="both", expand=True)

        # Character tab
        characters = [c.name for c in current_room.characters]
        self.character_frame = self.main_tabview.add(f"Characters ({len(characters)})")
        self.scrollable_character_frame = CTkScrollableFrame(self.character_frame)
        self.character_selector = CTkSegmentedButton(self.scrollable_frame, values=characters, orientation="vertical")

        self.scrollable_character_frame.pack(fill="both", expand=True)
        self.character_selector.pack(fill="both", expand=True)

        ### Room Viewport ###
        self.room_top_menu = CTkFrame(self)
        self.room_select_label = CTkLabel(self.room_top_menu, text="Room select:", anchor="w")
        self.room_select_menu = CTkOptionMenu(
            self.room_top_menu, dynamic_resizing=False, values=list(self.room_data), command=self._change_room
        )

        self.room_top_menu.pack(side=TOP, fill="x")
        self.room_select_label.pack(side=LEFT, padx=(20, 0), pady=(10, 10))
        self.room_select_menu.pack(side=LEFT, padx=20, pady=(10, 10))

        self.room_canvas = CTkCanvas(
            width=self.NATIVE_WINDOW_RESOLUTION[0] * self.MULTIPLIER,
            height=self.NATIVE_WINDOW_RESOLUTION[1] * self.MULTIPLIER,
        )
        self.room_canvas.pack(side=LEFT, anchor="nw")

        self._draw_room(current_room)

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
        set_window_scaling(new_scaling_float)

    def _change_theme_event(self, new_theme: str) -> None:
        set_default_color_theme(new_theme)
        self.new_instance_requested = True
        self.destroy()

    def _get_image_size(self, image: Images, scale: float = 1) -> tuple[int, int]:
        """Return the size of the given image as a (width, height) tuple."""
        pil_image = image.load()
        return (int(pil_image.size[0] * scale), int(pil_image.size[1] * scale))

    def get_prop_image(self, prop: PropData) -> ImageTk.PhotoImage:
        image = Image.open(prop.image.get_path())
        size = prop.size or (int(image.size[0] * prop.scale), int(image.size[1] * prop.scale))
        scaled_size = (size[0] * self.MULTIPLIER, size[1] * self.MULTIPLIER)
        return ImageTk.PhotoImage(image.resize(scaled_size))

    def _draw_room(self, room: RoomData) -> None:
        """Draw room content in depth order using scaled canvas coordinates."""
        self.room_canvas.delete("all")
        self.photo_images.clear()

        props = sorted(room.props, key=lambda item: item.depth, reverse=True)
        # characters = sorted(room.characters, key=lambda item: item.depth, reverse=True)

        for index, prop in enumerate(props):
            image = self.get_prop_image(prop)
            self.photo_images.append(image)
            corrected_position = (prop.position[0] * self.MULTIPLIER, prop.position[1] * self.MULTIPLIER)
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

    def _change_room(self, new_room: str) -> None:
        """Switch the preview and content tree to the chosen room."""
        # self._refresh_tree()
        self._draw_room(self.room_data[new_room])

    # def _canvas_press(self, event: Event) -> None:
    #     """Select the topmost tagged item and begin dragging movable content."""
    #     self.drag_origin = (event.x, event.y)

    # def _canvas_drag(self, event: Event) -> None:
    #     """Move the selected prop or character in room-coordinate increments."""
    #     selected_item = "bank"
    #     if self.drag_origin is None or selected_item is None:
    #         return
    #     kind, index = self.selection
    #     if kind not in {"props", "characters"}:
    #         return
    #     delta_x = round((event.x - self.drag_origin[0]) / (VIEW_SCALE * self.scale))
    #     delta_y = round((event.y - self.drag_origin[1]) / (VIEW_SCALE * self.scale))
    #     target = self.drag_position[0] + delta_x, self.drag_position[1] + delta_y
    #     self._set_content_position(kind, index, target)

    # def _canvas_release(self, event: Event) -> None:
    #     """Finish a drag and refresh the tree and form with the final position."""
    #     if self.selection is not None:
    #         kind, index = self.selection
    #         if kind in {"props", "characters"} and self.drag_origin is not None and self.drag_position is not None:
    #             target = (
    #                 self.drag_position[0] + round((event.x - self.drag_origin[0]) / (VIEW_SCALE * self.scale)),
    #                 self.drag_position[1] + round((event.y - self.drag_origin[1]) / (VIEW_SCALE * self.scale)),
    #             )
    #             if target != getattr(self.room, kind)[index].position:
    #                 self._set_content_position(kind, index, target)
    #         self._refresh_tree()
    #         self.tree.selection_set(f"{self.selection[0]}:{self.selection[1]}")
    #         self._refresh_form()
    #     self.drag_origin = None
