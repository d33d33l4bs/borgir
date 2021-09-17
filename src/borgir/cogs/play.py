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


class Playlist(asyncio.Queue):
    def __init__(self, name, maxsize=0):
        super().__init__(maxsize)
        self._name = name

    @property
    def name(self):
        return self._name

    def clear(self):
        self._queue.clear()
        self._wakeup_next(self._putters)

    async def get(self):
        item = await super().get()
        # We don't care about tasks.
        self.task_done()
        return item

    def __iter__(self):
        return iter(self._queue)


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
        self._playlist = Playlist("default")
        self._voice_client = None
        self._stream_task = None
        self._skip_song = False
        self._current_song = None

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
        # Retrieve the YT song.
        try:
            song = YoutubeSong.from_url(url)
        except:
            await self.bot.command_channel.send("An error occured with your url.")
            return
        # Make a new voice channel if needed.
        if self._voice_client is None:
            channel = ctx.message.author.voice.channel
            self._voice_client = await channel.connect()
        # Run the background task if needed.
        if self._stream_task is None:
            self._stream_task = asyncio.create_task(self._stream())
        # Put the song into the playlist.
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

    @commands.command(name="l")
    async def list(self, ctx):
        """Lists all the playlist songs."""
        if self._playlist.qsize() > 0 or self._current_song:
            await self.bot.command_channel.send("Songs in the playlist:")
            if self._current_song is not None:
                await self.bot.command_channel.send(f"{self._current_song.title}")
            for song in self._playlist:
                await self.bot.command_channel.send(f"{song.title}")
        else:
            await self.bot.command_channel.send("No song in the playlist.")

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
        self._playlist.clear()
        self._current_song = None
    
    @commands.command(name="d")
    async def disconnect(self, ctx):
        """Disconnects the bot from the voice channel."""
        if ctx.message.channel != self.bot.command_channel:
            return
        await self.stop(ctx)
        if self._voice_client is not None:
            await self._voice_client.disconnect()
            self._voice_client = None

    async def _stream(self):
        """Background task that streams the playlist songs."""
        while True:
            self._current_song = await self._playlist.get()
            await self.bot.command_channel.send(f"Currently playing: {self._current_song.url}.")
            # We do not use the Python library here because it doesn't provide
            # an easy way to pipe its output.
            cmd = ["youtube-dl", "-o", "-", self._current_song.url]
            with _run_and_terminate(cmd, stdout=subprocess.PIPE) as ydl:
                self._skip_song = False
                # Start the youtube-dl stdout streaming to the voice channel.
                self._voice_client.play(FFmpegPCMAudio(ydl.stdout, pipe=True))
                # Continue to stream unless another command asks to stop or
                # skip the current song.
                while self._voice_client.is_playing() and not self._skip_song:
                    await asyncio.sleep(1)
                self._voice_client.stop()
                self._current_song = None


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
