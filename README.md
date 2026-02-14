# PyJockie

A macOS menu bar app that streams Spotify audio into a Discord voice channel via Spotify Connect. Control playback entirely from the Spotify app.

## How It Works

```
Spotify App (phone/PC)
  → Spotify Connect (Zeroconf on LAN)
    → librespot (receives + decrypts audio)
      → named pipe (FIFO)
        → ffmpeg (resamples 44.1kHz → 48kHz)
          → Discord bot (streams to voice channel)
```

## Requirements

- **macOS** (Apple Silicon or Intel)
- **Spotify Premium** account
- **Discord Bot** token ([create one here](https://discord.com/developers/applications))

## Quick Start (Development)

```bash
# Install system dependencies
brew install librespot ffmpeg opus

# Install Python dependencies
uv venv && uv pip install -r bot/requirements.txt

# Run the menu bar app
python app.py
```

On first launch, the app will prompt for your Discord bot token.

## Building the App

```bash
scripts/build-app.sh
```

This produces `dist/PyJockie.app` — a self-contained app bundling Python, librespot, ffmpeg, and libopus. Drag it to `/Applications` to install.

## Usage

1. Launch PyJockie (♫ appears in the menu bar).
2. Click ♫ → **Start Streaming**.
3. In Discord, type `/join` in any text channel while in a voice channel.
4. Open Spotify → **Devices** → select **PyJockie**.
5. Play music — it streams through the Discord voice channel.
6. Control playback (play, pause, skip, repeat, shuffle) from Spotify.

## Discord Commands

| Command | Description |
|---------|-------------|
| `/join` | Join your voice channel and start streaming |
| `/leave` | Disconnect from the voice channel |
| `/np` | Show the currently playing track |

## Configuration

The Discord token is stored in `~/.config/pyjockie/config.json` after first setup.

For development, you can also set the `DISCORD_TOKEN` environment variable or use a `.env` file.

## License

MIT
