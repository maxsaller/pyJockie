# PyJockie macOS Menu Bar App — Design

**Date:** 2026-02-13
**Status:** Approved

## Overview

Pivot from Docker/TrueNAS deployment to a self-contained macOS menu bar app. The app bundles librespot, ffmpeg, and the Discord bot into a single `.app` that lives in the menu bar tray.

## Architecture

```
┌─────────────────────────────────────────────┐
│  PyJockie.app (macOS menu bar)              │
│                                             │
│  rumps MenuBarApp                           │
│  ├── Status icon + dropdown menu            │
│  ├── librespot (subprocess)                 │
│  │   └── writes PCM → /tmp/pyjockie.fifo   │
│  ├── Discord bot (asyncio on bg thread)     │
│  │   ├── slash commands (/join /leave /np)  │
│  │   └── reads FIFO → ffmpeg → voice        │
│  └── aiohttp server (librespot events)      │
└─────────────────────────────────────────────┘
```

Single Python process. rumps owns the macOS main thread (NSApplication run loop). The Discord bot runs on a background thread with its own asyncio event loop. librespot is a child subprocess.

## Menu Bar UI

```
♫ PyJockie
├── 🟢 Connected to Discord
├── 🎵 Track Name — Artist
├── ──────────────────
├── Start Streaming
├── Stop Streaming
├── Restart
├── ──────────────────
├── Open Spotify
├── ──────────────────
├── Quit
```

**States:**
- Not running: dimmed icon, "Start Streaming" enabled
- Running, no track: "Waiting for Spotify..."
- Running, playing: track + artist, green status
- Running, paused: track + artist, yellow "Paused"
- Discord not in voice: "Discord: use /join"

## Process Management

**librespot:** Launched via `subprocess.Popen` with bundled binary. Args: `--name PyJockie --backend pipe --device /tmp/pyjockie.fifo --bitrate 320 --format S16`. Crash detection via poll loop.

**Discord bot:** Background `threading.Thread(daemon=True)` running its own `asyncio.run()`. The aiohttp event server for librespot metadata runs inside this event loop.

**FIFO:** Created at `/tmp/pyjockie.fifo` on startup, removed on quit.

**Startup:** App launches → create FIFO → start librespot → start bot thread → show "Waiting for Spotify..."

**Shutdown:** Stop bot (disconnect voice, close) → terminate librespot → remove FIFO.

**Config:** Discord token stored in `~/.config/pyjockie/config.json`. Prompted on first launch via dialog if missing.

## Bundling

Built with py2app into a self-contained `.app`:

```
PyJockie.app/Contents/
├── MacOS/PyJockie              (entry point)
├── Resources/
│   ├── librespot               (arm64 binary from Homebrew)
│   ├── ffmpeg                  (arm64 binary from Homebrew)
│   ├── libopus.dylib           (shared library)
│   └── icon.icns               (app icon)
└── Frameworks/Python.framework (bundled runtime + deps)
```

Estimated size: ~80-100MB. Installation: drag to /Applications.

## Project Structure

```
pyjockie/
├── app.py                    # rumps menu bar app (new entry point)
├── setup.py                  # py2app build config
├── bot/
│   ├── audio.py              # SpotifyAudioSource (unchanged)
│   ├── state.py              # shared state (unchanged)
│   ├── bot.py                # Discord bot (minor refactor)
│   └── main.py               # run_bot() helper
├── scripts/
│   └── build-app.sh          # build script
├── resources/
│   └── icon.icns             # app icon
├── docs/plans/               # this document
├── .env                      # dev only
└── README.md                 # updated
```

## What Changes

- **Keep:** `bot/audio.py`, `bot/state.py` (unchanged)
- **Modify:** `bot/bot.py` (event server callable from app), `bot/main.py` (becomes `run_bot()` helper)
- **New:** `app.py`, `setup.py`, `scripts/build-app.sh`, `resources/icon.icns`
- **Deprecate:** `docker-compose.yml`, `bot/Dockerfile` (keep for reference)

## Tech Stack

- **rumps** — macOS menu bar framework (Python, wraps PyObjC/NSStatusBar)
- **py2app** — bundles Python app into `.app` with embedded runtime
- **discord.py** — Discord bot (existing)
- **aiohttp** — HTTP server for librespot events (existing)
- **ffmpeg** — audio resampling (bundled binary)
- **librespot** — Spotify Connect receiver (bundled binary)
