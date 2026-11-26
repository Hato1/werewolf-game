from enum import Enum

import pygame as pg

from my_game.constants import DIALOGUE_ANTI_ALIAS, DIALOGUE_FONT_SIZE, SCREEN_SIZE
from my_game.core.logger import get_logger
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts
from my_game.werewolf.controllers.dialogue import Dialogue, Line
from my_game.werewolf.inputs import Action
from my_game.werewolf.room.characters import PLAYER, TEST_CHARACTER
from my_game.werewolf.room.props import BACKGROUND_TOWN_HALL
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData

logger = get_logger(__name__)


class Converser:
    BORDER = 4
    OUTLINE = "#b2972a"
    FILL = "sienna4"
    FONT = Fonts.PICO8.load(DIALOGUE_FONT_SIZE)

    def __init__(self, name, image: pg.Surface, *, is_player: bool = False, flipx: bool = False, flipy: bool = False):
        self.outline_loc = (0, 0)
        self.pic_loc = (0, 0)

        if is_player:
            self.outline_loc = SCREEN_SIZE
            self.pic_loc = (SCREEN_SIZE[0] - self.BORDER, SCREEN_SIZE[1] - self.BORDER)
        else:
            self.pic_loc = (image.get_size()[0] + self.BORDER, image.get_size()[1] + self.BORDER)
            self.outline_loc = (self.pic_loc[0] + self.BORDER, self.pic_loc[1] + self.BORDER)

        self.name = name
        self.surf = pg.transform.flip(image, flipx, flipy)
        self.rect = self.surf.get_rect(bottomright=self.pic_loc)

        self.outline_surf = pg.Surface(
            (self.surf.get_size()[0] + self.BORDER * 2, +self.surf.get_size()[1] + self.BORDER * 2)
        )
        self.outline_surf.fill(self.OUTLINE)
        self.outline_rect = self.outline_surf.get_rect(bottomright=self.outline_loc)

        self.background_surf = pg.Surface(self.surf.get_size())
        self.background_surf.fill(self.FILL)
        self.background_rect = self.background_surf.get_rect(bottomright=self.pic_loc)

        self.textbox_loc = (0, 0)
        self.text_loc = (0, 0)
        self.textbox_height = int(self.surf.get_size()[1] * 5 / 8)
        self.textbox_width = SCREEN_SIZE[0] - self.surf.get_size()[0] - self.BORDER * 2
        if is_player:
            self.textbox_loc = (0, SCREEN_SIZE[1])
        else:
            self.textbox_loc = (self.surf.get_size()[0] + self.BORDER * 2, self.textbox_height)

        self.textbox_surf = pg.Surface((self.textbox_width, self.textbox_height))
        self.textbox_surf.fill(self.FILL)
        self.textbox_rect = self.textbox_surf.get_rect(bottomleft=self.textbox_loc)

        self.line: Line | None = None
        self.line_surf: pg.Surface | None = None
        self.line_rect: pg.Rect | None = None

    def set_line(self, line: Line):
        self.line = line
        self.line_surf = pg.Font.render(
            self.FONT, line.dialogue, DIALOGUE_ANTI_ALIAS, pg.Color("White"), None, self.textbox_width - self.BORDER * 2
        )
        self.line_rect = self.line_surf.get_rect(topleft=self.textbox_rect.__getattribute__("topleft"))

    def draw(self, renderer):
        renderer(self.outline_surf, self.outline_rect, unlit=True)
        renderer(self.background_surf, self.background_rect, unlit=True)
        renderer(self.surf, self.rect, unlit=True)
        renderer(self.textbox_surf, self.textbox_rect, unlit=True)
        if self.line:
            renderer(self.line_surf, self.line_rect, unlit=True)


class DialogueView(State[WerewolfState, WerewolfTransitionData]):
    def __init__(self) -> None:
        super().__init__()
        self.transition_data: WerewolfTransitionData
        self.renderer: Renderer

        self.bg_bg_surf = pg.Surface(SCREEN_SIZE)
        self.bg_bg_surf.fill("grey20")
        self.bg_bg_rect = self.bg_bg_surf.get_rect(topleft=(0, 0))
        self.bg_surf: pg.Surface
        self.bg_rect: pg.Rect

        self.player: Converser
        self.talker: Converser

        self.dialogue: Dialogue

    def enter(self, transition_data: WerewolfTransitionData, renderer: Renderer):
        self.transition_data = transition_data
        self.renderer = renderer

        # backgrounds
        self.bg_surf = pg.transform.box_blur(BACKGROUND_TOWN_HALL.image.load(), 2)
        self.bg_rect = self.bg_surf.get_rect(topleft=(0, 0))

        # characters
        self.player = Converser("Player", PLAYER.image.load(), is_player=True, flipx=True)
        self.talker = Converser("Test Character", TEST_CHARACTER.image.load())

        # dialogue
        self.dialogue = Dialogue(self.player.name, self.talker.name)
        self.next_line()

    def next_line(self):
        if not self.dialogue:
            logger.error("No dialogue object")
            return
        line = self.dialogue.get_next_line()

        if not line:
            logger.error("No line returned")
        if line.name == self.player.name:
            self.player.set_line(line)
        elif line.name == self.talker.name:
            self.talker.set_line(line)
        else:
            logger.error("Invalid name: " + line.name)

    def handle_keyboard(self, actions: set[Enum]) -> None:
        if Action.UI_SELECT in actions:
            self.next_line()

    def handle_mouse(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.MOUSE_SELECT in actions:
            self.next_line()

    def handle_event(self, actions, event):
        self.handle_keyboard(actions)
        self.handle_mouse(actions, event)

    def update(self, dt, input_state):
        pass

    def draw(self, renderer, dt):
        renderer(self.bg_bg_surf, self.bg_bg_rect, unlit=True)
        renderer(self.bg_surf, self.bg_rect, unlit=True)
        self.player.draw(renderer)
        self.talker.draw(renderer)

    def exit(self):
        pass
