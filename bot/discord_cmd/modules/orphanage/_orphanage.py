from discord import Bot,ApplicationContext,slash_command,guild_only,option,Role,TextChannel,Forbidden
from discord.ext import commands
from pycord.multicog import subcommand

from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.database import Database
from bot.api import SMMOApi
from time import time
from datetime import datetime

from bot.discord_cmd.modules.orphanage._task import OrphanageTask

class Orphanage(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client

    @subcommand("admin orphanage")
    @slash_command(description="Setup orphanage ping. *different tier **can** have different role to ping*")
    @guild_only()
    @option(name="tier", choices=["All Tiers","Tier 1","Tier 2","Tier 3"])
    @option(name="channel", description="Define the channel where send the orphanage ping. default: current channel")
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin orphanage")
    @command_utils.took_too_long()
    async def setup(self,ctx:ApplicationContext,role:Role,tier:str="All Tiers",channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,ontent="Bot doesn't have the perms to see/write the channel.")
        match tier:
            case "Tier 1":
                t = 1
            case "Tier 2":
                t = 2
            case "Tier 3":
                t = 3
            case _:
                t = 0
        if not await Database.insert_orphanage(channel.id,None,role.id,t,active=0):
            return await helpers.send(ctx,content="This is already configured")
        await helpers.send(ctx,content=f"Orphanage tier {tier} set up.")

    @subcommand("admin orphanage")
    @slash_command(description="Remove orphanage ping from a channel.")
    @guild_only()
    @option(name="channel", description="Define the channel where was set up the messages. default: current channel")
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.took_too_long()
    async def remove(self,ctx:ApplicationContext,tier:int,channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        await Database.delete_orphanage(channel.id)
        await helpers.send(ctx,content=f"Orphanage notify removed.")
    

    @slash_command(description="Show the current status of orphanage")
    @guild_only()
    @command_utils.auto_defer(ephemeral=False)
    @command_utils.took_too_long()
    async def orphanage(self, ctx: ApplicationContext) -> None:
        orphanage_data = await SMMOApi.get_orphanage()
        emb = helpers.Embed(title="Orphanage Status", description=f"updated: <t:{int(time())}:R>")

        for tier in orphanage_data:
            msg = f"**Active**: {":white_check_mark:" if tier.is_active else ":x:"}\n"
            msg += f"**Status**: {tier.current_value:,}:coin:/{tier.target_value:,}:coin: (*{tier.percentage}%*)\n"
            msg += f"**Remaining**: {tier.target_remaining:,}:coin:"
            emb.add_field(name=tier.tier.name,
                          value=msg, inline=False)

        await ctx.followup.send(embed=emb)
    
def setup(client:Bot):
    client.add_cog(Orphanage(client))
    client.add_cog(OrphanageTask(client))
