"""Registry for looking up room definitions by stable ID.

IDs are kept as strings so interaction definitions can cross-reference rooms
without importing the room modules that define them (which would be circular).
"""

from my_game.core.logger import get_logger
from my_game.werewolf.room import rooms
from my_game.werewolf.room.loaders import CharacterData, RoomData

logger = get_logger(__name__)


def _build_room_registry() -> dict[str, RoomData]:
    """Index public room definitions by explicit ID, falling back to their constant name."""
    registry: dict[str, RoomData] = {}
    for name, room in vars(rooms).items():
        if name.startswith("_") or not isinstance(room, RoomData):
            continue
        room_id = room.id or name
        if room_id in registry and registry[room_id] != room:
            logger.warning("Duplicate room ID.", room_id=room_id, definition=name)
        registry[room_id] = room
    return registry


def _build_character_registry() -> dict[str, CharacterData]:
    """Index public character definitions by explicit ID, falling back to their constant name."""
    registry: dict[str, CharacterData] = {}

    rooms = list(_ROOMS.values())
    characters = [character for room in rooms for character in room.characters]

    for character in characters:
        if character.id in registry and registry[character.id] != character:
            logger.warning("Duplicate character ID.", character_id=character.id, definition=character.name)
        registry[character.id] = character
    return registry


_ROOMS = _build_room_registry()
_CHARACTERS = _build_character_registry()


def get_room(room_id: str) -> RoomData:
    """Return the room definition registered under ``room_id``."""
    try:
        return _ROOMS[room_id]
    except KeyError:
        logger.error("Unknown room ID.", room_id=room_id, available=sorted(_ROOMS))
        raise


def get_character(character_id: str) -> CharacterData:
    """Return the character definition registered under ``character_id``."""
    try:
        return _CHARACTERS[character_id]
    except KeyError:
        logger.error("Unknown character ID.", character_id=character_id, available=sorted(_CHARACTERS))
        raise
