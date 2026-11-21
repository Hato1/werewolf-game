from enum import Enum

import pygame as pg

from my_game.core.gl_renderer import GLRenderer
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class RenderTest(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        prompt_font = Fonts.PICO8.load(12)
        self.prompt = prompt_font.render(
            "Render Test - press Esc to return\nPress 1-6 to change active light\nPress again to stop editing a light\nUse Up/Down Arrow to change Z position",
            antialias=True,
            color=pg.Color("white"),
        )
        self.prompt_rect = self.prompt.get_rect(topleft=(16, 16))
        self.quit = False
        self.done = False
        self.background = Images.load(Images.TEST_CHURCH)
        self.light_mask = Images.load(Images.TEST_SHADOW)
        self.normal_map = Images.load(Images.TEST_CHURCH_NORMALS)
        self.light_z = 0.5
        self.i_hate_python: Renderer | None = None
        self.editing_light_index = 0
        self.previous_edit_index = -1
        self.active_edit = False

    @property
    def renderer(self):
        if self.i_hate_python is not None:
            return self.i_hate_python
        else:
            return None

    def draw(self, renderer: Renderer, dt: float) -> None:
        # renderer(background)
        # super().draw(renderer, dt)
        if self.renderer is None:
            self.i_hate_python = renderer
        renderer(self.background, renderer.rect, fit=True)
        renderer(self.light_mask, self.light_mask.get_rect(), draw_mode=1, fit=True)
        renderer(self.normal_map, self.normal_map.get_rect(), draw_mode=2, fit=True)
        renderer(self.prompt, self.prompt_rect, unlit=True)
        GLRenderer.light_z = self.light_z

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_CANCEL in actions:
            self.done = True
            self.next_state = WerewolfState.MAIN_MENU

        if Action.DEBUG_ROOM_1 in actions:
            self.change_lighting_index(0)
        elif Action.DEBUG_ROOM_2 in actions:
            self.change_lighting_index(1)
        elif Action.DEBUG_ROOM_3 in actions:
            self.change_lighting_index(2)
        elif Action.DEBUG_ROOM_4 in actions:
            self.change_lighting_index(3)
        elif Action.DEBUG_ROOM_5 in actions:
            self.change_lighting_index(4)
        elif Action.DEBUG_ROOM_6 in actions:
            self.change_lighting_index(5)

    def change_lighting_index(self, index):
        self.editing_light_index = index
        if self.previous_edit_index != self.editing_light_index:
            self.previous_edit_index = self.editing_light_index
            self.active_edit = True
        else:
            self.active_edit = False
            self.previous_edit_index = -1

    def update_light(self):
        if self.renderer is None:
            return
        if self.renderer.gl_renderer is None:
            return
        mouse_position_on_screen = (
            (pg.mouse.get_pos()[0] / self.renderer.gl_renderer.lit_surface.size[0]),
            (pg.mouse.get_pos()[1] / self.renderer.gl_renderer.lit_surface.size[1]),
        )
        self.renderer.gl_renderer.set_light_position(
            self.editing_light_index, mouse_position_on_screen[0], mouse_position_on_screen[1], self.light_z
        )
        self.renderer.gl_renderer.set_light_radius(self.editing_light_index, 0.5)

    def update(self, dt: float, input_state: InputState) -> None:
        # move mouse z position
        if Action.UP in input_state.held_actions:
            self.light_z += dt
        if Action.DOWN in input_state.held_actions:
            self.light_z -= dt

        self.light_z = max(-1, min(1, self.light_z))
        if self.active_edit:
            self.update_light()
