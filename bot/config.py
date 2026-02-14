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
