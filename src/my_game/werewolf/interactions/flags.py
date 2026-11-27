"""Runtime game flags used by interaction conditions and effects."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Self


@dataclass
class Flags:
    """Mutable flag values for a play session.

    Story flags used so far include ``woods_body_found`` and
    ``mayor_told_suspect``. Interaction bookkeeping flags use an internal
    prefix so they cannot collide with story flags.
    """

    values: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, values: Mapping[str, bool] | None = None) -> Self:
        """Create flags from a saved or transition payload."""
        return cls(dict(values or {}))

    def get(self, flag: str) -> bool:
        """Return whether ``flag`` is set."""
        return self.values.get(flag, False)

    def set(self, flag: str, *, value: bool) -> None:
        """Set ``flag`` to ``value``."""
        self.values[flag] = value

    def as_dict(self) -> dict[str, bool]:
        """Return a copy suitable for state transition data."""
        return dict(self.values)
