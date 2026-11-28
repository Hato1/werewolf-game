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

from dataclasses import dataclass

from my_game.werewolf.assets import DialogueFile


@dataclass
class Line:
    name: str
    dialogue: str
    options: list[str]
    done: bool = False


@dataclass
class Node:
    title: str
    lines: list


class DialogueParser:
    unique_id = None
    char_id = None
    npc_id = None
    script = None  # array of messages
    responses = None  # optional array of responses to load new dialogues or end current one

    def __find_read_node(self, dialogue_file: DialogueFile, title: str) -> Node:
        dialogue = dialogue_file.load()

        lines = dialogue.split("\n")
        node = Node(title, [])
        in_text = False

        for line in lines:
            if not in_text and line.strip()[:7] == "title: " and line[7:].strip().lower() == title.lower():
                in_text = True
            elif in_text:
                if line.strip() == "---" or line.strip() == "":
                    continue
                elif line.strip() == "===":
                    break
                elif line.strip()[:2] == "->":
                    split_index = 0
                    if line.count(":") > 0:
                        split_index = line.index(":")
                    else:
                        split_index = line.index(">")

                    if len(node.lines[len(node.lines) - 1].options) > 0:
                        node.lines[len(node.lines) - 1].options.append(line[split_index + 1 :].strip())
                    else:
                        line_node = Line("", "", [line[split_index + 1 :].strip()])
                        node.lines.append(line_node)
                else:
                    colon_index = line.index(":")
                    line_node = Line(line[:colon_index].strip(), line[colon_index + 1 :].strip(), list(""))
                    node.lines.append(line_node)
        return node

    def get_next_line(self, selected=-1) -> Line:

        if self.pos >= len(self.node.lines):
            line = Line("", "", [], done=True)
            return line

        line = self.node.lines[self.pos]
        if line.done:
            pass
        elif len(line.options) > 0:
            self.pos += 1
        else:
            self.pos += 1
        return line

    def __init__(self, char_id, npc_id, dialogue: DialogueFile):
        self.char_id = char_id
        self.npc_id = npc_id
        self.act = 1  # Will be updated when there are multiple phases
        # self.inventory = saved
        # self.knoweldge = saved
        self.Node: Node | None = None
        self.pos = 0
        self.node = self.__find_read_node(dialogue, "Start")

    # def write_text(self, screen: pg.Surface, text):
    #     anti_alias = True
    #     text_surface = self.FONT.render(text, anti_alias, pg.Color("magenta"))
