import logging
import os

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from audio import SpotifyAudioSource
from state import AppState, TrackInfo, state

log = logging.getLogger(__name__)

FIFO_PATH = os.environ.get("FIFO_PATH", "/mnt/pipe/spotify.fifo")
EVENT_PORT = int(os.environ.get("EVENT_PORT", "8080"))


class PyJockie(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.audio_source: SpotifyAudioSource | None = None
        self._http_runner: web.AppRunner | None = None

    async def setup_hook(self):
        self.tree.add_command(join)
        self.tree.add_command(leave)
        self.tree.add_command(now_playing)
        await self.tree.sync()
        log.info("Slash commands synced")

        # Start the HTTP event receiver
        await self._start_event_server()

    async def _start_event_server(self):
        app = web.Application()
        app.router.add_post("/api/librespot-event", _handle_librespot_event)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", EVENT_PORT)
        await site.start()
        self._http_runner = runner
        log.info("Librespot event server listening on port %d", EVENT_PORT)

    async def close(self):
        if self._http_runner:
            await self._http_runner.cleanup()
        await super().close()


bot = PyJockie()


@bot.event
async def on_ready():
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Connected to %d guild(s)", len(bot.guilds))


@app_commands.command(name="join", description="Join your voice channel and start streaming Spotify")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            "You need to be in a voice channel first.", ephemeral=True
        )
        return

    channel = interaction.user.voice.channel

    # Already connected to this channel
    if interaction.guild.voice_client and interaction.guild.voice_client.channel == channel:
        await interaction.response.send_message(
            f"Already connected to **{channel.name}**.", ephemeral=True
        )
        return

    # Move if connected elsewhere
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
        await interaction.response.send_message(f"Moved to **{channel.name}**.")
    else:
        vc = await channel.connect()
        await interaction.response.send_message(
            f"Joined **{channel.name}**. Now select **PyJockie** as your Spotify device."
        )

    state.voice_channel_id = channel.id
    state.guild_id = interaction.guild.id

    # Start audio source
    vc = interaction.guild.voice_client
    if vc.is_playing():
        vc.stop()

    source = SpotifyAudioSource(FIFO_PATH)
    source.start()
    bot.audio_source = source

    vc.play(source, after=lambda e: log.error("Player error: %s", e) if e else None)
    log.info("Audio source started, streaming from FIFO")


@app_commands.command(name="leave", description="Disconnect from the voice channel")
async def leave(interaction: discord.Interaction):
    if not interaction.guild.voice_client:
        await interaction.response.send_message("Not connected to any voice channel.", ephemeral=True)
        return

    if bot.audio_source:
        bot.audio_source.cleanup()
        bot.audio_source = None
    await interaction.guild.voice_client.disconnect()
    state.voice_channel_id = None
    state.guild_id = None
    await interaction.response.send_message("Disconnected.")
    log.info("Disconnected from voice channel")


@app_commands.command(name="np", description="Show the currently playing track")
async def now_playing(interaction: discord.Interaction):
    track = state.current_track
    if not track or not track.name:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        return

    embed = discord.Embed(
        title=track.name,
        description=f"by **{track.artists}**",
        color=discord.Color.green(),
    )
    if track.album:
        embed.add_field(name="Album", value=track.album, inline=True)
    if track.duration_ms:
        mins, secs = divmod(track.duration_ms // 1000, 60)
        embed.add_field(name="Duration", value=f"{mins}:{secs:02d}", inline=True)
    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    status = "Playing" if state.is_playing else "Paused"
    embed.set_footer(text=status)

    await interaction.response.send_message(embed=embed)


async def _handle_librespot_event(request: web.Request) -> web.Response:
    """Receive player events from librespot's ONEVENT_POST_ENDPOINT."""
    try:
        data = await request.json()
    except Exception:
        # Some events may come as form data or plain text — log and skip
        body = await request.text()
        log.debug("Non-JSON librespot event: %s", body[:500])
        return web.json_response({"ok": True})

    event = data.get("PLAYER_EVENT", "")
    log.debug("Librespot event: %s", event)

    if event == "track_changed":
        covers = data.get("COVERS", "")
        state.current_track = TrackInfo(
            name=data.get("NAME", ""),
            artists=data.get("ARTISTS", ""),
            album=data.get("ALBUM", ""),
            cover_url=covers.split(",")[0] if covers else "",
            duration_ms=int(data.get("DURATION_MS", 0)),
        )
    elif event == "playing":
        state.is_playing = True
        state.is_streaming = True
        state.position_ms = int(data.get("POSITION_MS", 0))
    elif event == "paused":
        state.is_playing = False
        state.position_ms = int(data.get("POSITION_MS", 0))
    elif event == "stopped":
        state.is_playing = False
        state.is_streaming = False
        state.current_track = None
    elif event == "volume_changed":
        state.volume = int(data.get("VOLUME", 100))
    elif event == "shuffle_changed":
        state.shuffle = str(data.get("SHUFFLE", "false")).lower() == "true"
    elif event == "repeat_changed":
        state.repeat = data.get("REPEAT", "off")

    return web.json_response({"ok": True})
