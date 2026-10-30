"""PyInstaller build script.

Running this script will create an executable for the current platform in the dist directory.
A build directory and a .spec file will also be created in the project root, but these can be
safely deleted after the build is complete.

It uses the program name and version from pyproject.toml to name the output files.

Requires Python 3.11+ due to tomllib usage. Pillow is required for converting PNG icons to
ICO and ICNS for Windows and Mac builds respectively.

Mac apps built on ARM Macs may not run on Intel Macs. The reverse should be ok as ARM Macs
can run x86_64 binaries via Rosetta2.

Data files not loaded via the Asset Manager / Importlib may fail to be included or found
unless configured correctly. This could be operating system or --onefile dependent.
Run the executable from the command line to see any error messages.

Pyinstaller Docs: https://pyinstaller.org/en/stable/usage.html
"""

import sys
import tomllib
from importlib.resources import files
from pathlib import Path

import PyInstaller.__main__ as pyinstaller  # type: ignore[import-untyped]

PLATFORM = sys.platform
if PLATFORM.startswith("darwin"):
    PLATFORM = "mac"
if PLATFORM.startswith("win"):
    PLATFORM = "win"

# Extract program name and version from pyproject.toml
with Path("pyproject.toml").open("rb") as f:
    pyproject = tomllib.load(f)

NAME = pyproject["project"]["name"]
VERSION = pyproject["project"]["version"]
ICON = f"{files(NAME) / 'assets' / 'icon.png'}"
if not Path(ICON).is_file():
    raise FileNotFoundError(f"Icon file not found: {ICON}")
HIDDEN_IMPORTS: list[str] = [
    # Add any hidden imports here.
]


def build() -> None:
    """Build the executable"""

    hidden_imports = [arg for item in HIDDEN_IMPORTS for arg in ("--hidden-import", item)]

    pyinstaller.run(
        [
            str(files(NAME) / "main.py"),
            # '--clean',
            *("-n", f"{NAME}-{VERSION}-{PLATFORM}"),
            # Onefile mode is not recommended due to long load times and antivirus issues.
            # Especially on MacOS where an app bundle is preferred.
            # '--onefile',
            "--windowed",
            "--noconfirm",
            *("--log-level", "WARN"),
            *hidden_imports,
            "--collect-data",
            NAME,
            "-i",
            ICON,
        ]
    )


if __name__ == "__main__":
    build()
