import random
from enum import Enum
from typing import Self

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from my_game.examples.bullet_hell.assets import Fonts, Images, UIElements
from my_game.examples.bullet_hell.inputs import Action
from my_game.examples.bullet_hell.state_data import BulletHellState, BulletHellTransitionData


def get_random_position_on_rect_perimeter(rect: pg.Rect) -> pg.Vector2:
    """Returns a random position on the perimeter of the given rect."""

    # Decide whether to pick a position on a horizontal or vertical edge.
    # This is weighted by the length of the edges to ensure uniform distribution.
    if random.random() < (rect.width / (rect.width + rect.height)):
        x = random.randrange(rect.left, rect.right)
        y = random.choice([rect.top, rect.bottom])
    else:
        x = random.choice([rect.left, rect.right])
        y = random.randrange(rect.top, rect.bottom)
    return pg.Vector2(x, y)


class Monster:
    """A simple monster class for demonstration purposes.

    Monsters start just outside the screen and move in a straight
    line so that they intersect with their target.

    Monster's never despawn; they just keep going indefinitely.
    That's ok though because they have negligible resource usage.

    """

    SPRITE = (
        Images.MONSTER_FRAME_0.load(),
        Images.MONSTER_FRAME_1.load(),
    )

    def __init__(self, position: pg.Vector2, direction: pg.Vector2, speed: float):
        self.position = position
        self.direction = direction
        self.speed = speed
        self.rect = self.SPRITE[0].get_rect(center=(self.position))

    @classmethod
    def create_monster(cls, screen_rect: pg.Rect, target: pg.Vector2) -> Self:
        """Create a monster with a default position, vector, and speed."""
        half_sprite_dims = cls.SPRITE[0].get_width() / 2, cls.SPRITE[0].get_height() / 2
        # Make sure enemies spawn just outside the screen.
        spawn_area = screen_rect.inflate(half_sprite_dims)
        position = get_random_position_on_rect_perimeter(spawn_area)
        # Aim the monster towards the target position.
        vector = target - position
        speed = random.uniform(0.05, 0.5)
        return cls(position, vector, speed)

    def update(self, dt: float):
        """Update the monster's position based on its speed and direction."""
        self.position += self.direction * self.speed * dt

    def draw(self, surface: pg.Surface, current_time: float):
        # Simple animation based on time and monster speed.
        sprite_index = int((current_time * self.speed * 10) % 2)
        sprite = self.SPRITE[sprite_index]
        self.rect = sprite.get_rect(center=(self.position))
        surface.blit(sprite, self.rect)


class Player:
    """A simple player class for demonstration purposes.

    The directional arrows or WASD keys control the players velocity instead of position.
    This gives the player a smoother, more 'slidey' movement experience.
    """

    SPRITE = Images.MONSTER_FRAME_1.load()
    INITIAL_HEALTH_CAPACITY = 3
    THRUST_SCALAR = 2  # How quickly the player accelerates.
    FRICTION = 0.05  # Percentage of speed lost each second.

    def __init__(self, position: pg.Vector2):
        self.position: pg.Vector2 = position
        self.velocity = pg.Vector2(0, 0)
        self.max_health = self.INITIAL_HEALTH_CAPACITY
        self.health = self.max_health
        self.rect = self.SPRITE.get_rect(center=(self.position))

    def increase_velocity(self, delta: pg.Vector2):
        if not delta:
            return
        delta = delta.clamp_magnitude(1) * self.THRUST_SCALAR
        self.velocity += delta

    def clamp_position(self, surface_rect: pg.Rect):
        """Keep the player within the bounds of the given rect."""
        half_width = self.rect.width / 2
        half_height = self.rect.height / 2
        x = pg.math.clamp(self.position.x, surface_rect.left + half_width, surface_rect.right - half_width)
        y = pg.math.clamp(self.position.y, surface_rect.top + half_height, surface_rect.bottom - half_height)
        # If clamping occurred, stop movement in that direction.
        if x != self.position.x:
            self.velocity.x = 0
            self.position.x = x
        if y != self.position.y:
            self.velocity.y = 0
            self.position.y = y

    def update(self, surface_rect: pg.Rect, dt: float):
        self.position += self.velocity * dt
        # Make friction dt-aware so deceleration is frame-rate independent.
        # Use exponential decay so that FRICTION represents the per-second
        # retention factor when dt is in seconds. For small dt this approximates
        # linear scaling but remains stable for variable frame times.
        self.velocity *= self.FRICTION**dt
        self.clamp_position(surface_rect)
        self.rect = self.SPRITE.get_rect(center=(self.position))

    def draw(self, surface):
        surface.blit(self.SPRITE, self.rect)


class Game(State[BulletHellState, BulletHellTransitionData]):
    DEFAULT_MONSTER_INTERVAL = 2  # Seconds between monster spawns.
    MONSTER_INTERVAL_DECREASE_RATE = 0.02  # Rate at which monster spawn interval decreases.
    MINIMUM_MONSTER_INTERVAL = 0.1  # Minimum seconds between monster spawns.

    UI_OFFSET = 5  # Pixels from the edge of the screen to draw UI elements.
    FONT = Fonts.PICO8.load(6)

    def __init__(self) -> None:
        super().__init__()
        self.monster_meter: float
        self.monster_interval: float
        self.monsters: list[Monster]
        self.player: Player
        self.score: float = 0.0

    def enter(
        self,
        surface_rect: pg.Rect,
        transition_data: BulletHellTransitionData,
    ) -> None:
        super().enter(surface_rect, transition_data=transition_data)
        self.monster_meter = 0
        self.monster_interval = self.DEFAULT_MONSTER_INTERVAL
        self.monsters = []
        self.player = Player(pg.Vector2(surface_rect.center))
        self.score = 0.0

    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.UI_SELECT in actions:
            self.done = True
            self.next_state = BulletHellState.SCOREBOARD

    def draw_healthbar(self, surface) -> None:
        """Draws the player's health as hearts in the top-left corner."""
        heart_full = UIElements.HEART_FULL.load()
        empty_heart = UIElements.HEART_EMPTY.load()

        for i in range(self.player.max_health):
            heart = heart_full if i < self.player.health else empty_heart
            surface.blit(heart, (self.UI_OFFSET + i * (heart.get_width() + self.UI_OFFSET), self.UI_OFFSET))

    def draw_score(self, surface: pg.Surface) -> None:
        """Draws the player's score in the top-right corner."""
        anti_alias = True
        score_surf = self.FONT.render(f"score: {self.score:.2f}", anti_alias, pg.Color("yellow"))
        score_rect = score_surf.get_rect(topright=(surface.get_width() - self.UI_OFFSET, self.UI_OFFSET))
        surface.blit(score_surf, score_rect)

    def update_monster_spawner(self, surface_rect: pg.Rect, dt: float) -> None:
        """Spawns monsters over time based on the monster meter and interval."""
        self.monster_meter += dt
        while self.monster_meter > self.monster_interval:
            new_monster = Monster.create_monster(surface_rect, self.player.position)
            self.monsters.append(new_monster)
            self.monster_meter -= self.monster_interval

    def update_player_movement(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        """Update player position based on input strength."""
        strength = input_state.get_action_strength
        movement = pg.Vector2(
            strength(Action.RIGHT) - strength(Action.LEFT),
            strength(Action.DOWN) - strength(Action.UP),
        )
        self.player.increase_velocity(movement)
        self.player.update(surface_rect, dt)

    def update_difficulty(self, dt: float) -> None:
        """Gradually increase game difficulty over time."""
        self.monster_interval -= self.MONSTER_INTERVAL_DECREASE_RATE * dt
        self.monster_interval = max(self.monster_interval, self.MINIMUM_MONSTER_INTERVAL)

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        self.update_monster_spawner(surface_rect, dt)
        self.update_player_movement(surface_rect, dt, input_state)

        # Iterate in reverse order to safely remove monsters while iterating
        for monster in self.monsters[::-1]:
            monster.update(dt)
            if monster.rect.colliderect(self.player.rect):
                self.player.health -= 1
                self.monsters.remove(monster)

        if self.player.health <= 0:
            self.done = True
            self.next_state = BulletHellState.SCOREBOARD

        self.update_difficulty(dt)

        # Score is time survived in seconds.
        self.score = (pg.time.get_ticks() / 1000.0) - self.start_time

    def draw(self, surface: pg.Surface, dt: float) -> None:
        surface.fill(pg.Color("gray"))
        for monster in self.monsters:
            monster.draw(surface, pg.time.get_ticks() / 1000.0)
        self.player.draw(surface)
        self.draw_healthbar(surface)
        self.draw_score(surface)

    def exit(self) -> BulletHellTransitionData:
        self.transition_data.score = self.score
        transition_data = super().exit()
        return transition_data
