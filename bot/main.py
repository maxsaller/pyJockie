import logging
import os
import sys

import discord
if not discord.opus.is_loaded():
    # macOS Homebrew path; on Linux (Docker) it loads automatically
    for path in ["/opt/homebrew/lib/libopus.dylib", "/usr/lib/libopus.so.0"]:
        try:
            discord.opus.load_opus(path)
            break
        except OSError:
            continue

from bot import bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("pyjockie")


def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        log.error("DISCORD_TOKEN environment variable is required")
        sys.exit(1)

    log.info("Starting PyJockie...")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
