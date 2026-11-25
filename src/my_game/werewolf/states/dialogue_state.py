import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.renderer import Renderer
from my_game.core.state_manager import State
from my_game.werewolf.assets import Fonts
from my_game.werewolf.assets import Images
from my_game.werewolf.state_data import WerewolfState, WerewolfTransitionData
from my_game.werewolf.room.characters import *
from my_game.werewolf.room.props import BACKGROUND_TOWN_HALL
from my_game.werewolf.room.loaders import CharacterData
from my_game.werewolf.room.loaders import PropData
from my_game.werewolf.room.models import Prop, Character
from my_game.constants import SCREEN_SIZE

class Dialogue(State[WerewolfState, WerewolfTransitionData]):
    TITLE_FONT_SIZE = 60 // 2
    MENU_BUTTON_OFFSET_Y = 200 // 2
    OUTLINE = "#b2972a"
    FILL = "sienna4"
    BORDER = 4



    def __init__(self) -> None:
        super().__init__()

        self.transition_data: WerewolfTransitionData | None = None
        self.renderer: Renderer | None = None

        self.bg_bg_surf = pg.Surface(SCREEN_SIZE)
        self.bg_bg_surf.fill("grey20")
        self.bg_bg_rect = self.bg_bg_surf.get_rect(topleft=(0,0))
        self.bg_surf: pg.Surface | None = None
        self.bg_rect: pg.Rect | None = None

        self.player_surf: pg.Surface | None = None
        self.player_rect: pg.Rect | None = None
        self.play_ol_surf: pg.Surface | None = None
        self.play_ol_rect: pg.Rect | None = None
        self.play_bg_surf: pg.Surface | None = None
        self.play_bg_rect: pg.Rect | None = None

        self.talker_surf: pg.Surface | None = None
        self.talker_rect: pg.Rect | None = None
        self.talk_ol_surf: pg.Surface | None = None
        self.talk_ol_rect: pg.Rect | None = None
        self.talk_bg_surf: pg.Surface | None = None
        self.talk_bg_rect: pg.Rect | None = None


    def enter(self, transition_data: WerewolfTransitionData, renderer: Renderer):
        self.transition_data = transition_data
        self.renderer = renderer

        self.bg_surf = pg.transform.box_blur(BACKGROUND_TOWN_HALL.image.load(), 2)
        self.bg_rect = self.bg_surf.get_rect(topleft=(0,0))

        #player
        self.player_surf = pg.transform.flip(PLAYER.image.load(), True, False)
        self.player_rect = self.player_surf.get_rect(bottomright=(SCREEN_SIZE[0]-self.BORDER, SCREEN_SIZE[1]-self.BORDER))

        self.play_ol_surf = pg.Surface((self.player_surf.get_size()[0] + self.BORDER*2, + self.player_surf.get_size()[1] + self.BORDER*2))
        self.play_ol_surf.fill(self.OUTLINE)
        self.play_ol_rect = self.play_ol_surf.get_rect(bottomright=SCREEN_SIZE)

        self.play_bg_surf = pg.Surface(self.player_surf.get_size())
        self.play_bg_surf.fill(self.FILL)
        self.play_bg_rect = self.play_bg_surf.get_rect(bottomright=(SCREEN_SIZE[0]-self.BORDER, SCREEN_SIZE[1]-self.BORDER))

        self.play_talk_surf = pg.Surface((SCREEN_SIZE[0]-self.play_ol_surf.get_size()[0], self.player_surf.get_size()[1]*5/8))
        self.play_talk_surf.fill(self.FILL)
        self.play_talk_rect = self.play_talk_surf.get_rect(topright=(SCREEN_SIZE[0], 0))

        #talker
        self.talker_surf = TEST_CHARACTER.image.load()
        self.talker_rect = self.talker_surf.get_rect(topleft=(self.BORDER,self.BORDER))

        self.talk_ol_surf = pg.Surface((self.talker_surf.get_size()[0] + self.BORDER*2, + self.talker_surf.get_size()[1] + self.BORDER*2))
        self.talk_ol_surf.fill(self.OUTLINE)
        self.talk_ol_rect = self.talk_ol_surf.get_rect(topleft=(0,0))

        self.talk_bg_surf = pg.Surface(self.talker_surf.get_size())
        self.talk_bg_surf.fill(self.FILL)
        self.talk_bg_rect = self.talk_bg_surf.get_rect(topleft=(self.BORDER,self.BORDER))

        self.talk_talk_surf = pg.Surface((SCREEN_SIZE[0]-self.talk_ol_surf.get_size()[0], self.talker_surf.get_size()[1]*5/8))
        self.talk_talk_surf.fill(self.FILL)
        self.talk_talk_rect = self.talk_talk_surf.get_rect(bottomleft=(0, SCREEN_SIZE[1]))

    def handle_event(self, actions, event):
        return super().handle_event(actions, event)

    def update(self, dt, input_state):
        return super().update(dt, input_state)

    def draw(self, renderer, dt):
        renderer(self.bg_bg_surf, self.bg_bg_rect, unlit=True)
        renderer(self.bg_surf, self.bg_rect, unlit=True)
        renderer(self.play_ol_surf, self.play_ol_rect, unlit=True)
        renderer(self.talk_ol_surf, self.talk_ol_rect, unlit=True)
        renderer(self.play_bg_surf, self.play_bg_rect, unlit=True)
        renderer(self.talk_bg_surf, self.talk_bg_rect, unlit=True)
        renderer(self.player_surf, self.player_rect, unlit=True)
        renderer(self.talker_surf, self.talker_rect, unlit=True)
        renderer(self.play_talk_surf, self.play_talk_rect, unlit=True)
        renderer(self.talk_talk_surf, self.talk_talk_rect, unlit=True)


    def exit():
        pass