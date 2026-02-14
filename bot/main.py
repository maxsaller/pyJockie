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
