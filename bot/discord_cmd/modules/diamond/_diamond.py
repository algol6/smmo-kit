from discord import ApplicationContext, slash_command, Bot, guild_only,Role,TextChannel,Forbidden
from discord.ext.commands import Cog
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.modules.diamond._market_url_button import MarketUrlButton
from bot.discord_cmd.modules.diamond._tasks import DiamondsTasks
from datetime import datetime

class Diamonds(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client

    @slash_command(description="Show current diamond market")
    @guild_only()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/diamond_market")
    @command_utils.took_too_long()
    async def diamond_market(self,ctx:ApplicationContext):
        diamond_market = sorted(await SMMOApi.get_diamond_market(), key=lambda x: x.price_per_diamond)[:5]
        emb = helpers.Embed(title="Diamond Market", description=f"Last Update: <t:{int(datetime.now().timestamp())}:R>")
        for entry in diamond_market:
            emb.add_field(name="",value=f"**Seller**: [{entry.seller.name}](https://simple-mmo.com/user/view/{entry.seller.id})\n**Price**: {entry.price_per_diamond:,} :coin:\n**Amount**: {entry.diamonds_remaining:,}/{entry.diamond_amount_at_start:,} :gem:",inline=False)
        await helpers.send(ctx,embed=emb,view=MarketUrlButton())

    
    @subcommand("admin diamonds")
    @slash_command(description="Set the pinging when the price goes under x gold")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin diamonds set_ping")
    @command_utils.took_too_long()
    async def set_ping(self,ctx:ApplicationContext,role:Role,min_price:int,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")
        if not await Database.insert_diamonds(role.id,channel.id,min_price):
            return await helpers(content="Diamond ping already setted.")
        await helpers.send(ctx,content="Diamond market ping has been set up")

    @subcommand("admin diamonds")
    @slash_command(description="Remove the pinging from a channel")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin diamonds remove_ping")
    @command_utils.took_too_long()
    async def remove_ping(self,ctx:ApplicationContext,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        await Database.delete_diamonds(channel.id)
        await helpers.send(ctx,content="Diamond market ping has been removed")

def setup(client:Bot):
    client.add_cog(Diamonds(client))
    client.add_cog(DiamondsTasks(client))
