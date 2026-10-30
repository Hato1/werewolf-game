import pytest

from my_game.examples.bullet_hell import assets
from my_game.examples.bullet_hell.assets import Levels, Sounds


def test_sound_placeholder_has_clear_missing_asset_error() -> None:
    with pytest.raises(FileNotFoundError, match=r"explosion\.wav"):
        Sounds.EXPLOSION.load()


def test_level_placeholder_has_clear_missing_asset_error() -> None:
    with pytest.raises(FileNotFoundError, match=r"level_1\.json"):
        Levels.LEVEL_1.load()


def test_level_load_returns_resource_text(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    level_text = '{"name": "example"}'
    (tmp_path / "level_1.json").write_text(level_text, encoding="utf-8")
    monkeypatch.setattr(assets, "LEVELS_PATH", tmp_path)

    assert Levels.LEVEL_1.load() == level_text
