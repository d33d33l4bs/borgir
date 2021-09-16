import asyncio
import contextlib
import subprocess

from dataclasses import dataclass
from functools import lru_cache

from discord import FFmpegPCMAudio
from discord.ext import commands
from youtube_dl import YoutubeDL


@dataclass
class YoutubeSong:
    url: str
    title: str
    duration: int

    @classmethod
    @lru_cache(maxsize=100)
    def from_url(cls, url):
        """Make a new YoutubeSong instance by parsing a Youtube url.

        A lru cache is used in order to minimize the number of requests sent to
        Youtube.
        """
        with YoutubeDL() as ydl:
            infos = ydl.extract_info(url, download=False)
        return cls(
            url,
            infos.get("title", None),
            infos.get("duration", None)
        )


class Play(commands.Cog):
    """
    Attributes
    ----------
    _playlist : asyncio.Queue
        A queue in which all the Youtube urls are stored.
    _voice_client : discord.VoiceClient
        The Discord voice client used to stream songs.
    _stream_task : asyncio.Task
        The background task that consumes the playlist and streams songs on
        a voice channel.
    _skip_song : bool
        Allows to skip the music being played.
    """
    def __init__(self, bot):
        self.bot = bot
        self._playlist = asyncio.Queue()
        self._voice_client = None
        self._stream_task = None
        self._skip_song = False

    @property
    def is_playing(self):
        """Returns True if the bot is currently playing a song."""
        return self._voice_client is not None \
            and self._voice_client.is_playing()

    @commands.command(name="p")
    async def play(self, ctx, url: str):
        """Adds a new song to the playlist and run the streaming task."""
        if ctx.message.channel != self.bot.command_channel:
            return
        # Make a new voice channel if needed.
        if self._voice_client is None:
            channel = ctx.message.author.voice.channel
            self._voice_client = await channel.connect()
        # Run the background task if needed.
        if self._stream_task is None:
            self._stream_task = asyncio.create_task(self._stream())
        # Retrieve the YT song and put it into the playlist.
        song = YoutubeSong.from_url(url)
        await self._playlist.put(song)
        await self.bot.command_channel.send(f'"{song.title}" added to queue (duration: {song.duration}s).')

    @commands.command(name="n")
    async def next(self, ctx):
        """Skips the current song."""
        if ctx.message.channel != self.bot.command_channel:
            return
        if self.is_playing:
            self._skip_song = True
        else:
            await self.bot.command_channel.send("Nothing to skip...")

    @commands.command(name="s")
    async def stop(self, ctx):
        """Stops the stream and reset the playlist."""
        if ctx.message.channel != self.bot.command_channel:
            return
        if self._voice_client is not None:
            self._voice_client.stop()
        if self._stream_task is not None:
            self._stream_task.cancel()
            self._stream_task = None
        self._playlist = asyncio.Queue()
    
    @commands.command(name="d")
    async def disconnect(self, ctx):
        """Disconnects the bot from the voice channel."""
        if ctx.message.channel != self.bot.command_channel:
            return
        if self._voice_client is not None:
            await self._voice_client.disconnect()
            self._voice_client = None
        if self._stream_task is not None:
            self._stream_task.cancel()
            self._stream_task = None

    async def _stream(self):
        """Background task that streams the playlist songs."""
        while True:
            song = await self._playlist.get()
            await self.bot.command_channel.send(f"Currently playing: {song.url}.")
            # We do not use the Python library here because it doesn't provide
            # an easy way to pipe its output.
            cmd = ["youtube-dl", "-o", "-", song.url]
            with _run_and_terminate(cmd, stdout=subprocess.PIPE) as ydl:
                self._skip_song = False
                # Start the youtube-dl stdout streaming to the voice channel.
                self._voice_client.play(FFmpegPCMAudio(ydl.stdout, pipe=True))
                # Continue to stream unless another command asks to stop or
                # skip the current song.
                while self._voice_client.is_playing() and not self._skip_song:
                    await asyncio.sleep(1)
                self._voice_client.stop()


def setup(bot):
    bot.add_cog(Play(bot))


@contextlib.contextmanager
def _run_and_terminate(*args, **kwargs):
    """Ensures that a process is well terminated even if an exception
    occured."""
    try:
        process = subprocess.Popen(*args, **kwargs)
        yield process
    finally:
        process.terminate()
        process.communicate()
