from enum import Enum

import pygame as pg

from my_game.constants import DIALOGUE_ANTI_ALIAS, DIALOGUE_FONT_SIZE, SCREEN_SIZE
from my_game.core.logger import get_logger
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts
from my_game.werewolf.controllers.dialogue import DialogueParser, Line
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

        self.says = ""
        self.says_surf = pg.Surface((0, 0))
        self.says_rect = self.says_surf.get_rect()

        self.opt_1 = ""
        self.opt_1_surf = pg.Surface((0, 0))
        self.opt_1_rect = self.opt_1_surf.get_rect()

        self.opt_2 = ""
        self.opt_2_surf = pg.Surface((0, 0))
        self.opt_2_rect = self.opt_2_surf.get_rect()

        self.pos = 0

    def set_line(self, line: Line, pos):
        self.line = line
        self.pos = 0

        if self.name.strip() == line.name.strip():
            self.says = line.dialogue
            self.says_surf = pg.Font.render(
                self.FONT, self.says, DIALOGUE_ANTI_ALIAS, pg.Color("White"), None, self.textbox_width - self.BORDER * 2
            )
            self.says_rect = self.says_surf.get_rect(topleft=self.textbox_rect.__getattribute__("topleft"))
        else:
            self.says = ""

        self.display_option()

    def display_option(self):
        if self.name.strip() == "Player" and len(self.line.options) > 0:
            o1_color = pg.Color("White")
            o2_color = pg.Color("White")
            o1_adder = ""
            o2_adder = ""
            top_pos = self.pos
            if self.pos % 2 == 0:
                o1_color = pg.Color("Yellow")
                o1_adder = "   "
            else:
                o2_color = pg.Color("Yellow")
                top_pos -= 1
                o2_adder = "   "

            self.opt_1 = self.line.options[top_pos]
            if len(self.line.options) - 1 == top_pos:
                self.opt_2 = ""
            elif len(self.line.options) > top_pos:
                self.opt_2 = self.line.options[top_pos + 1]

            textbox_topleft = self.textbox_rect.__getattribute__("topleft")

            self.opt_1_surf = pg.Font.render(
                self.FONT,
                o1_adder + "* " + self.opt_1,
                DIALOGUE_ANTI_ALIAS,
                o1_color,
                None,
                self.textbox_width - self.BORDER * 2,
            )
            self.opt_1_rect = self.opt_1_surf.get_rect(topleft=textbox_topleft)

            self.opt_2_surf = pg.Font.render(
                self.FONT,
                o2_adder + "* " + self.opt_2,
                DIALOGUE_ANTI_ALIAS,
                o2_color,
                None,
                self.textbox_width - self.BORDER * 2,
            )
            self.opt_2_rect = self.opt_2_surf.get_rect(
                topleft=(textbox_topleft[0], int(textbox_topleft[1] + self.textbox_height / 2))
            )
        else:
            self.opt_1 = ""
            self.opt_2 = ""

    def change_option(self, *, down=True):
        if not self.line or len(self.line.options) <= 0:
            return
        elif self.pos > 0 and not down:
            self.pos -= 1
        elif self.pos < len(self.line.options) - 1 and down:
            self.pos += 1
        self.display_option()

    def draw(self, renderer):
        renderer(self.outline_surf, self.outline_rect, unlit=True)
        renderer(self.background_surf, self.background_rect, unlit=True)
        renderer(self.surf, self.rect, unlit=True)
        renderer(self.textbox_surf, self.textbox_rect, unlit=True)
        if self.line:
            renderer(self.says_surf, self.says_rect, unlit=True)
        if self.opt_1:
            renderer(self.opt_1_surf, self.opt_1_rect, unlit=True)
        if self.opt_2:
            renderer(self.opt_2_surf, self.opt_2_rect, unlit=True)


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

        self.dialogue_parser: DialogueParser

    def enter(self, transition_data: WerewolfTransitionData, renderer: Renderer):
        super().enter(transition_data, renderer)
        self.renderer = renderer

        # backgrounds
        self.bg_surf = pg.transform.box_blur(BACKGROUND_TOWN_HALL.image.load(), 2)
        self.bg_rect = self.bg_surf.get_rect(topleft=(0, 0))

        # characters
        self.player = Converser("Player", PLAYER.image.load(), is_player=True, flipx=True)
        self.talker = Converser("Test Character", TEST_CHARACTER.image.load())

        # dialogue
        if not self.transition_data.dialogue:
            raise ValueError("No dialogue provided in transition data to dialogue state")
        self.dialogue_parser = DialogueParser(self.player.name, self.talker.name, self.transition_data.dialogue)
        self.next_line()

    def next_line(self):
        if not self.dialogue_parser:
            logger.error("No dialogue object")
            return
        line = self.dialogue_parser.get_next_line(selected=self.player.pos)

        if not line:
            logger.error("No line returned")
            return
        elif line.done:
            self.done = True
            self.next_state = WerewolfState(str(self.transition_data.previous_state))
            return

        self.player.set_line(line, 0)
        self.talker.set_line(line, 0)

    def handle_keyboard(self, actions: set[Enum]) -> None:
        if Action.UI_SELECT in actions or Action.RIGHT in actions:
            self.next_line()
        elif Action.UP in actions:
            self.player.change_option(down=False)
        elif Action.DOWN in actions:
            self.player.change_option(down=True)

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
