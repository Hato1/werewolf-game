import sys
from enum import Enum

import pygame as pg

from my_game.constants import MENU_ANTI_ALIAS, MENU_FONT_SIZE, SCREEN_SIZE
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
        mask_rects = pg.mask.from_surface(self.image).get_bounding_rects()
        self.hitbox = mask_rects[0].copy() if mask_rects else pg.Rect(0, 0, 0, 0)
        for mask_rect in mask_rects[1:]:
            self.hitbox = self.hitbox.union(mask_rect)
        self.font = font
        self.next_state = next_state

    def draw(self, renderer: Renderer, *, x_offset: int = 0, y_offset: int = 0, selected: bool) -> None:
        self.rect = self.image.get_rect(topleft=(x_offset, y_offset))
        renderer(self.selected_image if selected else self.image, self.rect, unlit=True)

    def collidepoint(self, pos) -> bool:
        """Use the smallest rect containing the visible pixels as the click area."""
        local_pos = (pos[0] - self.rect.x, pos[1] - self.rect.y)
        return bool(self.hitbox.collidepoint(local_pos))


def _extend_surface_edges(surface: pg.Surface, margin_x: int, margin_y: int | None = None) -> pg.Surface:
    """Add a margin by repeating edge pixels, keeping the original artwork unscaled."""
    if margin_y is None:
        margin_y = margin_x
    width, height = surface.get_size()
    extended = pg.Surface((width + 2 * margin_x, height + 2 * margin_y), pg.SRCALPHA)
    extended.blit(surface, (margin_x, margin_y))

    if margin_x:
        left = pg.transform.scale(surface.subsurface((0, 0, 1, height)), (margin_x, height))
        right = pg.transform.scale(surface.subsurface((width - 1, 0, 1, height)), (margin_x, height))
        extended.blit(left, (0, margin_y))
        extended.blit(right, (margin_x + width, margin_y))

    if margin_y:
        top = pg.transform.scale(surface.subsurface((0, 0, width, 1)), (width, margin_y))
        bottom = pg.transform.scale(surface.subsurface((0, height - 1, width, 1)), (width, margin_y))
        extended.blit(top, (margin_x, 0))
        extended.blit(bottom, (margin_x, margin_y + height))

    if margin_x and margin_y:
        corners = (
            ((0, 0), (0, 0)),
            ((width - 1, 0), (margin_x + width, 0)),
            ((0, height - 1), (0, margin_y + height)),
            ((width - 1, height - 1), (margin_x + width, margin_y + height)),
        )
        for source_pos, target_pos in corners:
            corner = pg.transform.scale(surface.subsurface((*source_pos, 1, 1)), (margin_x, margin_y))
            extended.blit(corner, target_pos)

    return extended


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
    PARALLAX_RESPONSE = 6.0
    # (image, maximum offset in pixels when the cursor is at a screen edge)
    PARALLAX_LAYERS_BEFORE_CLOUDS: tuple[tuple[Images, float], ...] = (
        (Images.BACKGROUND_NIGHTSKY, 2.0),
        (Images.BACKGROUND_FULLMOON, 4.0),
    )
    PARALLAX_LAYERS_AFTER_CLOUDS: tuple[tuple[Images, float], ...] = (
        (Images.BG_GEO2, 10.0),
        (Images.BG_GEO3, 14.0),
        (Images.TITLE_TEMEREV, 14.0),
        (Images.TITLE_TREE, 28.0),
    )
    PARALLAX_LAYERS = PARALLAX_LAYERS_BEFORE_CLOUDS + PARALLAX_LAYERS_AFTER_CLOUDS
    CLOUD_PARALLAX = 8.0
    PLAQUE_PARALLAX = (24.0, 14.0)
    TITLE_PARALLAX = 2.0

    def __init__(self) -> None:
        super().__init__()

        self.FONT = Fonts.PICO8.load(MENU_FONT_SIZE)
        self.TITLE_FONT = Fonts.BITMGOTHIC.load(self.TITLE_FONT_SIZE)

        # background
        self.total_dt = 0.0
        self.mouse_pos = (SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2)
        self.parallax = pg.Vector2()
        self.parallax_target = pg.Vector2()

        # Extend full-screen layers so shifting them never exposes the screen edges.
        margin = round(max(depth for _, depth in self.PARALLAX_LAYERS) + 2)
        self.parallax_surfaces = {
            image: _extend_surface_edges(image.load(), margin) for image, _ in self.PARALLAX_LAYERS
        }

        # Clouds tile horizontally, so only their vertical edges need extending.
        self.clouds = _extend_surface_edges(Images.BACKGROUND_CLOUDS.load(), 0, margin_y=margin)
        self.cloud_margin = margin
        self.clouds_rect = self.clouds.get_rect(topleft=(0, -margin))
        self.plaque = Images.PLAQUE1.load()

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

    def _set_parallax_target(self, mouse_pos: tuple[float, float]) -> None:
        """Convert a screen position into a normalized parallax target."""
        center_x, center_y = SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2
        self.parallax_target.update(
            max(-1.0, min(1.0, (center_x - mouse_pos[0]) / center_x)),
            max(-1.0, min(1.0, (center_y - mouse_pos[1]) / center_y)),
        )

    def _parallax_rect(self, surface: pg.Surface, depth: float) -> pg.Rect:
        center = (
            SCREEN_SIZE[0] / 2 + self.parallax.x * depth,
            SCREEN_SIZE[1] / 2 + self.parallax.y * depth,
        )
        return surface.get_rect(center=center)

    def _draw_parallax_layer(self, renderer: Renderer, surface: pg.Surface, depth: float) -> None:
        renderer(surface, self._parallax_rect(surface, depth))

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
            self.mouse_pos = event.pos
            self._set_parallax_target(event.pos)
            for i, button in enumerate(self.buttons):
                if button.collidepoint(event.pos):
                    self.button_index = i

    def update(self, dt: float, input_state: InputState) -> None:
        self.total_dt += dt

        # Ease towards the cursor-driven parallax target.
        blend = min(1.0, dt * self.PARALLAX_RESPONSE)
        self.parallax += (self.parallax_target - self.parallax) * blend

        # Scroll clouds left over time, with horizontal parallax folded into the scroll phase.
        scroll = (-self.total_dt * self.CLOUD_SPEED + self.parallax.x * self.CLOUD_PARALLAX) % self.clouds.get_width()
        self.clouds_rect.x = round(scroll)
        self.clouds_rect.y = round(self.parallax.y * self.CLOUD_PARALLAX - self.cloud_margin)

    def draw(self, renderer: Renderer, dt: float) -> None:
        # Draw second layer of clouds for seamless scrolling
        second_clouds_rect = self.clouds_rect.copy()
        second_clouds_rect.x -= self.clouds.get_width()

        for image, depth in self.PARALLAX_LAYERS_BEFORE_CLOUDS:
            self._draw_parallax_layer(renderer, self.parallax_surfaces[image], depth)

        renderer(self.clouds, self.clouds_rect)
        renderer(self.clouds, second_clouds_rect)

        for image, depth in self.PARALLAX_LAYERS_AFTER_CLOUDS:
            self._draw_parallax_layer(renderer, self.parallax_surfaces[image], depth)

        plaque_x = round(350 + self.parallax.x * self.PLAQUE_PARALLAX[0])
        plaque_y = round(self.parallax.y * self.PLAQUE_PARALLAX[1])
        renderer(self.plaque, self.plaque.get_rect(topleft=(plaque_x, plaque_y)))

        title_x = round(2 + self.parallax.x * self.TITLE_PARALLAX)
        title_y = round(2 + self.parallax.y * self.TITLE_PARALLAX)
        renderer(self.title_surface, self.title_surface.get_rect(topleft=(title_x, title_y)), unlit=True)

        for i, button in enumerate(self.buttons):
            button.draw(renderer, x_offset=plaque_x, y_offset=plaque_y, selected=self.button_index == i)
