import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Self

if __import__("sys").platform == "emscripten":
    from platform import window  # type: ignore[attr-defined]

from my_game.core.renderer import suggest_resolution_scale

OPTIONS_FILE = Path("settings.json")


@dataclass
class Settings:
    """Represents the overall settings for the options menu."""

    lighting: bool = field(default_factory=lambda: sys.platform != "emscripten")
    fullscreen: bool = False
    resolution_scale: int = field(default_factory=suggest_resolution_scale)
    sound_effects: bool = True
    music: bool = True

    @classmethod
    def from_persistent_storage_desktop(cls) -> Self:
        try:
            with OPTIONS_FILE.open("r") as settings_file:
                saved_settings = json.loads(settings_file.read())
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError:
            return cls()
        else:
            s = saved_settings[0]
            return cls(**s)

    @classmethod
    def from_persistent_storage_emscripten(cls) -> Self:
        settings = window.localStorage.getItem(OPTIONS_FILE.stem)  # pyright: ignore[reportAttributeAccessIssue, reportPossiblyUnboundVariable]
        if settings:
            try:
                saved_settings = json.loads(settings)
            except json.JSONDecodeError:
                return cls()
            else:
                return cls(**saved_settings)
        return cls()

    @classmethod
    def from_persistent_storage(cls) -> Self:
        if sys.platform == "emscripten":
            return cls.from_persistent_storage_emscripten()
        else:
            return cls.from_persistent_storage_desktop()

    def to_persistent_storage_desktop(self) -> None:
        with OPTIONS_FILE.open("w") as settings_file:
            json.dump([asdict(self)], settings_file, indent=4)

    def to_persistent_storage_emscripten(self) -> None:
        window.localStorage.setItem(OPTIONS_FILE.stem, json.dumps(asdict(self)))  # pyright: ignore[reportAttributeAccessIssue, reportPossiblyUnboundVariable]

    def to_persistent_storage(self) -> None:
        if sys.platform == "emscripten":
            self.to_persistent_storage_emscripten()
        else:
            self.to_persistent_storage_desktop()
