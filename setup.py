"""
py2app build configuration.

This file exists because py2app requires setup.py — it does not support
PEP 517 build backends. All project metadata and dependencies live in
pyproject.toml. Build with: make build
"""
from setuptools import setup

APP = ["app.py"]
APP_NAME = "PyJockie"

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/icon.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.pyjockie.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,
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
    data_files=[],
    options={"py2app": OPTIONS},
)
