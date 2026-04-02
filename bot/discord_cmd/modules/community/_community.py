from discord import ApplicationContext, slash_command, Bot, guild_only, option, TextChannel, Forbidden, User, Member
from discord.ext import tasks, commands
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.api.model import PlayerInfo
from bot.database import Database
from bot.database.model import EventTeam,UserStat
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.modules.community._tasks import CommunityTasks
from bot.discord_cmd.modules.community._market_list_view import MarketListView
from bot.discord_cmd.modules.community._my_list_view import MyListView
from bot.discord_cmd.modules.community._item_info_dialog import ItemModal
from bot.discord_cmd.modules.community._confirm_view import ConfirmButton

from datetime import time, datetime, timezone
from random import shuffle
from collections import Counter, defaultdict

class Community(commands.Cog):
    def __init__(self, client:Bot) -> None:
        self.client = client

    # TODO: Make a setting to se a channel where you can get a message when someone add an item to the market
    # Add that message to the cleanup db 7 days
    # if the item is removed change update the clean up time to 0, so it get deleted in the next check
    @subcommand("admin market")
    @slash_command(description="Set a channel where get players selling messages")
    @guild_only()
    @permissions.require_linked_account()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin market set_market_notice")
    @command_utils.took_too_long()
    async def set_market_notice(self, ctx: ApplicationContext, channel:TextChannel):
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Exception:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")
        if not await Database.insert_market_notice(ch.id):
            return await helpers.send(ctx,content="Error while adding the channel into database")
        await helpers.send(ctx,content="Channel setted up, sending items already listed...")
        count = await Database.select_count_all_market()
        if count == 0:
            return
        view = ConfirmButton()
        view.channel = ch
        await view.send(ctx)

    @subcommand("admin market")
    @slash_command(description="Remove the market channel")
    @guild_only()
    @permissions.require_linked_account()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin market rm_market_notice")
    @command_utils.took_too_long()
    async def rm_market_notice(self, ctx: ApplicationContext, channel:TextChannel):
        await Database.delete_market_notice(channel.id)
        await helpers.send(ctx,content="Removed setting from the channel")


    @subcommand("market")
    @slash_command(description="Show listed items")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/market my_listing")
    @command_utils.took_too_long()
    async def my_listing(self, ctx: ApplicationContext):
        is_empty,data = helpers.gen_is_empty(await Database.select_market_by_user(ctx.user.id))
        if is_empty:
            return await ctx.followup.send("You have no item listed, use '/market sell' to add one.")
        view = MyListView()
        view.data = tuple(data)
        await view.send(ctx)
    
    @subcommand("market")
    @slash_command(description="Add an item to sell")
    @guild_only()
    @option(name="category",choices=["Weapons","Armour","Items","Pets","Amulets","Shields","Boots","Helmets","Collectables","Avatars","Materials","Sprites","Greaves","Gaunlets","Backgrounds","Specials","Tools","Potions","Event Materials","Pleb","Misc"])
    @permissions.require_linked_account()
    @command_utils.statistics("/market sell")
    @command_utils.took_too_long()
    async def sell(self, ctx: ApplicationContext, category:str):
        modal = ItemModal(title="Listing Info")
        modal.client = self.client
        modal.category = category
        modal.author_id = ctx.user.id
        modal.author_smmo_id = ctx.discord_user.smmo_id
        profile = await helpers.get_user(ctx)
        modal.author_name = profile.name
        modal.time = int(datetime.now().timestamp())
        await ctx.send_modal(modal)

    @subcommand("market")
    @slash_command(description="Show listed items", name="list")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/market list")
    @command_utils.took_too_long()
    async def market_list(self, ctx: ApplicationContext):
        view = MarketListView()
        view.data = tuple([tuple(await Database.select_market_by_cat(x)) for x in range(21)])
        await view.send(ctx)
        
    
def setup(client:Bot):
    client.add_cog(Community(client))
    client.add_cog(CommunityTasks(client))
    