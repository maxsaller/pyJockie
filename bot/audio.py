import logging
import subprocess
import time

import discord

log = logging.getLogger(__name__)

FRAME_SIZE = 3840  # 20ms at 48kHz, 16-bit, stereo
SILENCE = b"\x00" * FRAME_SIZE
MAX_RESTART_ATTEMPTS = 5
RESTART_BACKOFF_SECS = 1.0


class SpotifyAudioSource(discord.AudioSource):
    """Reads raw PCM from a FIFO via ffmpeg and feeds it to discord.py."""

    def __init__(self, fifo_path: str):
        self.fifo_path = fifo_path
        self.process: subprocess.Popen | None = None
        self._closed = False
        self._restart_count = 0
        self._last_restart: float = 0

    def start(self):
        """Spawn the ffmpeg process that reads from the FIFO."""
        if self.process and self.process.poll() is None:
            return

        log.info("Starting ffmpeg: reading from %s", self.fifo_path)
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "warning",
                # Input: raw S16LE 44.1kHz stereo from librespot
                "-f", "s16le",
                "-ar", "44100",
                "-ac", "2",
                "-i", self.fifo_path,
                # Output: S16LE 48kHz stereo for Discord
                "-f", "s16le",
                "-ar", "48000",
                "-ac", "2",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._restart_count = 0

    def _restart(self) -> bool:
        """Kill the current ffmpeg and start a new one. Returns False if backoff limit hit."""
        now = time.monotonic()

        # Reset counter if last restart was long ago (stream was healthy)
        if now - self._last_restart > 10.0:
            self._restart_count = 0

        self._restart_count += 1
        self._last_restart = now

        if self._restart_count > MAX_RESTART_ATTEMPTS:
            log.warning(
                "ffmpeg restarted %d times rapidly, backing off for %.1fs",
                self._restart_count, RESTART_BACKOFF_SECS,
            )
            time.sleep(RESTART_BACKOFF_SECS)
            self._restart_count = 0

        log.info("Restarting ffmpeg process (attempt %d)", self._restart_count)
        self._kill_process()
        self.start()
        return True

    def _kill_process(self):
        if self.process:
            try:
                self.process.kill()
                self.process.wait(timeout=5)
            except Exception:
                pass
            self.process = None

    def read(self) -> bytes:
        if self._closed:
            return b""

        if self.process is None or self.process.poll() is not None:
            self._restart()

        try:
            data = self.process.stdout.read(FRAME_SIZE)
        except Exception:
            log.exception("Error reading from ffmpeg")
            return SILENCE

        if not data:
            self._restart()
            return SILENCE

        if len(data) < FRAME_SIZE:
            data += b"\x00" * (FRAME_SIZE - len(data))

        return data

    def is_opus(self) -> bool:
        return False

    def cleanup(self):
        self._closed = True
        self._kill_process()
        log.info("SpotifyAudioSource cleaned up")
