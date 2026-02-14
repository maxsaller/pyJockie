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

        # Ensure ffmpeg is on PATH for the audio module
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
