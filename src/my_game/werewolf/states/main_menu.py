import sys
from enum import Enum

import pygame as pg

from my_game.constants import MENU_ANTI_ALIAS, MENU_FONT_SIZE
from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts, Images
from my_game.werewolf.inputs import Action
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData


class MainMenuButton:
    def __init__(self, font, image: Images, next_state: WerewolfState | None) -> None:
        self.image = image.load()
        self.selected_image = self.image.copy()
        self.selected_image.fill((255, 255, 0), special_flags=pg.BLEND_RGB_ADD)
        self.rect = self.image.get_rect()
        self.image_mask = pg.mask.from_surface(self.image)
        self.font = font
        self.next_state = next_state

    def draw(self, renderer: Renderer, *, x_offset: int = 0, selected: bool) -> None:
        self.rect = self.image.get_rect(topleft=(x_offset, 0))
        renderer(self.selected_image if selected else self.image, self.rect, unlit=True)

    def collidepoint(self, pos) -> bool:
        local_pos = (pos[0] - self.rect.x, pos[1] - self.rect.y)
        try:
            return bool(self.image_mask.get_at(local_pos))
        except IndexError:
            return False


def add_outline_to_image(
    image: pg.Surface, thickness: int, color: pg.Color, color_key: tuple = (255, 0, 255)
) -> pg.Surface:
    mask = pg.mask.from_surface(image)
    mask_surf = mask.to_surface(setcolor=color)
    mask_surf.set_colorkey((0, 0, 0))

    new_img = pg.Surface((image.get_width() + 2 * thickness, image.get_height() + 2 * thickness))
    new_img.fill(color_key)
    new_img.set_colorkey(color_key)

    for i in range(-thickness, thickness + 1):
        new_img.blit(mask_surf, (i + thickness, thickness))
        new_img.blit(mask_surf, (thickness, i + thickness))
    new_img.blit(image, (thickness, thickness))

    return new_img


class MainMenu(State[WerewolfState, WerewolfTransitionData]):
    TITLE_FONT_SIZE = 64
    CLOUD_SPEED = 5

    def __init__(self) -> None:
        super().__init__()

        self.FONT = Fonts.PICO8.load(MENU_FONT_SIZE)
        self.TITLE_FONT = Fonts.BITMGOTHIC.load(self.TITLE_FONT_SIZE)

        # background
        self.clouds = Images.BACKGROUND_CLOUDS.load()
        self.clouds_rect = self.clouds.get_rect()
        self.total_dt = 0.0
        self.mouse_pos = (0, 0)

        # title
        title = "Beast of \nTemerev"
        self.title_surface = self.TITLE_FONT.render(title, MENU_ANTI_ALIAS, pg.Color("gray70"))
        self.title_surface = add_outline_to_image(self.title_surface, 2, pg.Color("darkred"))
        self.title_rect = self.title_surface.get_rect(topleft=(5, 5))

        # buttons
        self.buttons = [
            MainMenuButton(self.FONT, Images.PLAQUE_START, WerewolfState.ROOM),
            MainMenuButton(self.FONT, Images.PLAQUE_LOAD, WerewolfState.RENDER_TEST),
            MainMenuButton(self.FONT, Images.PLAQUE_OPTIONS, WerewolfState.OPTIONS_MENU),
            MainMenuButton(self.FONT, Images.PLAQUE_CREDITS, WerewolfState.TEST_ROOM),
        ]
        if sys.platform != "emscripten":
            self.buttons.append(MainMenuButton(self.FONT, Images.PLAQUE_EXIT, None))
        self.button_index = 0

    def press_button(self) -> None:
        """Switch to the state of the currently selected button.

        If the button has no next state, quit the game.
        """
        self.done = True
        self.next_state = self.buttons[self.button_index].next_state
        if not self.next_state:
            self.quit = True

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.press_button()

        if Action.UP in actions:
            self.button_index = (self.button_index - 1) % len(self.buttons)

        if Action.DOWN in actions:
            self.button_index = (self.button_index + 1) % len(self.buttons)

        if Action.MOUSE_SELECT in actions:
            for button in self.buttons:
                if button.collidepoint(event.pos):
                    self.button_index = self.buttons.index(button)
                    self.press_button()

        if event.type == pg.MOUSEMOTION:
            for i, button in enumerate(self.buttons):
                if button.collidepoint(event.pos):
                    self.button_index = i

    def update(self, dt: float, input_state: InputState) -> None:
        self.total_dt += dt

        # Move clouds to the left over time
        self.clouds_rect.x = -self.total_dt * self.CLOUD_SPEED % self.clouds.get_width()

    def draw(self, renderer: Renderer, dt: float) -> None:
        # Draw second layer of clouds for seamless scrolling
        second_clouds_rect = self.clouds_rect.copy()
        second_clouds_rect.x -= self.clouds.get_width()

        renderer(Images.BACKGROUND_NIGHTSKY.load())
        renderer(Images.BACKGROUND_FULLMOON.load())
        renderer(self.clouds, self.clouds_rect)
        renderer(self.clouds, second_clouds_rect)
        renderer(Images.BG_GEO2.load())
        renderer(Images.BG_GEO3.load())
        renderer(Images.TITLE_TEMEREV.load())
        renderer(Images.TITLE_TREE.load())

        plaque_x_offset = 350
        plaque = Images.PLAQUE1.load()
        plaque_rect = plaque.get_rect(topleft=(plaque_x_offset, 0))
        renderer(plaque, plaque_rect)

        renderer(self.title_surface, self.title_rect, unlit=True)

        for i in range(len(self.buttons)):
            self.buttons[i].draw(renderer, x_offset=plaque_x_offset, selected=self.button_index == i)
