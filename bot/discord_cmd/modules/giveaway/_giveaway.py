from discord import ApplicationContext, slash_command,Bot
from discord.ext.commands import Cog
from pycord.multicog import subcommand

from bot.database import Database
from bot.discord_cmd.helpers import command_utils,helpers


class Giveaway(Cog):
    def __init__(self, client:Bot) -> None:
        self.client = client

    @subcommand("giveaway")
    @slash_command(description="Get the best exp gains the guild has ever done", name="list")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/giveaway list")
    @command_utils.took_too_long()
    async def gw_list(self,ctx:ApplicationContext):
        return
        giveaways = await Database
        
def setup(client:Bot):
    client.add_cog(Giveaway(client))
