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

import sys
from dataclasses import dataclass
from pathlib import Path

from my_game.werewolf.assets import Fonts

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]


@dataclass
class Line:
    name: str
    dialogue: str
    done: bool = False


@dataclass
class Node:
    title: str
    lines: list


class Dialogue:
    FONT = Fonts.PICO8.load(6)
    unique_id = None
    char_id = None
    npc_id = None
    script = None  # array of messages
    responses = None  # optional array of responses to load new dialogues or end current one

    def __find_read_node(self, file: Path, title: str) -> Node:

        dialogue = ""
        if sys.platform == "emscripten":
            dialogue_file = window.localStorage.getItem(file.stem)
            print(dialogue_file)
        else:
            dialogue_file = Path.open(file)
            dialogue = dialogue_file.read()

        lines = dialogue.split("\n")
        node = Node(title, [])
        in_text = False

        for line in lines:
            if not in_text and line[:7] == "title: " and line[7:].strip().lower() == title.lower():
                in_text = True
            elif in_text:
                if line.strip() == "---" or line.strip() == "":
                    continue
                elif line.strip() == "===":
                    break
                else:
                    colon_index = line.index(":")
                    line_node = Line(line[:colon_index].strip(), line[colon_index + 1 :].strip())
                    node.lines.append(line_node)
        return node

    def get_next_line(self) -> Line:
        line = self.node.lines[self.pos]
        if line.done:
            pass
        if self.pos >= len(self.node.lines) - 1:
            line.done = True
        else:
            self.pos += 1
        return line

    def __init__(self, char_id, npc_id):
        self.char_id = char_id
        self.npc_id = npc_id
        self.act = 1  # Will be updated when there are multiple phases
        # self.inventory = saved
        # self.knoweldge = saved
        self.file = Path("src/my_game/werewolf/assets/dialogue/dialogue_test.yarn")
        self.Node: Node | None = None
        self.pos = 0
        self.node = self.__find_read_node(self.file, "Start")

    # def write_text(self, screen: pg.Surface, text):
    #     anti_alias = True
    #     text_surface = self.FONT.render(text, anti_alias, pg.Color("magenta"))
