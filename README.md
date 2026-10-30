# 🎮 Pygame Project Template

A template for building structured Pygame projects with modern Python tooling.

## Requirements and Support
* Python 3.14 or newer
* [UV](https://docs.astral.sh/uv/getting-started/installation/) for dependency management and project commands
* Automated release builds for Windows, macOS, and Linux via GitHub Actions

### ✨ Features:
* 🧠 State machine architecture (Main Menu, Level1, etc.)
* 🎨 Centralised asset loader
  * Works in packaged builds
  * Compatible with Pygbag web builds
* 🎮 Controller support
  * Hotplugging enabled
* 👾 Example playable game
* 📦 Dependency management with UV
* 🧹 Pre-commit hooks configured for:
  * Static type checking with Mypy
  * Linting with Ruff
* 🧪 Pytest with example tests
* 🏗️ PyInstaller configuration for:
  * Windows .exe
  * macOS .app
  * Linux binary
* 🚀 Automatic cross-platform builds via GitHub Actions
  * Build for Windows, Mac, and Linux - even if you don't own those systems

Note: Multiple controllers are not currently supported. Inputs from connected controllers are conflated.

## Getting Started
1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
2. Navigate to your project
```bash
cd your-project-folder
```
3. (Optional) Install pre-commit hooks.
```bash
uv run pre-commit install
```
4. Run the test game
```bash
uv run run-game
```


>####  💡 Optional: Activate the virtual environment  
> If you're tired of typing `uv run`, this will activate your environment for the session:
> ```bash
> # On macOS and Linux.
> source .venv/bin/activate
>
> # On Windows.
> .venv\Scripts\activate
> ```
> Now you can run the test game with simply `run-game`.

> 💡 Make sure your IDE is using the virtual environment created by UV.
> * VSCode should detect it automatically.
> * If not, manually select .venv.

## State Architecture

The state system lets you split a game into screens, such as a menu, a level, and a results screen. `StateManager` runs the game loop and keeps track of which screen is active.

### 1. Name Your Screens

A state ID is a name the manager uses to find a screen. Put the IDs and data shared between screens in a small module, such as `state_data.py`:

```python
from dataclasses import dataclass
from enum import StrEnum, auto

from my_game.core.state_manager import TransitionData


class GameState(StrEnum):
    MENU = auto()
    PLAYING = auto()
    RESULTS = auto()


@dataclass
class GameTransitionData(TransitionData):
    score: float = 0.0
```

`GameTransitionData` carries information from one screen to another. Add fields for anything your next screen needs. The manager fills in `previous_state` automatically.

### 2. Create a Screen

Each screen is a class that inherits from `State`. It handles events, updates the game, and draws the screen. Here is a small menu example:

```python
from enum import Enum, auto

import pygame as pg

from my_game.core.input_manager import InputState
from my_game.core.state_manager import State
from .state_data import GameState, GameTransitionData


class Action(Enum):
    START = auto()
    MOVE_LEFT = auto()


class Menu(State[GameState, GameTransitionData]):
    def handle_event(self, actions: set[Enum], event: pg.Event) -> None:
        if Action.START in actions:
            self.done = True
            self.next_state = GameState.PLAYING

    def update(self, surface_rect: pg.Rect, dt: float, input_state: InputState) -> None:
        if Action.MOVE_LEFT in input_state:
            print("Move left")

    def draw(self, surface: pg.Surface, dt: float) -> None:
        surface.fill("black")
```

When a player chooses to continue, set `done` to `True` and choose the next screen with `next_state`. In `update()`, `dt` is the time since the previous frame. Check held buttons with `action in input_state`; use `input_state.get_action_strength(action)` when analog strength matters.

The manager creates a new instance each time a screen is entered. Put setup that should happen on every visit in `enter()`. Override `exit()` if the screen needs to add data to `transition_data` before leaving.

### 3. Connect the Screens

Register each ID with its screen class. The class acts as a factory: the manager calls it to create a fresh screen. Set which screen opens first and which transition-data class to create:

```python
from my_game.core.state_manager import StateRegistry

from .game import Game
from .menu import Menu
from .results import Results
from .state_data import GameState, GameTransitionData


state_registry = StateRegistry(
    factories={
        GameState.MENU: Menu,
        GameState.PLAYING: Game,
        GameState.RESULTS: Results,
    },
    initial_state=GameState.MENU,
    transition_data_factory=GameTransitionData,
)
```

Keep this registry in one module that imports your screens. Screens can refer to the IDs in `state_data.py` without importing one another.

### 4. Start the Game Loop

After creating the Pygame window and input manager, pass them and the registry to `StateManager`:

```python
from my_game.core.state_manager import StateManager

manager = StateManager(screen, state_registry, input_manager, "My Game")
manager.main()
```

When a screen requests a change, the manager calls its `exit()`, records its ID in `previous_state`, creates the next screen, and passes it the transition data through `enter()`. The [bullet-hell example](src/my_game/examples/bullet_hell) shows the complete setup used by this project.


## 🏗️ Automatic Builds (Recommended)

After pushing changes to GitHub:

1. Create a Release
2. GitHub Actions will automatically:
    * Build Windows .exe
    * Build macOS .app
    * Build Linux binary
    * Build for web
    * Attach them all to the release
    * Deploy for web via Github Pages


## 🔧 Manual Builds

Use this if you need to debug or customize build settings.


### 🌐 Web Build (Pygbag)

> ⚠️ Warning:
> Web builds allow mobile users to play.  
Mobile users often do not have keyboards or mice.  
> Pygbag treats screen taps as left mouse clicks.

TODO: Add this section when Pygbag > 0.9.2 is stable.

---

### 🖥️ Windows EXE / macOS App / Linux Binary

Builds for the current OS and architecture (x86 / ARM).

> 💡 Rule of thumb:
Build on the oldest OS version you want to support.
Applications are usually forward-compatible, not backward-compatible.

Run:
```bash
uv run tools/build_app.py
```
This will:
1. Populate a `build` directory
2. Output the final executable in `dist`.


## ❓ FAQ
>### What is Pre-commit?
>A tool that runs checks (linting, formatting, typing) before each commit. After checking out the project it must be installed to run. This project is configured to run Mypy and Ruff checks by default.

>### What is a state system and why should I use it?
>A state system is a clean way to manage game screens like:
>* Main Menu
>* Settings
>* Level 1
>* Game Over  
>Without it, things can get confusing and it's easy not to properly set up, pack up and reset differents parts of a project. This can lead to bugs and difficult to maintain code.
