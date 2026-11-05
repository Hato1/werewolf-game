"""dialogue class will handle dialogue functionality with characters
What it will do:
- Write dialogue to text area during NPC interactions
- Write narration to text area while exploring
- Write narration to text area during cutscenes (when applicable)

We will likely need
1) unique ID
2) Character ID - one for each involved character
3) NPC Name - one for each involved character
4) Dialogue tree - represents entire dialogue and each branch player can take
5) initial dialogue state
6) flags and accessors to track which options are available
-- potentially different for each dialogue, so we might just store these in a dictionary or something

Ideally, this should be a parent class for dialogues between the player and NPCs.
I expect that this will be a big chunk of the game and that some dialogues might become relatively complex.
Ideally, by figuring out which components and behaviors are common to all dialogues, we can cut down on dev time a bit
by reducing redundancies where possible.
"""

from my_game.werewolf.assets import Fonts


class Dialogue:
    FONT = Fonts.PICO8.load(6)
    unique_id = None
    char_id = None
    npc_id = None
    script = None  # array of messages
    responses = None  # optional array of responses to load new dialogues or end current one

    def __init__(self, unique_id, char_id, npc_id, text, responses):
        self.unique_id = unique_id
        self.char_id = char_id
        self.npc_id = npc_id
        self.script = text
        self.responses = responses

    # def write_text(self, screen: pg.Surface, text):
    #     anti_alias = True
    #     text_surface = self.FONT.render(text, anti_alias, pg.Color("magenta"))
