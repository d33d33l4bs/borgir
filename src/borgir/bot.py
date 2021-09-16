from discord.ext import commands
from discord.utils import get


class Borgir(commands.Bot):
    def __init__(self, command_channel_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_channel = None
        self._command_channel_name = command_channel_name

    async def on_ready(self):
        # TODO: handle multi guilds?
        guild = self.guilds[0]
        self.command_channel = get(guild.text_channels, name=self._command_channel_name)
        print(f"{self.user} is now connected.")

    async def on_error(self, event, *args, **kwargs):
        pass
