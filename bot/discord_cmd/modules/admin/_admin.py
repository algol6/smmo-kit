from discord import Bot, ApplicationContext, guild_only, slash_command, TextChannel, Role, option
from discord.errors import Forbidden
from discord.ext.commands import Cog
from pycord.multicog import subcommand
from datetime import datetime, timedelta

from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.modules.guild._requirements_view import RequirementsView
from bot.database.model import Requirements
from bot.discord_cmd.modules.admin._tasks import AdminTask

class Admin(Cog):
    def __init__(self, client) -> None:
        self.client = client

    @subcommand("admin")
    @slash_command(description="Analize last 7 days of the guild and suggest best task to gain pp/gxp")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/admin task_calc")
    @command_utils.took_too_long()
    async def task_calc(self, ctx:ApplicationContext) -> None:
        members = await SMMOApi.get_guild_members(ctx.user_guild_id)
        total_stats = [0, 0] # [steps, npc_k]
        date = datetime.now() - timedelta(days=7)

        for m in members:
            past_stats = await Database.select_user_stat(m.user_id,date.year,date.month,date.day)
            if not past_stats:
                logger.warning("Stats of 7 days ago for user %s(%s) not found. Skipping user...",m.name,m.user_id)
                continue
            total_stats[0] += m.steps - past_stats.steps
            total_stats[1] += m.npc_kills - past_stats.npc_kills
        total_cost = 0
        total_pp_gained = 0
        total_xp_gained = 0
        best_cost = {}
        best_pp = {}
        best_xp = {}
        TASK_LIST = (
            {"req": 7500, "pp": 25, "xp": 75000, "cost": 8000000, "type": "npc"},
            {"req": 5000, "pp": 13, "xp": 40000, "cost": 5000000, "type": "npc"},
            {"req": 3850, "pp": 8, "xp": 15000, "cost": 4000000, "type": "npc"},
            {"req": 2700, "pp": 4, "xp": 5000, "cost": 2800000, "type": "npc"},
            {"req": 1500, "pp": 2, "xp": 2500, "cost": 1500000, "type": "npc"},
            {"req": 500, "pp": 1, "xp": 1000, "cost": 1000000, "type": "npc"},
            {"req": 30000, "pp": 10, "xp": 75000, "cost": 8000000, "type": "step"},
            {"req": 19000, "pp": 3, "xp": 40000, "cost": 5000000, "type": "step"},
            {"req": 14500, "pp": 2, "xp": 15000, "cost": 4000000, "type": "step"},
            {"req": 10000, "pp": 1, "xp": 6500, "cost": 2800000, "type": "step"},
            {"req": 5500, "pp": 0, "xp": 2500, "cost": 1500000, "type": "step"},
            {"req": 2000, "pp": 0, "xp": 1000, "cost": 1000000, "type": "step"},
        )
        daily_raids = 0
        for task in TASK_LIST:
            if task["type"] == "npc":
                id = 1
            else:
                id = 0
            times_done = total_stats[id] // task["req"]
            if total_cost == 0 or total_cost > times_done * task["cost"]:
                total_cost = times_done * task["cost"]
                best_cost = task
            if total_pp_gained < times_done * task["pp"]:
                total_pp_gained = times_done * task["pp"]
                best_pp = task
                daily_raids = (total_pp_gained // 7) // 24
            if total_xp_gained < times_done * task["xp"]:
                total_xp_gained = times_done * task["xp"]
                best_xp = task
        emb = helpers.Embed(title="Best Task based on the past 7 days")

        if best_cost == best_pp == best_xp:
            emb.add_field(
                name="Best Task",
                value=f"Type: {best_cost['type'].upper()}\nQuantity: {best_cost['req']:,}",
            )
        else:
            emb.add_field(
                name="Cheaper Task",
                value=f"Type: {best_cost['type'].upper()}\nQuantity: {best_cost['req']:,}",
                inline=False
            )
            emb.add_field(
                name="Best Gxp Gain",
                value=f"Type: {best_xp['type'].upper()}\nQuantity: {best_xp['req']:,}",
                inline=False
            )
            emb.add_field(
                name="Best PP Gain",
                value=f"Type: {best_pp['type'].upper()}\nQuantity: {best_pp['req']:,}\nThe last 7 days with this task you would have gained enough to mantain {int(daily_raids)} daily raids",
                inline=False
            )
        await helpers.send(ctx,embed=emb)

    @subcommand("admin")
    @slash_command(description="Set a message for vault code")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin set_vault_ping")
    @command_utils.took_too_long()
    async def set_vault_ping(self,ctx:ApplicationContext,channel:TextChannel=None,role:Role=None)->None:
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")

        if not await Database.insert_valutmsg(channel.id, role.id if role else None):
            return await helpers.send(ctx,content="Message already setted.")
        await helpers.send(ctx,content="Ping set.")

    @subcommand("admin")
    @slash_command(description="Remove the message for vault code from a channel")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin remove_vault_ping")
    @command_utils.took_too_long()
    async def remove_vault_ping(self,ctx:ApplicationContext,channel:TextChannel=None)->None:
        if channel is None:
            channel = ctx.channel
        await Database.delete_valutmsg(channel.id)
        await helpers.send(ctx,content="Ping removed.")

    @subcommand("admin")
    @slash_command(description="Set a ping to remind of monthly in-game reward")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin add_monthly_reward_ping")
    @command_utils.took_too_long()
    async def add_monthly_reward_ping(self,ctx:ApplicationContext,role:Role,channel:TextChannel=None)->None:
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")

        if not await Database.insert_monthly_reward(role.id, channel.id):
            return await helpers.send(ctx,content="Ping already setted.")
        await helpers.send(ctx,content="Ping setted.")

    @subcommand("admin")
    @slash_command(description="Remove the monthly in-game reward ping")
    @guild_only()
    @command_utils.auto_defer()
    @command_utils.took_too_long()
    @command_utils.statistics("/admin remove_monthly_reward_ping")
    @permissions.require_admin_or_staff()
    async def remove_monthly_reward_ping(self,ctx:ApplicationContext,channel:TextChannel=None) -> None:
        if channel is None:
            channel = ctx.channel
        await Database.delete_monthly_reward(channel.id)
        await helpers.send(ctx,content="Ping removed.")

    @subcommand("admin")
    @slash_command(description="Add a role that can be considered admin by the bot")
    @guild_only()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin role_add")
    @command_utils.took_too_long()
    async def role_add(self,ctx:ApplicationContext,role:Role) -> None:
        if not await Database.insert_staff(ctx.user_guild_id, role.id):
            return await helpers.send(ctx,content="Role already added")
        await helpers.send(ctx,content="Role added.")

    @subcommand("admin")
    @slash_command(description="Remove a role that was considered admin by the bot.")
    @guild_only()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin role_remove")
    @command_utils.took_too_long()
    async def role_remove(self,ctx:ApplicationContext,role:Role) -> None:
        await Database.delete_staff(ctx.user_guild_id, role.id)
        await helpers.send(ctx,content="Role removed.")

    @subcommand("admin")
    @slash_command(description="Show the roles that are considered admin by the bot.")
    @guild_only()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer(ephemeral=False)
    @command_utils.statistics("/admin roles")
    @command_utils.took_too_long()
    async def roles(self,ctx:ApplicationContext) -> None:
        roles = await Database.select_staff(ctx.user_guild_id)
        is_empty,roles=helpers.gen_is_empty(roles)
        error: bool = False
        if is_empty:
            emb: helpers.Embed = helpers.Embed(title="No roles to consider staff for this bot in this server")
        else:
            emb: helpers.Embed = helpers.Embed(title="Staff Roles")
            for x, i in zip(roles, range(25)):
                emb.add_field(name="", value=f"<@&{x.role_id}>\n")
                if i >= 24:
                    error = True
                    break
        if error:
            emb.set_footer(text="*The command can't show more than 25 roles*")
        await helpers.send(ctx,embed=emb)

    @subcommand("admin link")
    @slash_command(description="You can link the server with the guild")
    @guild_only()
    @permissions.require_linked_account()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin link server")
    @command_utils.took_too_long()
    async def server(self,ctx:ApplicationContext,guild_id:int) -> None:
        player = ctx.user_game_profile if "user_game_profile" in ctx else await SMMOApi.get_player_info(ctx.discord_user.smmo_id)
        guild_members = await SMMOApi.get_guild_members(guild_id)
        if player.guild is not None and player.guild.id == guild_id and any(x.position != "Member" for x in guild_members if player.id == x.user_id):
            if not await Database.insert_server(guild_id, ctx.guild_id):
                logger.Warning("Can't insert guild_id into Database")
                return await helpers.send(ctx,"Error.")
            return await helpers.send(ctx,"Server added")
        await helpers.send(ctx,"You need to be in a guild or be the Leader/colead/officer to link it to a discord server.")

    @subcommand("admin guilds")
    @slash_command(description="Set guild requirement.")
    @guild_only()
    @option(name="days",description="ex: 7 to check the user who didn't meet req during the past 7days",required=True)
    @option(name="levels", description="Set to 0 to ignore this stats",default=0)
    @option(name="npc", description="Set to 0 to ignore this stats",default=0)
    @option(name="pvp", description="Set to 0 to ignore this stats",default=0)
    @option(name="steps", description="Set to 0 to ignore this stats",default=0)
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin set_members_req")
    @command_utils.took_too_long()
    async def set_members_req(self,ctx:ApplicationContext,days:int,levels:int=0,npc:int=0,pvp:int=0,steps:int=0):
        if not await Database.insert_requirements(ctx.user_guild_id, days, levels, npc, pvp, steps):
            return await helpers.send(ctx,content="Requirements already added for this guild.\nRemove first before adding again")
        await helpers.send(ctx,content="Requirements saved.")

    @subcommand("admin guilds")
    @slash_command(description="Remove guild requirement.")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin remove_member_req")
    @command_utils.took_too_long()
    async def remove_member_req(self,ctx:ApplicationContext):
        await Database.delete_requirements(ctx.user_guild_id)
        await helpers.send(ctx,content="Requirements removed.")

    @subcommand("admin guilds")
    @slash_command(description="Show members that are under the requirement")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/admin check_req")
    @command_utils.took_too_long()
    async def check_req(self,ctx:ApplicationContext,days:int=0,levels:int=0,npc:int=0,pvp:int=0,steps:int=0,ignore_staff:bool=True):
        req = await Database.select_requirements(ctx.user_guild_id)

        if all(v == 0 for v in [days, levels, npc, pvp, steps]) and req is None:
            return await helpers.send(ctx,content="Set requirements or add manually the parameters in the command")
        if days is None and req is None:
            return await helpers.send(ctx,content="Days is required.")
        if all(v is None for v in [req, levels, npc, pvp, steps]):
            return await helpers.send(ctx,content="Required at least one parameter *(levels,npc,pvp or steps)*")
        if days == 0 and req is not None:
            days = req.days
        if levels == 0 and req is not None:
            levels = req.levels
        if npc == 0 and req is not None:
            npc = req.npc
        if pvp == 0 and req is not None:
            pvp = req.pvp
        if steps == 0 and req is not None:
            steps = req.steps

        req = Requirements(ctx.user_guild_id, days, levels, npc, pvp, steps)

        is_empty,guild_members = helpers.gen_is_empty(await SMMOApi.get_guild_members(req.guild_id))
        safe_users = await Database.select_safe_user(req.guild_id)

        if is_empty:
            return await ctx.followup.send(content="Error when getting members list")

        date = helpers.get_current_date_game() - timedelta(days=req.days)
        la: list = []
        lvl: list = []
        np: list = []
        pv: list = []
        st: list = []
        for member in guild_members:
            if any(member.user_id == v.smmo_id for v in safe_users):
                continue
            if ignore_staff and member.position != "Member":
                continue
            if member.last_activity <= (datetime.now().timestamp() - req.days * 86400):
                la.append(
                    {
                        "name": member.name,
                        "value": member.last_activity,
                        "id": member.user_id,
                    }
                )
            member_stats = await Database.select_user_stat(member.user_id, date.year, date.month, date.day)
            if member_stats is None:
                continue

            if req.levels != 0 and member.level - member_stats.level < req.levels and member.level - member_stats.level >= 0:
                lvl.append(
                    {
                        "name": member.name,
                        "value": member.level - member_stats.level,
                        "id": member.user_id,
                    }
                )
            if req.npc != 0 and member.npc_kills - member_stats.npc_kills < req.npc:
                np.append(
                    {
                        "name": member.name,
                        "value": member.npc_kills - member_stats.npc_kills,
                        "id": member.user_id,
                    }
                )
            if req.pvp != 0 and member.user_kills - member_stats.user_kills < req.pvp:
                pv.append(
                    {
                        "name": member.name,
                        "value": member.user_kills - member_stats.user_kills,
                        "id": member.user_id,
                    }
                )
            if req.steps != 0 and member.steps - member_stats.steps < req.steps:
                st.append(
                    {
                        "name": member.name,
                        "value": member.steps - member_stats.steps,
                        "id": member.user_id,
                    }
                )

        req_view = RequirementsView()
        req_view.ignore_staff = ignore_staff
        req_view.req = req
        req_view.last_activity = la
        req_view.data = (
            sorted(la, key=lambda item: item["value"]),
            sorted(lvl, key=lambda item: item["value"]),
            sorted(np, key=lambda item: item["value"]),
            sorted(pv, key=lambda item: item["value"]),
            sorted(st, key=lambda item: item["value"])
        )
        await req_view.send(ctx)

    @subcommand("admin guilds")
    @slash_command(description="Show safe list. (player to ignore when checking requirements)")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin req_safe_list")
    @command_utils.took_too_long()
    async def req_safe_list(self,ctx:ApplicationContext):
        safe_users = await Database.select_safe_user(ctx.user_guild_id)
        emb = helpers.Embed(title="Safe Users List:")
        no_user: bool = True
        msg:str = ""
        for user in safe_users:
            player = await SMMOApi.get_player_info(user.smmo_id)
            if player is not None:
                msg += f"({player.id}) {player.name}\n"
                no_user = False
        emb.add_field(name="",value="No user in the safe list." if no_user else msg)
        await helpers.send(ctx,embed=emb)

    @subcommand("admin guilds")
    @slash_command(description="Add user to safe list")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin req_add_safe_list")
    @command_utils.took_too_long()
    async def req_add_safe_list(self,ctx:ApplicationContext,smmo_id:int):
        player = helpers.get_user(smmo_id=smmo_id)
        if player is None:
            return await helpers.send(ctx,content="Player not found.")
        if not await Database.insert_safe_user(smmo_id, ctx.user_guild_id):
            return await helpers.send(ctx,content="Player already in the safe list")
        await helpers.send(ctx,content=f"Player '{player.name}' added to safe list.")

    @subcommand("admin guilds")
    @slash_command(description="Remove user to safe list")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin req_remove_safe_list")
    @command_utils.took_too_long()
    async def req_remove_safe_list(self,ctx:ApplicationContext,smmo_id:int):    
        await Database.delete_safe_user(smmo_id, ctx.user_guild_id)
        return await helpers.send(ctx,content="Player removed.")
    
    @subcommand("admin guilds")
    @slash_command(description="Set a daily message that show top 25 guild gains")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin set_daily_gains_lb")
    @command_utils.took_too_long()
    async def set_daily_gains_lb(self,ctx:ApplicationContext,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")
        message = await channel.send(content="The gains lb will be setted here.")
        if not await Database.insert_gains_leaderboard(channel.id, message.id):
            return await helpers.send(ctx,content="Already set")
        await helpers.send(ctx,content="Done")

    @subcommand("admin guilds")
    @slash_command(description="Remove the daily message that show top 25 guild gains")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin remove_daily_gains_lb")
    @command_utils.took_too_long()
    async def remove_daily_gains_lb(self,ctx:ApplicationContext,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        await Database.delete_gains_leaderboard(channel.id)
        await helpers.send(ctx,content="Done")

    @subcommand("admin guilds")
    @slash_command(description="Set a daily message that show top top 5 members")
    @guild_only()
    @permissions.require_linked_server()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin set_daily_member_lb")
    @command_utils.took_too_long()
    async def set_daily_member_lb(self,ctx:ApplicationContext,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        try:
            ch = await self.client.fetch_channel(channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")
        message = await channel.send(content="The member lb will be setted here.")
        if not await Database.insert_lb(channel.id, message.id, await Database.select_server(ctx.guild_id),helpers.get_current_date_game().strftime("%d/%m/%Y")):
            return await helpers.send(ctx,content="Already set")
        await helpers.send(ctx,content="Done")

    @subcommand("admin guilds")
    @slash_command(description="Remove the daily message of top 5 members")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin remove_daily_member_lb")
    @command_utils.took_too_long()
    async def remove_daily_member_lb(self,ctx:ApplicationContext,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        await Database.delete_lb(channel.id)
        await helpers.send(ctx,content="Done")

def setup(client: Bot):
    client.add_cog(Admin(client))
    client.add_cog(AdminTask(client))
