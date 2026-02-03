from discord import slash_command, ApplicationContext,AutocompleteContext, Bot, guild_only, option, Role, TextChannel
from discord.ext.commands import Cog
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.database import Database
from bot.api.model import GuildSeasonLeaderboard, GuildMemberInfo, PlayerInfo
from bot.database.model import UserStat, Requirements
from bot.discord_cmd.modules.guild._advleaderboard_view import AdvleaderboardView
from bot.discord_cmd.modules.guild._member_list_view import MemberListView
from bot.discord_cmd.modules.guild._contribution_view import ContributionView
from bot.discord_cmd.modules.guild._contribution_dialog import ContributionModal
from bot.discord_cmd.modules.guild._war_target_view import WarTargetView
from bot.discord_cmd.modules.guild._guild_gains_view import GuildGainsView
from bot.discord_cmd.modules.guild._tasks import GuildTask
from bot.discord_cmd.helpers import permissions, command_utils, logger, helpers

from random import random, choice
from datetime import datetime, time, date, timezone, timedelta
from math import floor
from matplotlib import pyplot as plt
import pandas as pd

# TODO: do graph command but show only one guild all time xp across seasons

        
class Guild(Cog):
    def __init__(self, client):
        self.client:Bot = client

    @subcommand("guild")
    @slash_command(description="Get the best exp gains the guild has ever done")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild overall")
    @command_utils.took_too_long()
    async def overall(self,ctx:ApplicationContext,guild_id:int=None):
        if guild_id is None:
            guild_id = ctx.user_guild_id
        guild = await SMMOApi.get_guild_info(guild_id)
        if guild is None:
            return await helpers.send(ctx,content="Guild id not found")
        data = await Database.select_best_experience_gain(guild_id)
        if data is None:
            return await helpers.send(ctx,content="No data found")
        emb = helpers.Embed(title=f"{guild.name}'s Overall", description="Most Experience gained in a day:", thumbnail=f"https://simple-mmo.com/img/icons/{guild.icon}")
        for d in data:
            emb.add_field(name="", 
                        value=f"<t:{int(d.time)}>-<t:{int((datetime(d.year,d.month,d.day,11,59)+timedelta(days=1)).timestamp())}>\n**Experience**: +{format(d.experience,",d")}",
                        inline=False)
        emb.set_footer(text="Data limited to that saved in the Database.")
        await helpers.send(ctx,embed=emb)

    @subcommand("admin guilds")
    @slash_command(description="Set a timer for your raid")
    @guild_only()
    @option(name="duration", choices=[1,2,4,8,12,24])
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin guild raid_set_ping")
    @command_utils.took_too_long()
    async def raid_set_ping(self,ctx:ApplicationContext,role:Role,duration:int,channel:TextChannel=None):
        if channel is None:
            channel = ctx.channel
        if not await Database.insert_raid(channel.id,datetime.now().timestamp(),duration,role.id):
            return await helpers.send(ctx,content="A raid ping is already set in this channel. remove it if you want to add another")
        await helpers.send(ctx,content="Once the timer is up, the bot will send the message to ping")

    @subcommand("admin guilds")
    @slash_command(description="Remove a timer for your raid")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin guild raid_remove_ping")
    @command_utils.took_too_long()
    async def raid_remove_ping(self,ctx:ApplicationContext,channel:TextChannel):
        await Database.delete_raid(channel.id)
        await helpers.send(ctx,content="Raid ping removed.")

    @subcommand("guild")
    @slash_command(description="Show the staff(Leader,Co-leaders,Officers) of the guild")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild staff")
    @command_utils.took_too_long()
    async def staff(self,ctx:ApplicationContext) -> None:
        embed = helpers.Embed(title="Staff list")
        guild_member = await SMMOApi.get_guild_members(ctx.user_guild_id)
        x = {"Leader":"","Co-leader":[],"Officer":[]}
        for member in guild_member:
            if member.position == "Leader":
                bot_user = await Database.select_user_smmoid(member.user_id)
                x["Leader"] = f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}"
            if member.position == "Co Leader":
                bot_user = await Database.select_user_smmoid(member.user_id)
                x["Co-leader"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")
            if member.position == "Officer":
                bot_user = await Database.select_user_smmoid(member.user_id)
                x["Officer"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")
        embed.add_field(name="Leader", value=x["Leader"], inline=False)
        if len(x["Co-leader"]) != 0:
            if len(x["Co-leader"]) >= 1024:
                msg:str = ""
                for i,v in enumerate(x["Co-leader"]):
                    msg += f"\n{v}"
                    if (i + 1 % 5) == 0:
                        embed.add_field(name="Co-leader", value=msg, inline=False)
                        msg = ""
            else:
                embed.add_field(name="Co-leader", value="\n".join(x["Co-leader"]), inline=False)

        if len(x["Officer"]) != 0:
            if len(x["Officer"]) >= 1024:
                msg:str = ""
                for i,v in enumerate(x["Officer"]):
                    msg += f"\n{v}"
                    if (i + 1 % 5) == 0:
                        embed.add_field(name="Officer", value=msg, inline=False)
                        msg = ""
            else:
                embed.add_field(name="Officer", value="\n".join(x["Officer"]), inline=False)
        await helpers.send(ctx,embed=embed)
    
    @subcommand("guild")
    @slash_command(description="Show the members of the guild")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild members")
    @command_utils.took_too_long()
    async def members_list(self,ctx:ApplicationContext) -> None:
        guild_member = await SMMOApi.get_guild_members(ctx.user_guild_id)
        guild_info = await SMMOApi.get_guild_info(ctx.user_guild_id)
        x:list[str] = []
        x:dict = {"Leader":[],"Co-leader":[],"Officer":[],"Member":[]}
        for member in guild_member:
            bot_user = await Database.select_user_smmoid(member.user_id)
            if member.position == "Leader":
                x["Leader"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}) (**Lvl**:{member.level:,}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")
            if member.position == "Co Leader":
                x["Co-leader"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}) (**Lvl**:{member.level:,}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")
            if member.position == "Officer":
                x["Officer"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}) (**Lvl**:{member.level:,}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")

            x["Member"].append(f"[{member.name}](https://simple-mmo.com/user/view/{member.user_id}) (**Lvl**:{member.level:,}){f" <@{bot_user.discord_id}>" if bot_user is not None else ""}")
            
        mblist_view = MemberListView()
        mblist_view.data = x
        mblist_view.icon = guild_info.icon
        mblist_view.name = guild_info.name
        mblist_view.updated = int(datetime.now().timestamp())
        await mblist_view.send(ctx)

    @subcommand("guild")
    @slash_command(description="Show the leaderboard of current season")
    @guild_only()
    @option(name="number", min_value=10, max_value=50, description="How many guild show in the top list.")
    @command_utils.auto_defer()
    @command_utils.statistics("/guild lb")
    @command_utils.took_too_long()
    async def lb(self,ctx:ApplicationContext,number:int=10) -> None:
        season_id = await helpers.get_current_season_id()
        is_empty,season_lb = helpers.gen_is_empty(await SMMOApi.get_guild_season_leaderboard(season_id))
        if is_empty:
            return await helpers.send(ctx,"No data found. try again later")
        msg: str = "\n".join(f"#{x.position} **[{x.guild["name"]}](https://simple-mmo.com/guilds/view/{x.guild["id"]})** ({format(x.experience, ",d")} gxp)" for x,_ in zip(season_lb,range(number)))
        embed = helpers.Embed(title=f"Top {number} Guilds")
        if len(msg) >= 1024:
            final_msg = msg.split("\n")
            msg2 = ""
            for i in range(1,len(final_msg)+1):
                msg2 += f"{final_msg[i-1]}\n"
                if i%5==0 or i == len(final_msg):
                    embed.add_field(name="", value=msg2, inline=False)
                    msg2 = ""
        else:
            embed.add_field(name="",value=msg,inline=False)
    
        await helpers.send(ctx,embed=embed)

    
    @subcommand("guild")
    @slash_command(description="Show war info of the guild")
    @guild_only()
    @option(name="guild_target", description="Target Guild ID", autocomplete=helpers.get_war_guild)
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild war_target")
    @command_utils.took_too_long()
    async def war_target(self,ctx:ApplicationContext,guild_target:str) -> None:
        if guild_target is None:
            return await helpers.send(ctx,content="Insert guild_target")
        guild_id = guild_target.split("-")[-1].strip()
        if not guild_id.isdigit():
            return await helpers.send(ctx,content="Guild ID not found")
        guild = await SMMOApi.get_guild_info(guild_id)
        if guild is None:
            return await helpers.send(ctx,content="Guild not found")

        guild_members = await SMMOApi.get_guild_members(guild_id)
        targets = []
        for member in guild_members:
            if member.safe_mode:
                continue
            targets.append(await SMMOApi.get_player_info(member.user_id))

        if len(targets) == 0:
            return helpers.send(ctx,content="No Player without safe mode found")
        target_view = WarTargetView()
        target_view.data = (
            (x for x in targets if x.hp >= x.max_hp/2),
            sorted(targets,key=lambda item: item.hp/item.max_hp)
        )
        target_view.guild_info = guild
        target_view.updated = datetime.now()
        await target_view.send(ctx)

    @subcommand("guild")
    @slash_command(description="Show war progress of the guild(works only with top 50 guilds)")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild wars")
    @command_utils.took_too_long()
    async def wars(self, ctx: ApplicationContext, guild_id: int = None, war_xp:bool = False) -> None:
        if guild_id is None:
            guild_id = ctx.user_guild_id
        season_id: int = await helpers.get_current_season_id()
        season_lb = await SMMOApi.get_guild_season_leaderboard(season_id)

        embed = helpers.Embed(title="Guild Leaderboard Stats")
        x = True
        prev = None
        for c, v in enumerate(season_lb):
            if v.guild["id"] == guild_id:
                x = False
                if c != 0:
                    previus_guild = await SMMOApi.get_guild_info(prev.guild["id"])
                    embed.add_field(
                        name="Previous guild",
                        value=await helpers.make_wars_emb(previus_guild, c, v, prev, war_xp,True),
                        inline=False
                        )
                
                cur_guild = await SMMOApi.get_guild_info(guild_id)
                msg: str = await helpers.make_wars_emb(cur_guild, c, v, season_lb, war_xp)
                embed.add_field(
                    name=v.guild["name"],
                    value=msg
                )
                if c < 49:
                    s_guild = next(season_lb)
                    successive_guild = await SMMOApi.get_guild_info(s_guild.guild["id"])
                    embed.add_field(
                        name="Successive guild",
                        value=await helpers.make_wars_emb(successive_guild, c, v, s_guild, war_xp,False),
                        inline=False
                        )
                break
            prev = v
        if x:
            return await helpers.send(ctx,content="Wrong id, or guild not in guild leaderboard")
        await helpers.send(ctx,embed=embed)

    @subcommand("guild")
    @slash_command(description="Show the xp gain of the guilds")
    @guild_only()
    @option(name="timeframe", choices=["Daily","Past 7 Days","In-Game Weekly","Yesterday","Monthly","In-Game Monthly"])
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild gains")
    @command_utils.took_too_long()
    async def gains(self, ctx: ApplicationContext, timeframe: str = "Daily") -> None:
        season = await helpers.get_current_season()
        is_empty,season_lb = helpers.gen_is_empty(await SMMOApi.get_guild_season_leaderboard(season.id))
        if is_empty:
            return await helpers.send(ctx,content="No data. Season just started try after server reset")

        date = helpers.get_date_game(timeframe)

        gains_view = GuildGainsView()
        gains_view.season_lb = tuple(season_lb)
        gains_view.timeframe = timeframe
        gains_view.date = date
        gains_view.to_date = helpers.get_current_date_game() if timeframe == "Yesterday" else datetime.now()
        gains_view.season = season
        gains_view.last_update = int(datetime.now().timestamp())
        return await gains_view.send(ctx)
    

    @subcommand("guild members")
    @slash_command(description="Show guild stepping members")
    @guild_only()
    @option(name="who", choices=["Current","All"])
    @option(name="show_names", description="Show the name of the steppers, in the location with few steppers",choices=["Yes","No"])
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild members stepping")
    @command_utils.took_too_long()
    async def stepping(self,ctx:ApplicationContext,who:str="Current",guild_id:int=None,show_names:str="No") -> None:
        if guild_id is None:
            guild_id = ctx.user_guild_id
        members = await SMMOApi.get_guild_members(guild_id)
        message = await helpers.send(ctx,content="List of steppers will be loaded here.")
        embed = helpers.Embed(title=f"Here the location of {"all" if who == "All" else "current"} steppers")
        embed.add_field(name="", value="*Might take up to 10 minutes to load all data.*", inline=False)
        x:dict = {}
        member_count:int=0
        two_minute_ago:int = floor(datetime.now().timestamp()) - 60

        for m in members:
            if who == "Current":
                if m.last_activity >= two_minute_ago:
                    player = await SMMOApi.get_player_info(m.user_id)
                else:
                    continue
                if player.current_location.name in x:
                    x[player.current_location.name]["amount"] += 1
                    x[player.current_location.name]["people"].append(player.name)
                else:
                    x[player.current_location.name] = {"amount":1}
                    x[player.current_location.name]["people"] = [player.name]
                member_count+=1
            elif who == "All":
                player = await SMMOApi.get_player_info(m.user_id)
                if player:
                    if player.current_location.name in x:
                        x[player.current_location.name]["amount"] += 1
                        x[player.current_location.name]["people"].append(player.name)
                    else:
                        x[player.current_location.name] = {"amount":1}
                        x[player.current_location.name]["people"] = [player.name]
            embed.set_field_at(0, name="", value="\n".join(f"**{key}**: {str(value["amount"])} {f"[{",".join(value["people"])}]" if show_names=="Yes" and value["amount"] <= 10 else ""}" for key,value in x.items()))
            embed.set_footer(text="Loading...")
            await message.edit(content="", embed=embed)

        x = dict(sorted(x.items(), key=lambda item: -item[1]["amount"]))

        msg:str = "\n".join(f"**{key}**: {str(value["amount"])} {f"[{",".join(value["people"])}]" if show_names=="Yes" else ""}" for key,value in x.items())

        final_msg = msg.split("\n")
        #msg:str = "\n".join(f"{key}: {str(value)}" for key,value in x.items())
        if who == "Current":
            msg = f"{msg}\n\n**Member stepping: {str(member_count)}**"

        embed.remove_field(0)
        for m in final_msg:
            if len(m) >= 1024:
                from re import sub
                m = sub("[\(\[].*?[\)\]]", "", m)
            embed.add_field(name="",value=m,inline=False)
        embed.set_footer(text="")

        await message.edit(embed=embed)


    @subcommand("guild members")
    @slash_command(description="Show top 5 members stats for each category(lvl,steps,npc,pvp)")
    @guild_only()
    @option(name="timeframe", choices=["Daily","Past 7 Days","In-Game Weekly","Yesterday","Monthly","In-Game Monthly"])
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild members lb")
    @command_utils.took_too_long()
    async def members_lb(self,ctx:ApplicationContext,timeframe:str="Daily",guild_id:int=None,reverse:bool=False) -> None:
        if guild_id is None:
            guild_id = ctx.user_guild_id
        is_empty,guild_members = helpers.gen_is_empty(await SMMOApi.get_guild_members(guild_id))
        guild = await SMMOApi.get_guild_info(guild_id)
        date = helpers.get_date_game(timeframe)
        to_date = helpers.get_current_date_game() 
        if timeframe != "Yesterday":
            to_date += timedelta(days=1)

        if is_empty:
            return await helpers.send(ctx,content="No data found")
        
        season_id = await helpers.get_current_season_id()
        guild_data = await Database.select_guild_stats(guild_id, date.year, date.month,date.day,season_id)

        x:int = guild_data.experience if guild_data is not None else 0
 
        var:list[dict] = []
        total:list[int] = [0,0,0,0]
        
        for m2 in guild_members:
            m_s = await Database.select_user_stat(m2.user_id,date.year,date.month,date.day)
            if timeframe == "Yesterday":
                m_stats = await Database.select_user_stat(m_s,to_date.year,to_date.month,to_date.day)
                if m_stats is not None:
                    m2.level = m_stats.level
                    m2.steps = m_stats.steps
                    m2.npc_kills = m_stats.npc_kills
                    m2.user_kills = m_stats.user_kills
            var.append({"id": m2.user_id,
                        "levels": m2.level - m_s.level,
                        "steps": m2.steps - m_s.steps,
                        "npc_kills": m2.npc_kills - m_s.npc_kills,
                        "user_kills": m2.user_kills - m_s.user_kills,
                        "name": m2.name})
            total[0] += m2.steps - m_s.steps
            total[1] += m2.npc_kills - m_s.npc_kills
            total[2] += m2.user_kills - m_s.user_kills
            total[3] += m2.level - m_s.level
            
        emb = helpers.Embed(title=f"Members leaderboard",
                            description=f"**Stats**: from <t:{int(date.timestamp())}> to <t:{int(to_date.timestamp())}>\n"
                                        f"**Last update**: <t:{int(datetime.now().timestamp())}:R>\n"
                                        f"**Guild**: {guild.name}\n"
                                        f"**Exp**: {format(guild.current_season_exp,",d")} (+{guild.current_season_exp-x:,})",
                            thumbnail=f"https://simple-mmo.com/img/icons/{guild.icon}")
        emb.add_field(name=f"Steps: (Total: {total[0]:,})",
                      value="\n".join(f"[{x["name"]}](https://simple-mmo.com/user/view/{x["id"]}): {x["steps"]:,}" for x in sorted(var, key=lambda member: (member["steps"]),reverse=not reverse)[:5]),
                      inline=False)
        emb.add_field(name=f"NPC: (Total: {total[1]:,})",
                      value="\n".join(f"[{x["name"]}](https://simple-mmo.com/user/view/{x["id"]}): {x["npc_kills"]:,}" for x in sorted(var, key=lambda member: (member["npc_kills"]),reverse=not reverse)[:5]),
                      inline=False)
        emb.add_field(name=f"PVP: (Total: {total[2]:,})",
                      value="\n".join(f"[{x["name"]}](https://simple-mmo.com/user/view/{x["id"]}): {x["user_kills"]:,}" for x in sorted(var, key=lambda member: (member["user_kills"]),reverse=not reverse)[:5]),
                      inline=False)
        emb.add_field(name=f"Levels: (Total: {total[3]:,})",
                      value="\n".join(f"[{x["name"]}](https://simple-mmo.com/user/view/{x["id"]}): {x["levels"]:,}" for x in sorted(var, key=lambda member: (member["levels"]),reverse=not reverse)[:5]),
                      inline=False)
        await helpers.send(ctx,embed=emb)


    @subcommand("guild members")
    @slash_command(description="Show the stats of the guild")
    @permissions.require_linked_server()
    @guild_only()
    @option(name="timeframe",choices=["Past 7 Days","In-Game Weekly","Yesterday","Monthly","In-Game Monthly"])
    @option(name="from_date", description="Write data in format dd/mm/yyyy. default 7 days ago")
    @option(name="to_date", description="Write data in format dd/mm/yyyy. default today.")
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild members advlb")
    @command_utils.took_too_long()
    async def advlb(self,ctx:ApplicationContext,timeframe:str="Yesterday",from_date:str=None,to_date:str=None,guild_id:int=None) -> None:
        if guild_id is None:
            guild_id = await Database.select_server(ctx.guild_id)
        if from_date:
            try:
                s_date = datetime.strptime(from_date, "%d/%m/%Y")
            except:
                return await helpers.send(ctx,content="Wrong date format. use dd/mm/yyyy format")
        else:
            s_date = helpers.get_date_game(timeframe)
        
        if to_date is None:
            e_date = helpers.get_current_date_game()
        else:
            try:
                e_date = datetime.strptime(to_date, "%d/%m/%Y")
            except:
                return await helpers.send(ctx,content="Wrong date format. use dd/mm/yyyy format")

        members = await SMMOApi.get_guild_members(guild_id)
        da = [[[],[],[],[]],[[],[],[],[]],[[],[],[],[]],[[],[],[],[]],[[],[],[],[]],[[],[],[],[]],[[],[],[],[]],[[],[],[],[]]]
        for m in members:
            d1 = await Database.select_user_stat(m.user_id,s_date.year,s_date.month,s_date.day)
            d2 = await Database.select_user_stat(m.user_id,e_date.year,e_date.month,e_date.day)
            if d1 is None or d2 is None:
                continue

            if m.level <= 25:
                index = 1
            elif m.level <= 100:
                index = 2
            elif m.level <= 500:
                index = 3
            elif m.level <= 1000:
                index = 4
            elif m.level <= 5000:
                index = 5
            elif m.level <= 10000:
                index = 6
            else:
                index = 7

            da[index][0].append({"name":m.name, "stats": d2.npc_kills - d1.npc_kills, "id":d1.smmo_id})
            da[0][0].append({"name":m.name, "stats": d2.npc_kills - d1.npc_kills, "id":d1.smmo_id})

            da[index][1].append({"name":m.name, "stats": d2.user_kills - d1.user_kills, "id":d1.smmo_id})
            da[0][1].append({"name":m.name, "stats": d2.user_kills - d1.user_kills, "id":d1.smmo_id})

            da[index][2].append({"name":m.name, "stats": d2.steps - d1.steps, "id":d1.smmo_id})
            da[0][2].append({"name":m.name, "stats": d2.steps - d1.steps, "id":d1.smmo_id})

            da[index][3].append({"name":m.name, "stats": d2.level - d1.level if d2.level - d1.level >= 0 else d2.level, "id":d1.smmo_id})
            da[0][3].append({"name":m.name, "stats": d2.level - d1.level if d2.level - d1.level >= 0 else d2.level, "id":d1.smmo_id})
 
        if all(len(x)==0 for x in da):
            return await ctx.followup.send(content="No data found.")
    
        for i in range(len(da)):
            for j in range(len(da[i])):
                da[i][j] = sorted(da[i][j], key=lambda item: item["stats"],reverse=True)  

        advlb_view = AdvleaderboardView()
        advlb_view.data = da
        advlb_view.end_data = int(e_date.replace(tzinfo=timezone.utc,hour=12,minute=0,second=0,microsecond=0).timestamp())
        advlb_view.start_data = int(s_date.replace(tzinfo=timezone.utc,hour=12,minute=0,second=0,microsecond=0).timestamp())
        await advlb_view.send(ctx)
    
    @subcommand("guild")
    @slash_command(description="Show guild contribution")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.statistics("/guild contribution")
    @command_utils.took_too_long()
    async def contribution(self,ctx:ApplicationContext):
        modal = ContributionModal(title="Insert your APIKey")
        await ctx.send_modal(modal)
        await modal.wait()
        user = await SMMOApi.get_me(modal.api_key)
        if user is None:
            return await helpers.send(ctx,"API Key not valid.")
        data = [[],[],[],[],[]]
        for member in await SMMOApi.get_guild_members(user.guild["id"]):
            contr = await SMMOApi.get_guild_member_contribution(user.guild["id"], member.user_id, modal.api_key)
            if contr is None:
                continue
            data[0].append({"name":member.name,"id":member.user_id,"stats":contr.power_points_deposited})
            data[1].append({"name":member.name,"id":member.user_id,"stats":contr.gold_deposited})
            data[2].append({"name":member.name,"id":member.user_id,"stats":(contr.pve_exp + contr.pvp_exp)})
            data[3].append({"name":member.name,"id":member.user_id,"stats":contr.tax_contribution["guild_bank"]})
            data[4].append({"name":member.name,"id":member.user_id,"stats":contr.tax_contribution["sanctuary"]})
        data = [sorted(x, key=lambda item: -item["stats"]) for x in data]
        contribution_view = ContributionView()
        contribution_view.data = data
        return await contribution_view.send(ctx)

    @subcommand("guild")
    @slash_command(description="Show current setted requirements")
    @guild_only()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/guild requirements")
    @command_utils.took_too_long()
    async def requirements(self, ctx: ApplicationContext):
        req = await Database.select_requirements(ctx.user_guild_id)
        if req is None:
            return await helpers.send(ctx,content="There are no requirements set.")
        msg: str = f"**Gains you need to meet every {f"*{req.days}* days" if req.days != 1 else "day"}**:\n"
        if req.levels != 0:
            msg += f"*Levels*: {req.levels}\n"
        if req.npc != 0:
            msg += f"*NPC Kill*: {req.npc}\n"
        if req.pvp != 0:
            msg += f"*User Kill*: {req.pvp}\n"
        if req.steps != 0:
            msg += f"*Steps*: {req.steps}"
        await helpers.send(ctx,content=msg)

def setup(client:Bot):
    client.add_cog(Guild(client))
    client.add_cog(GuildTask(client))
    