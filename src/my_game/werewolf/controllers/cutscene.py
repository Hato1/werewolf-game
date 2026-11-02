"""
Class Parent class for cutscenes

If we have cutscenes with dialogue, we may want to have a simple object that loads a cutscene
and the correct dialogue for it
In theory, we should not ever have to worry about having to load dialogue dynamically,
assuming the "dialogue" object represents the whole dialogue, rather than the text on an individual dialogue window
"""


class Cutscene:
    cutscene_id = None
    cutscene_name = None
    dialogue = None
