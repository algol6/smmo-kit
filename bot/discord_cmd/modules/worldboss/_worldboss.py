from discord import ApplicationContext, slash_command,guild_only,option,TextChannel,Role
from discord.ext.commands import Cog

from pycord.multicog import subcommand

from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.database.model import WorldBoss
from datetime import datetime, time
from bot.discord_cmd.modules.worldboss._worldboss_url_button import WorldbossUrlButton
from bot.discord_cmd.modules.worldboss._worldboss_view import WorldbossView
from bot.discord_cmd.modules.worldboss._task import WorldbossTasks



class Worldboss(Cog):
    def __init__(self, client) -> None:
        self.client = client

    @slash_command(description="Show weekly worldboss")
    @guild_only()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/worldboss_list")
    @command_utils.took_too_long()
    async def worldboss_list(self, ctx: ApplicationContext) -> None:
        wb_view = WorldbossView()
        wb_view.data = sorted(await Database.select_all_worldboss(), key=lambda boss: boss.enable_time)
        await wb_view.send(ctx)

    @slash_command(description="Show worldboss ping")
    @guild_only()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/worldboss_pings")
    @command_utils.took_too_long()
    async def worldboss_pings(self, ctx: ApplicationContext) -> None:
        pings: list[str] = []
        append = pings.append
        guild_channels = set(x.id for x in ctx.guild.channels)
        for ping in await Database.select_wb_notification():
            if ping.channel_id in guild_channels:
                append(f"<#{ping.channel_id}> <@&{ping.role_id}> **{ping.seconds_before//60}** minutes before. {"God only." if bool(ping.god) else "All wb."}")
        emb = helpers.Embed(title="Worldboss Pings")
        emb.add_field(name="",value=f"{"\n".join(pings)}")
        await helpers.send(ctx,embed=emb)

    @subcommand("admin worldboss")
    @slash_command(description="Remove the worldboss message")
    @guild_only()
    @option(name="channel", description="Define the channel where remove the messages. default: current channel")
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin worldboss remove_message")
    @command_utils.took_too_long()
    async def remove_message(self,ctx:ApplicationContext,channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        await Database.delete_wb_message(channel.id)
        await helpers.send(ctx,content="Message removed")  
        
    @subcommand("admin worldboss")
    @slash_command(description="Remove the ping for world boss")
    @guild_only()
    @option(name="channel", description="Define the channel where remove the ping. default: current channel")
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin worldboss remove_ping")
    @command_utils.took_too_long()
    async def remove_ping(self,ctx:ApplicationContext,minutes_before:int,channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        await Database.delete_wb_notification(channel.id, minutes_before * 60)
        await helpers.send(ctx,content="Notifications has been removed")

    @subcommand("admin worldboss")
    @slash_command(description="Setup the message to show current worldboss")
    @guild_only()
    @option(name="channel", description="Define the channel where send the messages. default: current channel")
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin worldboss set_message")
    @command_utils.took_too_long()
    async def set_message(self,ctx:ApplicationContext,channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        await helpers.get_channel_and_send(self.client,channel.id,delete_after=1)
        
        if not await Database.insert_wb_message(channel.id):
            return await helpers.send(ctx,content="Message already set up in this channel")
        await helpers.send(ctx,content="Setup done")
     
    @subcommand("admin worldboss")
    @slash_command(description="Setup the ping for world boss")
    @guild_only()
    @option(name="channel", description="Define the channel where send the messages. default: current channel")
    @option(name="god_only", description="Set the ping only for the GOD world boss", choices=["Yes","No"])
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin worldboss set_ping")
    @command_utils.took_too_long()    
    async def set_ping(self,ctx:ApplicationContext,role:Role,minutes_before:int,channel:TextChannel=None,god_only:str="No") -> None:
        if channel is None:
            channel = ctx.channel
        await helpers.get_channel_and_send(self.client,channel.id,delete_after=1)

        if not await Database.insert_wb_notification(channel.id, role.id, minutes_before * 60, False if god_only=="No" else True):
            return await helpers.send(ctx,content="Notification already set up in this channel")
        await helpers.send(ctx,content="Notifications has been set up")

def setup(client):
    client.add_cog(Worldboss(client))
    client.add_cog(WorldbossTasks(client))