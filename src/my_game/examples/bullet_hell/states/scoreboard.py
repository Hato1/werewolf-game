# Highest score should be 100 seconds. I have achieved this score.
from enum import Enum, auto
from typing import NamedTuple

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.examples.bullet_hell.assets import Fonts
from my_game.examples.bullet_hell.inputs import Action
from my_game.examples.bullet_hell.state_data import BulletHellState, BulletHellTransitionData


class SubState(Enum):
    VIEWING = auto()
    NEW_HIGHSCORE = auto()


class ScoreEntry(NamedTuple):
    name: str
    score: float


DEFAULT_SCORES: list[ScoreEntry] = [
    ScoreEntry("hat", 9.999),
    ScoreEntry("cat", 9.00),
    ScoreEntry("rat", 7.50),
    ScoreEntry("mat", 6.00),
    ScoreEntry("sat", 4.50),
    ScoreEntry("vat", 3.00),
    ScoreEntry("kat", 2.00),
    ScoreEntry("pat", 1.00),
]


class Scoreboard(State[BulletHellState, BulletHellTransitionData]):
    BIGFONT = Fonts.PICO8.load(12)
    FONT = Fonts.PICO8.load(6)
    UI_OFFSET = 5  # Pixels from the edge of the screen to draw UI elements.

    def __init__(self):
        super().__init__()
        self.scores: list[ScoreEntry] = DEFAULT_SCORES.copy()
        self.player_name: list[str] = ["a", "a", "a"]
        self.current_score: float
        self.cursor_position: int
        self.sub_state: SubState

    def enter(
        self,
        surface_rect: pg.Rect,
        transition_data: BulletHellTransitionData,
    ):
        super().enter(surface_rect, transition_data=transition_data)
        self.current_score = transition_data.score
        if self.current_score == 0.0:
            print("No score found in persistent data; defaulting to 0.")

        # Determine if this is a new high score.
        if any(self.current_score > entry.score for entry in self.scores):
            self.sub_state = SubState.NEW_HIGHSCORE
        else:
            self.sub_state = SubState.VIEWING

        self.cursor_position = 0

    def advance_cursor(self, n: int = 1):
        self.cursor_position = min(2, max(0, (self.cursor_position + n)))

    def set_char_at_cursor(self, character: str):
        if len(character) != 1:
            raise ValueError("Character must be a single character.")
        self.player_name[self.cursor_position] = character.lower()

    def enter_score(self):
        name_str = "".join(self.player_name)
        new_entry = ScoreEntry(name_str, self.current_score)
        self.scores.append(new_entry)
        self.scores.sort(key=lambda entry: entry.score, reverse=True)
        self.scores.pop()  # Keep only top scores.
        self.sub_state = SubState.VIEWING

    def change_character(self, delta: int):
        """Change the character at the cursor position by delta in the alphabet."""
        current_char = self.player_name[self.cursor_position]
        if current_char == " ":
            current_index = -1  # Treat space as before 'a'.
        else:
            current_index = ord(current_char) - ord("a")

        new_index = (current_index + delta) % 26  # Wrap around alphabet.
        new_char = chr(ord("a") + new_index)
        self.set_char_at_cursor(new_char)

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if self.sub_state == SubState.VIEWING:
            if Action.UI_SELECT in actions:
                self.done = True
                self.next_state = BulletHellState.MAIN_MENU

        elif self.sub_state == SubState.NEW_HIGHSCORE:
            if Action.LEFT in actions:
                self.advance_cursor(-1)
            if Action.RIGHT in actions:
                self.advance_cursor(1)
            if Action.DOWN in actions:
                self.change_character(1)
            if Action.UP in actions:
                self.change_character(-1)
            if Action.UI_SELECT in actions:
                self.enter_score()

        else:
            raise ValueError(f"Unhandled sub-state: {self.sub_state}")

    def update(self, surface_rect, dt, input_state: InputState) -> None:
        pass

    def draw_title(self, surface: pg.Surface):
        anti_alias = True
        title_surf = self.BIGFONT.render("high scores", anti_alias, pg.Color("white"))
        title_rect = title_surf.get_rect(midtop=(surface.get_rect().centerx, self.UI_OFFSET))
        surface.blit(title_surf, title_rect)
        return title_rect.bottom + self.UI_OFFSET

    def draw_score(self, surface: pg.Surface, top_y: int, entry: ScoreEntry, position: int, *, highlight: bool = False):
        blink_frequency = 500  # milliseconds
        blink_duration = 25  # milliseconds
        if highlight and pg.time.get_ticks() % blink_frequency < blink_duration:
            return  # Skip drawing to create blink effect.

        color = pg.Color("yellow") if highlight else pg.Color("white")
        anti_alias = True
        entry_surf = self.FONT.render(f"{position + 1}. {entry.name} - {entry.score:.2f}", anti_alias, color)
        x = surface.get_rect().centerx
        y = top_y + position * (self.FONT.get_height() + self.UI_OFFSET)
        entry_rect = entry_surf.get_rect(midtop=(x, y))
        surface.blit(entry_surf, entry_rect)

    def draw_scores(self, surface: pg.Surface, top_y: int):
        # TODO: Draw arrows above/below the current character in the name entry when in NEW_HIGHSCORE sub-state.
        user_score_drawn = False
        for i, entry in enumerate(self.scores):
            if self.sub_state == SubState.NEW_HIGHSCORE:
                if not user_score_drawn and self.current_score > entry.score:
                    user_score = ScoreEntry("".join(self.player_name), self.current_score)
                    self.draw_score(surface, top_y, user_score, i, highlight=True)
                    user_score_drawn = True
            if i + user_score_drawn < len(self.scores):
                self.draw_score(surface, top_y, entry, i + user_score_drawn)

    def draw_prompt(self, surface):
        match self.sub_state:
            case SubState.VIEWING:
                prompt = "press enter to continue"
            case SubState.NEW_HIGHSCORE:
                prompt = "new highscore! enter name"
            case _:
                raise ValueError(f"Unhandled sub-state: {self.sub_state}")
        anti_alias = True
        prompt_surf = self.FONT.render(prompt, anti_alias, pg.Color("yellow"))
        prompt_rect = prompt_surf.get_rect(
            midbottom=(surface.get_rect().centerx, surface.get_height() - self.UI_OFFSET)
        )
        surface.blit(prompt_surf, prompt_rect)

    def draw(self, surface, dt):
        surface.fill(pg.Color("black"))
        top_y = self.draw_title(surface)
        self.draw_scores(surface, top_y)
        self.draw_prompt(surface)
