# """
# UI test sandbox. Formerly "ui", which will now be used to define the ui class
# """
#
# import pygame as pg
# import pygame_gui
#
# # ObjectID needed for referring to panels/buttons by ObjectID in theme file
# from pygame_gui.core import ObjectID
#
# from my_game.constants import SCREEN_SIZE
# from my_game.werewolf.assets import Fonts
#
# # UIButton and UIPanel needed for dynamically changing ObjectID to swap themes (like from human UI to werewolf UI)
#
# pg.init()
#
# window_surface = pg.display.set_mode(SCREEN_SIZE)
# background = pg.Surface(window_surface.get_size())
# background.fill("black")
#
# """
# Manager knows screen size, this can be used for scaling
# theme path helps keep a uniform style
# """
# manager = pygame_gui.UIManager(SCREEN_SIZE, theme_path="../assets/ui/ui_theme.json")
#
# ui_running = True
# ui_clock = pg.time.Clock()
#
#
# FONT = Fonts.PICO8.load(10)
#
# portrait_size = (100, 150)
# inventory_button_size = (100, 100)
# frame_size = (SCREEN_SIZE[0] - 10, 165)
#
# # portrait_image = pg.image.load(Images.load("player_portrait_wolf.png"))
#
# ui_frame = pygame_gui.elements.UIPanel(
#     relative_rect=pg.Rect((5, -165), frame_size),
#     manager=manager,
#     object_id=ObjectID(class_id="@frame_1", object_id="#ui"),
#     anchors={"left": "left", "bottom": "bottom"},
# )
#
# # Portrait can be a button to display a menu, if we want. Or to do fun little things when clicked.
# portrait = pygame_gui.elements.UIButton(
#     relative_rect=pg.Rect((5, -155), portrait_size),
#     manager=manager,
#     container=ui_frame,
#     object_id=ObjectID(class_id="@portrait", object_id="#ui_portrait"),
#     anchors={"left": "left", "bottom": "bottom"},
#     text="",
# )
#
# btn_inv_1 = pygame_gui.elements.UIButton(
#     relative_rect=pg.Rect((110, -105), inventory_button_size),
#     text="",
#     manager=manager,
#     container=ui_frame,
#     anchors={"left": "left", "bottom": "bottom"},
#     object_id=ObjectID(class_id="@inv_empty", object_id="#inv_empty"),
# )
#
# # btn_inv_1.image = UIElements.load("player_portrait_wolf.png")
#
# btn_inv_2 = pygame_gui.elements.UIButton(
#     relative_rect=pg.Rect((215, -105), inventory_button_size),
#     text="",
#     manager=manager,
#     container=ui_frame,
#     anchors={"left": "left", "bottom": "bottom"},
# )
# btn_inv_3 = pygame_gui.elements.UIButton(
#     relative_rect=pg.Rect((320, -105), inventory_button_size),
#     text="",
#     manager=manager,
#     container=ui_frame,
#     anchors={"left": "left", "bottom": "bottom"},
# )
# btn_inv_4 = pygame_gui.elements.UIButton(
#     relative_rect=pg.Rect((425, -105), inventory_button_size),
#     text="",
#     manager=manager,
#     container=ui_frame,
#     anchors={"left": "left", "bottom": "bottom"},
# )
#
# while ui_running:
#     # 60 FPS should be enough
#     time_delta = ui_clock.tick(60) / 1000.0
#
#     for event in pg.event.get():
#         match event.type:
#             case pg.QUIT:
#                 ui_running = False
#             case pygame_gui.UI_BUTTON_PRESSED:
#                 # Because the buttons are contained in the frame (#ui), objectID for empty inventory is: #ui.#inv_empty
#                 if event.ui_element == btn_inv_1:
#                     btn_inv_1.change_object_id(ObjectID(class_id="@inv_test", object_id="#inv_test"))
#                     print("btn_inv_1 pressed")
#                 elif event.ui_element == btn_inv_2:
#                     print("btn_inv_2 pressed")
#                 elif event.ui_element == btn_inv_3:
#                     print("btn_inv_3 pressed")
#                 elif event.ui_element == btn_inv_4:
#                     print("btn_inv_4 pressed")
#         manager.process_events(event)
#
#     manager.update(time_delta)
#
#     window_surface.blit(background, (0, 0))
#     manager.draw_ui(window_surface)  # update UI on screen
#
#     pg.display.update()
#
#
# """
# Functions for UI elements
# """
