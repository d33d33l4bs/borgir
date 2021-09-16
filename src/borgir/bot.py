from discord.ext import commands
from discord.utils import get


class Borgir(commands.Bot):
    def __init__(self, guild_name, command_channel_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_channel = None
        self._guild_name = guild_name
        self._command_channel_name = command_channel_name

    async def on_ready(self):
        guild = get(self.guilds, name=self._guild_name)
        self.command_channel = get(guild.text_channels, name=self._command_channel_name)
        print(f"{self.user} is now connected to the guild {self._guild_name}.")

    async def on_error(self, event, *args, **kwargs):
        pass
