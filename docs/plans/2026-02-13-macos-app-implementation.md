# macOS Menu Bar App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pivot PyJockie from a Docker-based deployment to a self-contained macOS menu bar app that bundles librespot, ffmpeg, and the Discord bot.

**Architecture:** A rumps-based menu bar app runs on the main thread, managing a librespot subprocess and a Discord bot on a background thread. Audio flows through a FIFO pipe from librespot → ffmpeg → discord.py. Config is stored in `~/.config/pyjockie/config.json`.

**Tech Stack:** rumps (menu bar), py2app (bundling), discord.py (bot), aiohttp (event receiver), subprocess (librespot/ffmpeg management)

---

### Task 1: Add rumps and py2app to dependencies

**Files:**
- Modify: `bot/requirements.txt`

**Step 1: Update requirements.txt**

Replace contents of `bot/requirements.txt` with:

```
discord.py[voice]>=2.3.0
PyNaCl>=1.5.0
aiohttp>=3.9.0
rumps>=0.4.0
py2app>=0.28.0
```

**Step 2: Install new dependencies**

Run: `uv pip install -r bot/requirements.txt`
Expected: All packages install successfully

**Step 3: Verify rumps works**

Run: `.venv/bin/python -c "import rumps; print(rumps.__version__)"`
Expected: Prints version number without error

**Step 4: Commit**

```bash
git add bot/requirements.txt
git commit -m "build: add rumps and py2app dependencies"
```

---

### Task 2: Create config module for Discord token management

**Files:**
- Create: `bot/config.py`

**Step 1: Write the config module**

Create `bot/config.py`:

```python
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "pyjockie"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from ~/.config/pyjockie/config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save config to ~/.config/pyjockie/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    log.info("Config saved to %s", CONFIG_FILE)


def get_discord_token() -> str | None:
    """Get Discord token from config, env var, or None."""
    # Env var takes precedence (for dev)
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        return token
    config = load_config()
    return config.get("discord_token")


def set_discord_token(token: str) -> None:
    """Save Discord token to config file."""
    config = load_config()
    config["discord_token"] = token
    save_config(config)
```

**Step 2: Verify it works**

Run: `.venv/bin/python -c "from bot.config import load_config; print(load_config())"`
Expected: Prints `{}` (empty dict, no config yet)

**Step 3: Commit**

```bash
git add bot/config.py
git commit -m "feat: add config module for persistent token storage"
```

---

### Task 3: Refactor bot.py to accept parameters instead of reading env vars

**Files:**
- Modify: `bot/bot.py`

The bot currently reads `FIFO_PATH` and `EVENT_PORT` from env vars at module level. We need to make these configurable so the app can pass them in.

**Step 1: Refactor bot.py**

Change `bot/bot.py` so that `FIFO_PATH` and `EVENT_PORT` are set via a `configure()` function instead of module-level env reads. The key changes:

1. Replace the module-level env var reads with module-level defaults
2. Add a `configure(fifo_path, event_port)` function
3. The rest of the file stays the same

Replace lines 1-16 of `bot/bot.py` with:

```python
import logging
import os

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from audio import SpotifyAudioSource
from state import AppState, TrackInfo, state

log = logging.getLogger(__name__)

# Defaults — overridden by configure()
FIFO_PATH = os.environ.get("FIFO_PATH", "/tmp/pyjockie.fifo")
EVENT_PORT = int(os.environ.get("EVENT_PORT", "8080"))


def configure(fifo_path: str | None = None, event_port: int | None = None):
    """Set runtime configuration before bot starts."""
    global FIFO_PATH, EVENT_PORT
    if fifo_path is not None:
        FIFO_PATH = fifo_path
    if event_port is not None:
        EVENT_PORT = event_port
```

Everything else in `bot.py` stays exactly the same — the `FIFO_PATH` and `EVENT_PORT` globals are already referenced by the existing code.

**Step 2: Verify bot still works standalone**

Run: `source .venv/bin/activate && DISCORD_TOKEN=$(grep DISCORD_TOKEN .env | cut -d= -f2) FIFO_PATH=/tmp/pyjockie.fifo python bot/main.py`
Expected: Bot starts and logs in (Ctrl+C to stop)

**Step 3: Commit**

```bash
git add bot/bot.py
git commit -m "refactor: make bot configuration injectable"
```

---

### Task 4: Refactor main.py into a reusable run_bot() function

**Files:**
- Modify: `bot/main.py`

**Step 1: Refactor main.py**

Replace `bot/main.py` with:

```python
import asyncio
import logging
import os
import sys

import discord

# Load opus before importing bot (which imports discord voice components)
if not discord.opus.is_loaded():
    for path in [
        # Inside .app bundle
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Resources", "libopus.dylib"),
        # macOS Homebrew
        "/opt/homebrew/lib/libopus.dylib",
        # Linux
        "/usr/lib/libopus.so.0",
    ]:
        try:
            discord.opus.load_opus(path)
            break
        except OSError:
            continue

from bot import bot, configure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("pyjockie")


def run_bot(token: str, fifo_path: str = "/tmp/pyjockie.fifo", event_port: int = 8080):
    """Start the Discord bot. Blocks until the bot stops."""
    configure(fifo_path=fifo_path, event_port=event_port)
    log.info("Starting PyJockie bot...")
    bot.run(token, log_handler=None)


def run_bot_async(token: str, fifo_path: str = "/tmp/pyjockie.fifo", event_port: int = 8080):
    """Start the Discord bot in a new asyncio event loop. For use from a background thread."""
    configure(fifo_path=fifo_path, event_port=event_port)
    log.info("Starting PyJockie bot (async)...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot.start(token))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(bot.close())
        loop.close()


def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        log.error("DISCORD_TOKEN environment variable is required")
        sys.exit(1)

    fifo_path = os.environ.get("FIFO_PATH", "/tmp/pyjockie.fifo")
    event_port = int(os.environ.get("EVENT_PORT", "8080"))
    run_bot(token, fifo_path, event_port)


if __name__ == "__main__":
    main()
```

**Step 2: Verify bot still works standalone**

Run: `source .venv/bin/activate && DISCORD_TOKEN=$(grep DISCORD_TOKEN .env | cut -d= -f2) FIFO_PATH=/tmp/pyjockie.fifo python bot/main.py`
Expected: Bot starts and logs in (Ctrl+C to stop)

**Step 3: Commit**

```bash
git add bot/main.py
git commit -m "refactor: extract run_bot() and run_bot_async() for app integration"
```

---

### Task 5: Create the rumps menu bar app

**Files:**
- Create: `app.py`

This is the main new file. It manages librespot as a subprocess, runs the Discord bot on a background thread, and presents the menu bar UI.

**Step 1: Create app.py**

Create `app.py` in the project root:

```python
import logging
import os
import signal
import subprocess
import sys
import threading

import rumps

# Ensure bot/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))

from config import get_discord_token, set_discord_token
from state import state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("pyjockie.app")

FIFO_PATH = "/tmp/pyjockie.fifo"
EVENT_PORT = 8080


def _find_resource(name: str) -> str:
    """Find a bundled resource, falling back to system PATH."""
    # Inside .app bundle
    if getattr(sys, "frozen", False):
        resources = os.path.join(os.path.dirname(sys.executable), "..", "Resources")
        bundled = os.path.join(resources, name)
        if os.path.isfile(bundled):
            return bundled

    # Development: use system binary
    import shutil
    found = shutil.which(name)
    if found:
        return found

    raise FileNotFoundError(f"Could not find {name}")


class PyJockieApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="PyJockie",
            title="\u266b",  # ♫
            quit_button=None,  # We handle quit ourselves
        )

        self._librespot_proc: subprocess.Popen | None = None
        self._bot_thread: threading.Thread | None = None
        self._running = False

        # Menu items
        self._status_item = rumps.MenuItem("Not running", callback=None)
        self._status_item.set_callback(None)
        self._track_item = rumps.MenuItem("", callback=None)
        self._track_item.set_callback(None)

        self.menu = [
            self._status_item,
            self._track_item,
            None,  # separator
            rumps.MenuItem("Start Streaming", callback=self._on_start),
            rumps.MenuItem("Stop Streaming", callback=self._on_stop),
            rumps.MenuItem("Restart", callback=self._on_restart),
            None,
            rumps.MenuItem("Open Spotify", callback=self._on_open_spotify),
            None,
            rumps.MenuItem("Quit", callback=self._on_quit),
        ]

    @rumps.timer(2)
    def _update_status(self, _):
        """Poll shared state and update menu items."""
        if not self._running:
            self._status_item.title = "Not running"
            self._track_item.title = ""
            return

        # Check if librespot is still alive
        if self._librespot_proc and self._librespot_proc.poll() is not None:
            log.warning("librespot exited unexpectedly (code %d)", self._librespot_proc.returncode)
            self._status_item.title = "\u274c librespot crashed"
            return

        # Update track info
        track = state.current_track
        if track and track.name:
            self._track_item.title = f"\U0001f3b5 {track.name} \u2014 {track.artists}"
        else:
            self._track_item.title = "Waiting for Spotify..."

        # Update status
        if state.is_playing:
            self._status_item.title = "\U0001f7e2 Playing"
        elif state.current_track:
            self._status_item.title = "\U0001f7e1 Paused"
        elif state.voice_channel_id:
            self._status_item.title = "\U0001f7e2 Connected to Discord"
        else:
            self._status_item.title = "Discord: use /join in your server"

    def _ensure_token(self) -> str | None:
        """Get token, prompting user if needed."""
        token = get_discord_token()
        if token:
            return token

        # Show dialog to get token
        response = rumps.Window(
            title="PyJockie Setup",
            message="Enter your Discord Bot Token:",
            default_text="",
            ok="Save",
            cancel="Cancel",
            dimensions=(320, 24),
        ).run()

        if response.clicked and response.text.strip():
            token = response.text.strip()
            set_discord_token(token)
            return token

        return None

    def _ensure_fifo(self):
        """Create the FIFO if it doesn't exist."""
        if not os.path.exists(FIFO_PATH):
            os.mkfifo(FIFO_PATH)
            log.info("Created FIFO at %s", FIFO_PATH)

    def _start_librespot(self):
        """Start the librespot subprocess."""
        librespot_bin = _find_resource("librespot")
        ffmpeg_bin = _find_resource("ffmpeg")

        # Set ffmpeg path for the audio module
        os.environ["PATH"] = os.path.dirname(ffmpeg_bin) + ":" + os.environ.get("PATH", "")

        log.info("Starting librespot: %s", librespot_bin)
        self._librespot_proc = subprocess.Popen(
            [
                librespot_bin,
                "--name", "PyJockie",
                "--backend", "pipe",
                "--device", FIFO_PATH,
                "--bitrate", "320",
                "--format", "S16",
                "--onevent-post", f"http://127.0.0.1:{EVENT_PORT}/api/librespot-event",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def _start_bot(self, token: str):
        """Start the Discord bot on a background thread."""
        from main import run_bot_async

        self._bot_thread = threading.Thread(
            target=run_bot_async,
            args=(token, FIFO_PATH, EVENT_PORT),
            daemon=True,
            name="discord-bot",
        )
        self._bot_thread.start()

    def _stop_all(self):
        """Stop librespot and the bot."""
        self._running = False

        if self._librespot_proc:
            log.info("Stopping librespot...")
            self._librespot_proc.terminate()
            try:
                self._librespot_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._librespot_proc.kill()
            self._librespot_proc = None

        # Bot thread is a daemon — it dies when we stop the bot
        from bot import bot
        import asyncio
        if bot.is_ready():
            # Schedule close on the bot's event loop
            loop = bot.loop
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(bot.close(), loop)

        # Clean up FIFO
        if os.path.exists(FIFO_PATH):
            try:
                os.remove(FIFO_PATH)
            except OSError:
                pass

        # Reset state
        state.is_playing = False
        state.is_streaming = False
        state.current_track = None
        state.voice_channel_id = None
        state.guild_id = None

        log.info("All services stopped")

    def _on_start(self, _):
        if self._running:
            rumps.alert("Already running!")
            return

        token = self._ensure_token()
        if not token:
            rumps.alert("No Discord token provided. Cannot start.")
            return

        try:
            self._ensure_fifo()
            self._start_librespot()
            self._start_bot(token)
            self._running = True
            log.info("PyJockie started")
        except FileNotFoundError as e:
            rumps.alert(f"Missing dependency: {e}")
        except Exception as e:
            log.exception("Failed to start")
            rumps.alert(f"Failed to start: {e}")

    def _on_stop(self, _):
        if not self._running:
            return
        self._stop_all()

    def _on_restart(self, _):
        self._on_stop(None)
        self._on_start(None)

    def _on_open_spotify(self, _):
        os.system("open -a Spotify")

    def _on_quit(self, _):
        self._stop_all()
        rumps.quit_application()


def main():
    PyJockieApp().run()


if __name__ == "__main__":
    main()
```

**Step 2: Smoke test the app**

Run: `source .venv/bin/activate && python app.py`
Expected: A `♫` icon appears in the macOS menu bar. Clicking it shows the menu. Click "Start Streaming" — it should prompt for a Discord token (or use the one from env/config), start librespot, and start the bot.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add rumps menu bar app"
```

---

### Task 6: Create setup.py and build script for py2app

**Files:**
- Create: `setup.py`
- Create: `scripts/build-app.sh`
- Create: `resources/` directory (placeholder for icon)

**Step 1: Create setup.py**

Create `setup.py` in project root:

```python
from setuptools import setup

APP = ["app.py"]
APP_NAME = "PyJockie"

DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/icon.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.pyjockie.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Hide from Dock (menu bar app)
    },
    "packages": ["discord", "aiohttp", "rumps", "bot"],
    "includes": [
        "discord.opus",
        "nacl",
        "nacl.bindings",
    ],
    "resources": [
        "bot/audio.py",
        "bot/bot.py",
        "bot/config.py",
        "bot/main.py",
        "bot/state.py",
    ],
}

setup(
    name=APP_NAME,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
```

**Step 2: Create build script**

Create `scripts/build-app.sh`:

```bash
#!/usr/bin/env bash
# Build PyJockie.app using py2app.
# Copies bundled binaries (librespot, ffmpeg, libopus) into the .app bundle.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "==> Cleaning previous build..."
rm -rf build dist

echo "==> Building .app with py2app..."
python setup.py py2app 2>&1

echo "==> Copying bundled binaries..."
RESOURCES="dist/PyJockie.app/Contents/Resources"

# Copy librespot
LIBRESPOT="$(which librespot)"
echo "    librespot: $LIBRESPOT"
cp "$LIBRESPOT" "$RESOURCES/librespot"
chmod +x "$RESOURCES/librespot"

# Copy ffmpeg
FFMPEG="$(which ffmpeg)"
echo "    ffmpeg: $FFMPEG"
cp "$FFMPEG" "$RESOURCES/ffmpeg"
chmod +x "$RESOURCES/ffmpeg"

# Copy libopus
LIBOPUS="/opt/homebrew/lib/libopus.dylib"
if [ -f "$LIBOPUS" ]; then
    echo "    libopus: $LIBOPUS"
    cp "$LIBOPUS" "$RESOURCES/libopus.dylib"
else
    echo "    WARNING: libopus not found at $LIBOPUS"
fi

echo ""
echo "==> Build complete!"
echo "    App: dist/PyJockie.app"
du -sh "dist/PyJockie.app"
echo ""
echo "    To install: cp -r dist/PyJockie.app /Applications/"
```

**Step 3: Make build script executable**

Run: `chmod +x scripts/build-app.sh`

**Step 4: Create resources directory with placeholder**

Run: `mkdir -p resources && touch resources/.gitkeep`

Note: We'll generate a proper icon later. py2app will still build without one.

**Step 5: Commit**

```bash
git add setup.py scripts/build-app.sh resources/.gitkeep
git commit -m "build: add py2app setup.py and build script"
```

---

### Task 7: Update .gitignore and README

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

**Step 1: Update .gitignore**

Add these lines to `.gitignore`:

```
build/
dist/
*.egg-info/
```

**Step 2: Update README.md**

Replace `README.md` with updated content reflecting the macOS app approach. Key sections:
- Overview (menu bar app, not Docker)
- Requirements (macOS, Spotify Premium, Discord bot token)
- Quick Start (dev mode: `python app.py`)
- Building the app (`scripts/build-app.sh`)
- Installation (drag to /Applications)
- Usage (start streaming, select PyJockie in Spotify, /join in Discord)
- Discord bot commands (/join, /leave, /np)
- Development (local scripts, env vars)

**Step 3: Commit**

```bash
git add .gitignore README.md
git commit -m "docs: update README and gitignore for macOS app"
```

---

### Task 8: Smoke test the full menu bar app

**Files:** None (testing only)

**Step 1: Run the app in dev mode**

Run: `source .venv/bin/activate && python app.py`

**Step 2: Verify menu bar**

Expected: `♫` icon appears in menu bar. Click it — see the menu with status, start/stop, etc.

**Step 3: Start streaming**

Click "Start Streaming". If no token is saved, a dialog should appear — paste the Discord token. Verify:
- librespot starts (check `ps aux | grep librespot`)
- Bot logs in (check terminal output)
- Menu updates to show "Discord: use /join in your server"

**Step 4: Test the full pipeline**

1. In Discord, `/join` a voice channel
2. Open Spotify, select "PyJockie" device
3. Play a track
4. Verify audio in Discord
5. Check menu shows track name
6. Click "Stop Streaming" — verify everything shuts down cleanly

**Step 5: Test restart**

Click "Restart" — verify it stops and starts cleanly.

---

### Task 9: Build the .app bundle

**Files:** None (build only)

**Step 1: Run the build**

Run: `source .venv/bin/activate && scripts/build-app.sh`

Expected: Build completes, `dist/PyJockie.app` is created.

**Step 2: Test the built app**

Run: `open dist/PyJockie.app`

Expected: Same behavior as dev mode — menu bar icon appears, streaming works.

**Step 3: If build fails, debug**

Common py2app issues:
- Missing modules: add to `includes` in `setup.py`
- Missing packages: add to `packages` in `setup.py`
- Binary linking issues: check `otool -L` on the binaries in Resources

**Step 4: Tag the release**

```bash
git tag -a v0.1.0 -m "v0.1.0: initial macOS menu bar app"
```
