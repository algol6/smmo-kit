from discord import ApplicationContext, slash_command,guild_only,Bot
from discord.ext import tasks
from discord.ext.commands import Cog
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.helpers import permissions, command_utils,helpers
from bot.discord_cmd.helpers.logger import logger


class Extra(Cog):
    def __init__(self, client:Bot) -> None:
        self.client = client

    @subcommand("bot")
    @slash_command(description="Link to the bot GitHub page")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot stats")
    @command_utils.took_too_long()
    async def source(self,ctx:ApplicationContext):
        emb = helpers.Embed(title="SMMO-kit Source")
        emb.add_field(name="", value="Source can be found on GitHub: https://github.com/algol6/smmo-kit")
        await helpers.send(ctx,embed=emb)

    @subcommand("bot")
    @slash_command(description="Show the bot commands stats")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot stats")
    @command_utils.took_too_long()
    async def stats(self,ctx:ApplicationContext):
        is_empty,data = helpers.gen_is_empty(await Database.select_statistics())
        if is_empty:
            await helpers.send(ctx,"No stats")
        data = [*data]
        data.sort(key=lambda x: x.time_used,reverse=True)
        emb = helpers.Embed(title="SMMO-kit Commands Statistics")
        emb.add_field(name="", value="\n".join(f"`{x.id}` Used **{x.time_used:,}** times with an average time of **{x.average_time:.2f}**s" for x in data[:10]))
        emb.set_footer(text="Since `v2.0.1`")
        await helpers.send(ctx,embed=emb)

    @subcommand("bot")
    @slash_command(description="Get the link to join the discord support server")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot help")
    @command_utils.took_too_long()
    async def help(self,ctx:ApplicationContext):
        emb = helpers.Embed(title="SMMO-kit Support")
        emb.add_field(name="", value="Got any question about the bot? Problems? Bugs? or requests?\nJoin https://discord.gg/bPRJkpnySB", inline=True)
        await helpers.send(ctx,embed=emb)


    @subcommand("bot")
    @slash_command(description="Show some info about the bot")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot about")
    @command_utils.took_too_long()
    async def about(self, ctx: ApplicationContext):
        emb = helpers.Embed(title="BOT INFO")
        emb.add_field(name="User Linked", value=f"`{await Database.select_counter_user_linked()}`", inline=True)
        emb.add_field(name="Guild Linked", value=f"`{await Database.select_counter_guild_linked()}`", inline=True)
        emb.add_field(name="Servers", value=f"`{len(self.client.guilds)}`", inline=True)
        emb.add_field(name="Developer's discord", value="`algol6`", inline=True)
        emb.add_field(name="Bot Version", value=f"`v2.0.0`", inline=True)
        emb.set_footer(text="Praise to DPS!")
        await helpers.send(ctx,embed=emb)

    @subcommand("bot")
    @slash_command(description="Get the bot to your server. It send link to add the bot to a server")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot invite")
    @command_utils.took_too_long()
    async def invite(self, ctx: ApplicationContext):
        emb = helpers.Embed(title="Invite Algol-Bot", description="Want to add this bot in your server?")
        emb.add_field(name="", value="You can use [THIS LINK](https://discord.com/oauth2/authorize?client_id=1232635599262056479&permissions=2147491856&integration_type=0&scope=bot) to invite this bot in your server.")
        await helpers.send(ctx,embed=emb)


    @subcommand("bot")
    @slash_command(description="Show the latency of the bot")
    @command_utils.auto_defer()
    @command_utils.statistics("/bot ping")
    @command_utils.took_too_long()
    async def ping(self, ctx: ApplicationContext):
        if round(self.client.latency * 1000) <= 50:
            embed=helpers.Embed(title="PING", description=f"The ping is **{round(self.client.latency *1000)}** milliseconds!", color=0x44ff44)
        elif round(self.client.latency * 1000) <= 100:
            embed=helpers.Embed(title="PING", description=f"The ping is **{round(self.client.latency *1000)}** milliseconds!", color=0xffd000)
        elif round(self.client.latency * 1000) <= 200:
            embed=helpers.Embed(title="PING", description=f" The ping is **{round(self.client.latency *1000)}** milliseconds!", color=0xff6600)
        else:
            embed=helpers.Embed(title="PING", description=f"The ping is **{round(self.client.latency *1000)}** milliseconds!", color=0x990000)
        await ctx.respond(embed=embed)
    


def setup(client:Bot):
    client.add_cog(Extra(client))
