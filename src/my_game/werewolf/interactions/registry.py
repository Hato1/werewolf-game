"""Registry for looking up room definitions by stable ID.

IDs are kept as strings so interaction definitions can cross-reference rooms
without importing the room modules that define them (which would be circular).
"""

from my_game.core.logger import get_logger
from my_game.werewolf.room import rooms
from my_game.werewolf.room.loaders import RoomData

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


_ROOMS = _build_room_registry()


def get_room(room_id: str) -> RoomData:
    """Return the room definition registered under ``room_id``."""
    try:
        return _ROOMS[room_id]
    except KeyError:
        logger.error("Unknown room ID.", room_id=room_id, available=sorted(_ROOMS))
        raise
