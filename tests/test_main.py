"""Test basic project functionality."""

import pytest


def test_game_import() -> None:
    """Check project imports successfully."""
    import my_game  # noqa: F401


@pytest.mark.filterwarnings("ignore:no fast renderer available")
def test_main_exists():
    """Check main function exists.

    This is required for web builds, which need to call main() to start the game.
    """
    from my_game.main import main

    assert callable(main)
