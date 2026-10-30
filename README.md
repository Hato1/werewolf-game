# 🎮 Beast of Temerev [Working Title]

A "point and click" style video game designed for the [2026 Transformation Game Jam](https://itch.io/jam/tf26) with the theme "Hidden".



## ✨ Features
* Available on Linux, Mac, Windows and Web.
* Controller support



## Installation

Install the latest version from the [releases](https://github.com/Hato1/werewolf-game/releases) page for your operating system.

Alternatively play directly in your browser [here](https://hato1.github.io/werewolf-game).



## 💻 Development environment setup
1. [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
2. Navigate to the project
```bash
cd your-project-folder/werewolf-game
```
3. Install pre-commit hooks.
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
> Now you can execute the game with simply `run-game`.

> 💡 Make sure your IDE is using the virtual environment created by UV.
> * VSCode should detect it automatically.
> * If not, manually select .venv.


## 🏗️ Automatic Builds

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

Good for testing and debugging builds.


### 🌐 Web Build (Pygbag)

> ⚠️ Warning:
> Web builds allow mobile users to play.  
Mobile users often do not have keyboards or mice.  
> Pygbag treats screen taps as left mouse clicks.

`uv run pygbag src/my_game`

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
