# PyJockie

A Discord bot that streams Spotify audio into a voice channel via Spotify Connect. Control playback entirely from the Spotify app on your phone or PC.

## Architecture

```
Spotify App (phone/PC)
  → Spotify Connect (Zeroconf on LAN)
    → librespot (receives + decrypts audio)
      → named pipe (FIFO)
        → ffmpeg (resamples 44.1kHz → 48kHz)
          → Discord bot (streams to voice channel)
```

## Requirements

- **Spotify Premium** account
- **Discord Bot** token ([create one here](https://discord.com/developers/applications))
- **Docker** and **Docker Compose**

## Setup

1. Clone this repository.

2. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```

3. Start the stack:
   ```bash
   docker compose up -d --build
   ```

4. Invite the bot to your Discord server using the OAuth2 URL from the Discord Developer Portal (with `bot` and `applications.commands` scopes, plus `Connect` and `Speak` voice permissions).

## Usage

1. Join a voice channel in Discord.
2. Run `/join` — the bot connects to your voice channel.
3. Open Spotify on your phone/PC. In the **Devices** menu, select **PyJockie**.
4. Play music — it streams through the Discord voice channel.
5. Control playback (play, pause, skip, repeat, shuffle) from Spotify.

### Commands

| Command | Description |
|---------|-------------|
| `/join` | Join your voice channel and start streaming |
| `/leave` | Disconnect from the voice channel |
| `/np` | Show the currently playing track |

## Configuration

Environment variables (set in `.env` or `docker-compose.yml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | — | Discord bot token (required) |
| `FIFO_PATH` | `/mnt/pipe/spotify.fifo` | Path to the audio FIFO |
| `EVENT_PORT` | `8080` | Port for librespot event webhook |

The librespot device name, bitrate, and other settings can be adjusted in `docker-compose.yml` under the `librespot` service environment variables.

## Deploying on TrueNAS (Portainer)

1. Install Portainer from the TrueNAS Apps catalog.
2. In Portainer, go to **Stacks** → **Add Stack**.
3. Paste the contents of `docker-compose.yml`.
4. Add `DISCORD_TOKEN` as an environment variable.
5. Deploy.

## First-Time Spotify Authentication

On first start, librespot advertises itself as **PyJockie** on your local network via Zeroconf/mDNS. Open Spotify, go to Devices, and select it. Credentials are cached automatically for subsequent restarts.

> **Note:** Both the `librespot` and `bot` containers use `network_mode: host` so that Spotify apps on your LAN can discover the device via mDNS.

## License

MIT
