"""Tests for dynamically registering image assets."""

from enum import StrEnum
from pathlib import Path

from my_game.werewolf.assets import Images, populate_images_enum


def _fixture_enum() -> type[StrEnum]:
    class TempImages(StrEnum):
        KNOWN = "known.png"

    return TempImages


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_real_images_enum_is_populated_on_import() -> None:
    assert "SIGN1" in Images.__members__
    assert Images.SIGN1.value == "props/sign1.png"
    assert Images("props/sign1.png") is Images.SIGN1


def test_populating_real_images_enum_again_keeps_dynamic_attributes() -> None:
    assert populate_images_enum() == ()
    assert Images.SIGN1.value == "props/sign1.png"


def test_populate_images_enum_adds_missing_images(tmp_path: Path) -> None:
    image_enum = _fixture_enum()
    _touch(tmp_path / "known.png")
    _touch(tmp_path / "new.png")
    _touch(tmp_path / "sub/new.png")

    added = populate_images_enum(tmp_path, image_enum=image_enum)

    new_member = image_enum["NEW"]
    nested_member = image_enum["SUB_NEW"]

    assert set(added) == {"NEW", "SUB_NEW"}
    assert new_member.value == "new.png"
    assert nested_member.value == "sub/new.png"
    assert image_enum("sub/new.png") is nested_member
    assert {member.name for member in image_enum} == {"KNOWN", "NEW", "SUB_NEW"}


def test_populate_images_enum_is_idempotent(tmp_path: Path) -> None:
    image_enum = _fixture_enum()
    _touch(tmp_path / "another.png")

    assert populate_images_enum(tmp_path, image_enum=image_enum) == ("ANOTHER",)
    assert populate_images_enum(tmp_path, image_enum=image_enum) == ()


def test_populate_images_enum_ignores_non_images(tmp_path: Path) -> None:
    image_enum = _fixture_enum()
    _touch(tmp_path / "notes.txt")

    assert populate_images_enum(tmp_path, image_enum=image_enum) == ()
