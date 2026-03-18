from discord import ApplicationContext, slash_command, Bot, guild_only, option, TextChannel, Forbidden, User, Member
from discord.ext import tasks, commands
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.api.model import PlayerInfo
from bot.database import Database
from bot.database.model import EventTeam,UserStat
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.modules.event._tasks import EventTasks

from bot.discord_cmd.modules.event._leaderboard_view import EvtLeaderboardView
from bot.discord_cmd.modules.event._event_global_list_view import EventListView
from bot.discord_cmd.modules.event._preview_registration_view import PreviewRegistrationView
from bot.discord_cmd.modules.event._registration_dialog import RegistrationModal
from bot.discord_cmd.modules.event._history_view import HistoryView
from bot.discord_cmd.modules.event._participants_view import ParticipantsView 

from datetime import time, datetime, timezone
from random import shuffle
from collections import Counter, defaultdict

# bot do random team anyway then can be customized

# Event setup has a parameter where you can select "guild member only" to accept only guildie to the event (automatic with the gxp)
# so multi guilds events can be done

# edit event need to upload the edit in the message


# Auto choose the last event, and show others event list in stats
class Events(commands.Cog):
    def __init__(self, client:Bot) -> None:
        self.client = client
    # @subcommand("admin event")
    # @slash_command(description="Create custom Teams for the event")
    # @discord.guild_only()
    # @command_utils.auto_defer()
    # @permissions.require_admin_or_staff()
    # @permissions.require_linked_server()
    # @permissions.took_too_long()
    # async def create_teams(self, ctx: ApplicationContext, event_id:int=None):
    #     evt = await Database.select_all_guild_events(await Database.select_server(ctx.guild_id))
    #     if len(evt) == 0:
    #         return await ctx.followup.send(content="No event found for this guild")
    #     elif len(evt) == 1:
    #         event_id = evt[0].id
    #     elif len(evt) != 1 and event_id is None:
    #         return await ctx.followup.send(content=f"More event found.\nInsert the event_id of the event you want to see.\nEvents you are in: `{"`  `".join(v.id for v in evt)}`")
    #     elif  event_id not in set(v.id for v in evt):
    #         return await ctx.followup.send(content="Event id not found")
        
    #     ## HOW TF I SHOULD DO IT T-T

    @subcommand("event")
    @slash_command(description="Show the list of global events",name="list")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event list")
    @command_utils.took_too_long()
    async def join_event(self, ctx: ApplicationContext):
        is_empty,events = helpers.gen_is_empty(await Database.select_all_global_events(datetime.now().timestamp()))
        if is_empty:
            emb = helpers.Embed(title="There are no Global Event Available Now",
            description="Create yours with '/admin event setup'")
            return await ctx.followup.send(embed=emb)
        view = EventListView()
        view.events = tuple(events)
        view.ts = datetime.now().timestamp()
        await view.send(ctx)


    @subcommand("event")
    @slash_command(description="Show event info")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event info")
    @command_utils.took_too_long()
    async def info(self, ctx: ApplicationContext, event_id:int=None):
        bot_user = await Database.select_user_discord(ctx.user.id)
        is_empty,user_events = helpers.gen_is_empty(await Database.select_event_user_partecipants(bot_user.smmo_id))
        if is_empty:
            return await helpers.send(ctx,content="You aren't in an event")
        elif event_id is None:
            event_id = next(user_events).event_id
        else:
            found = False
            for evt in user_events:
                if evt.event_id == event_id:
                    found = True
                    break
            if not found:
                return await helpers.send(ctx,content="You aren't in that event")
        evt = await Database.select_event(event_id) 
        if evt is None:
            return await helpers.send(ctx,content="Event not found")
        users = await Database.select_counter_event_user_partecipants(evt.id)

        emb = helpers.Embed(title=evt.name, description=evt.description, 
                                image=evt.image,
                                thumbnail=evt.thumbnail,
                                color=0x11ac4d)
        emb.add_field(name="Event Info",
                    value=f"**Starting date**: <t:{int(evt.start_time)}>\n"
                            f"**Ending date**: <t:{int(evt.end_time)}>\n"
                            f"**Event Formula**: `{evt.event_type.upper()}`\n"
                            f"**Participants**: {"Guild Members only" if evt.guildies_only else "Open to all"}\n"
                            f"**Teams size**: {evt.team_size}\n"
                            f"**Event ID**: `{evt.id}`",
                            inline=False
                    )
        emb.add_field(name="",value=f"Registered users: {users:,}",inline=False)
        await helpers.send(ctx,embed=emb)

    @subcommand("event")
    @slash_command(description="Show event participants")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event participants")
    @command_utils.took_too_long()
    async def participants(self, ctx: ApplicationContext, event_id:int=None):
        bot_user = await Database.select_user_discord(ctx.user.id)

        is_empty,user_events = helpers.gen_is_empty(await Database.select_event_user_partecipants(bot_user.smmo_id))
        if is_empty:
            return await helpers.send(ctx,content="You aren't in an event")
        elif event_id is None:
            event_id = next(user_events).event_id
        else:
            found = False
            for evt in user_events:
                if evt.event_id == event_id:
                    found = True
                    break
            if not found:
                return await helpers.send(ctx,content="You aren't in that event")
        evt = await Database.select_event(event_id) 

        event_participants = await Database.select_event_partecipants(evt.id)
        grouped = defaultdict(list)
        c = 0
        for member in event_participants:
            c+=1
            grouped[member.team].append(member)
        view = ParticipantsView()
        view.np = c
        view.evt = evt
        view.team_size = evt.team_size
        view.event_participants = [(members[0].team, members) for members in grouped.values()]
        await view.send(ctx)
            

    @subcommand("event")
    @slash_command(description="Show your event history")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event history")
    @command_utils.took_too_long()
    async def history(self, ctx: ApplicationContext):
        bot_user = await Database.select_user_discord(ctx.user.id)
        user_events = await Database.select_event_user_partecipants(bot_user.smmo_id)
        event_list = []
        for ue in user_events:
            event_list.append(await Database.select_event(ue.event_id))
        if len(event_list) == 0:
            return helpers.send(ctx,content="No events")
        evt = HistoryView()
        evt.event_list = sorted(event_list, key=lambda item: item.end_time,reverse=True)
        evt.last_update = int(datetime.now().timestamp())
        await evt.send(ctx)

    @subcommand("admin event")
    #@slash_command(description="Set up and event in this server", guild_ids=[1175190899182030888,1319980713541505044])
    @slash_command(description="Set up a custom event in the current channel")
    @guild_only()
    @option(name="custom_image", description="Specifies the link of an image/gif to be embedded within the text")
    @permissions.require_admin_or_staff()
    @permissions.require_linked_account()
    @command_utils.statistics("/event setup")
    @command_utils.took_too_long()
    async def setup(self,ctx:ApplicationContext,teams_size:int=1,custom_image:str=None,custom_thumbnail:str=None):
        try:
            ch = await self.client.fetch_channel(ctx.channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Exception:
            return await ctx.followup.send(content="Bot doesn't have the perms to see/write the channel.")
        player = await SMMOApi.get_player_info(ctx.discord_user.smmo_id)
        modal = RegistrationModal(title="Event Setup")
        modal.player = player
        modal.custom_image = custom_image
        modal.custom_thumbnail = custom_thumbnail
        modal.team_size = teams_size
        modal.author_id = ctx.author.id
        await ctx.send_modal(modal)
        
    @subcommand("admin event")
    @slash_command(description="Setup the leaderboard")
    @guild_only()
    @permissions.require_admin_or_staff()
    @command_utils.auto_defer()
    @command_utils.statistics("/admin event setup_lb")
    @command_utils.took_too_long()
    async def setup_lb(self, ctx: ApplicationContext, event_id:int, channel:TextChannel = None):
        if channel is None:
            channel = ctx.channel
        event = await Database.select_event(event_id)
        if event is None:
            return helpers.send(ctx,content="Event ID not found")
        if event.event_type == "None":
            return helpers.send(ctx,content="Event Type is None")
        try:
            ch = await self.client.fetch_channel(channel.id)
            message = await ch.send(content="The Event leaderboar will be shown in this message.")
        except Forbidden:
            return await helpers.send(ctx,content="Bot doesn't have the perms to see/write the channel.")

        if not await Database.insert_event_lb(ch.id,message.id,event_id):
            if not await Database.update_event_lb(ch.id,event_id,message.id):
                await message.delete()
                return await helpers.send(ctx,content="Error on setting up the event leaderboard.")
        await helpers.send(ctx,content=f"Leaderboard for event `{event_id}` has been set up.")
        #setup leaderboard show the same choosable list from events to set up leaderboard

    @subcommand("admin event")
    @slash_command(description="Remove the leaderboard")
    @guild_only()
    @permissions.require_linked_account()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer()
    @command_utils.statistics("/event remove_lb")
    @command_utils.took_too_long()
    async def remove_lb(self, ctx: ApplicationContext, event_id:int, channel:TextChannel = None):
        if channel is None:
            channel = ctx.channel
        await Database.delete_event_lb(channel.id,event_id)
        await ctx.followup.send(content=f"Leaderboard for event `{event_id}` has been removed.")

    @subcommand("admin event")
    @slash_command(description="Add participant to the event, the user need to be")
    @guild_only()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.statistics("/event add_participant")
    @command_utils.took_too_long()
    async def add_participant(self,ctx:ApplicationContext,event_id:int,user:User=None):
        user_discord = await Database.select_user_discord(user.id)
        if user_discord is None:
            return await helpers.send(ctx,content=f"User not linked with the bot")
        evt = await Database.select_event(event_id)
        server = await Database.select_server(ctx.guild_id)
        if evt is None or not (evt.guildies_only and evt.guild_id==server):
            return await helpers.send(ctx,content=f"Not allowed to add participant in this event")
        user_game = await SMMOApi.get_player_info(user_discord.smmo_id)
        await Database.insert_event_partecipant(user_discord.smmo_id,user_game.name,user_discord.discord_id,evt.id,"")
        await helpers.send(ctx,content=f"Player added to event")


    @subcommand("event")
    @slash_command(description="Show the leaderboard")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event lb")
    @command_utils.took_too_long()
    async def lb(self, ctx: ApplicationContext, event_id:int = None):
        g_user = await Database.select_user_discord(ctx.user.id)
        is_empty,user_events = helpers.gen_is_empty(await Database.select_event_user_partecipants(g_user.smmo_id))

        if is_empty:
            return await helpers.send(ctx,content="No Event Found")
        elif event_id is None:
            event_id = next(user_events).event_id
        else:
            found = False
            for evt in user_events:
                if evt.event_id == event_id:
                    found = True
                    break
            if not found:
                return await helpers.send(ctx,content="You aren't in that event")
        evt = await Database.select_event(event_id) 
        if evt is None:
            return await helpers.send(ctx,content="Event not found")
        if evt.event_type == "None":
            return await helpers.send(ctx,content="Event Type is None, No leaderboard for that type of event")

        event_partecipants = await Database.select_event_partecipants(event_id)

        event_teams:dict = dict()
        current_date = helpers.get_current_date_game()
        if evt.guildies_only:
            guild_member = tuple(await SMMOApi.get_guild_members(evt.guild_id))
        author_team = ""
        for partecipant in event_partecipants:
            if partecipant.smmo_id == g_user.smmo_id:
                author_team = str(partecipant.team)
            user_stats = await Database.select_user_stat(partecipant.smmo_id,evt.start_year,evt.start_month,evt.start_day)
            if user_stats is None:
                continue
            start_day_stats = await Database.select_user_stat(partecipant.smmo_id,current_date.year,current_date.month,current_date.day)
            if start_day_stats is None:
                continue
            if evt.guildies_only:
                current_stats = next((x for x in guild_member if x.user_id == partecipant.smmo_id), None)
            else:
                current_stats = await SMMOApi.get_player_info(partecipant.smmo_id)

            if current_stats is None:
                continue
            
            if partecipant.team == "":
                partecipant.team = "No Team"
            if partecipant.team not in event_teams:
                event_teams[partecipant.team] = []

            curr_stats = helpers.evaluate_formula(evt.event_type,
                                                 current_stats.steps-user_stats.steps,
                                                 current_stats.npc_kills-user_stats.npc_kills,
                                                 current_stats.user_kills-user_stats.user_kills)
            today_stats = helpers.evaluate_formula(evt.event_type,
                                                  start_day_stats.steps-user_stats.steps,
                                                  start_day_stats.npc_kills-user_stats.npc_kills,
                                                  start_day_stats.user_kills-user_stats.user_kills)
            
            if not helpers.is_number(curr_stats) or not helpers.is_number(today_stats):
                return await ctx.followup.send(content="Error, try again later, or ask Algol")

            event_teams[partecipant.team].append({"player":partecipant,"stats": curr_stats, "gains": curr_stats-today_stats, "name":current_stats.name})

        if len(event_teams) == 0:
            return await ctx.followup.send(content="No stats found, has the event started? right?")

        evt_view = EvtLeaderboardView()
        evt_view.event = evt
        evt_view.author_team = author_team
        evt_view.last_update = int(datetime.now().timestamp())
        # evt.event_teams = {k[0]:sum(y["stats"] for y in k[1]) for k in sorted(event_teams.items(), key=lambda item: sum(x["stats"] for x in item[1]), reverse=True)}
        evt_view.event_teams = [(k,sum(y["stats"] for y in event_teams[k]), [x["player"] for x in event_teams[k]]) for k in sorted(event_teams, key=lambda item: sum(x["stats"] for x in event_teams[item]), reverse=True)]
        await evt_view.send(ctx)
    
    # @subcommand("smmo event")
    # @slash_command(description="Register to an event", guild_ids=[1175190899182030888,1319980713541505044])
    # @command_utils.auto_defer()
    # async def partecipate(self, ctx: ApplicationContext, smmo_id:int = None):
    #     if smmo_id is None:
    #         p = await Database.get_user(ctx.user.id)
    #         if p.smmo_id is not None:
    #             smmo_id = p.smmo_id
    #         else:
    #             await ctx.followup.send(content="Your account is not linked, link using `/smmo user link SMMO_ID` or add the smmo_id to the command parameter")
    #             return
        
    #     # do a view with a choosable option witch show what events are on/ will be on
    
    @subcommand("event")
    @slash_command(description="Show your team's stats")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event stats")
    @command_utils.took_too_long()
    async def stats(self, ctx: ApplicationContext, user:Member=None, smmo_id:int = None, event_id:int=None):
        if user is not None:
            u_id = user.id
        else:
            u_id = ctx.user.id
        bot_user = await Database.select_user_discord(u_id)
        if bot_user is None:
            return await ctx.followup.send("User not linked.")
        smmo_id = bot_user.smmo_id if smmo_id is None else smmo_id

        is_empty,user_events = helpers.gen_is_empty(await Database.select_event_user_partecipants(bot_user.smmo_id))
        if is_empty:
            return await helpers.send(ctx,content="No Event Found")
        elif event_id is None:
            user_evt = next(user_events)
            event_id = user_evt.event_id
        else:
            found = False
            for evt in user_events:
                if evt.event_id == event_id:
                    user_evt = evt
                    found = True
                    break
            if not found:
                return await helpers.send(ctx,content="You aren't in that event")
        evt = await Database.select_event(event_id) 
        if evt is None:
            return await ctx.followup.send(content="Event not found")

        starting_stats = await Database.select_user_stat(smmo_id,evt.start_year,evt.start_month,evt.start_day)
        
        current_stats = await SMMOApi.get_player_info(smmo_id)
        team = await Database.select_event_team(user_evt.team, evt.guild_id) 
        team = team if team else []
        team = [x for x in team if team.smmo_id != bot_user.smmo_id]
        team_stats_current = [await SMMOApi.get_player_info(x.smmo_id) for x in team]
        team_stats_starting = [await Database.select_user_stat(x.smmo_id,evt.start_year,evt.start_month,evt.start_day) for x in team]

        current_day = helpers.get_current_date_game()
        ending_time = current_day.timestamp()
        ended = False
        if datetime(evt.end_year,evt.end_month,evt.end_day,12,tzinfo=timezone.utc) < current_day:
            current_temp = await Database.select_user_stat(smmo_id,evt.end_year,evt.end_month,evt.end_day)
            current_stats.steps = current_temp.steps
            current_stats.npc_kills = current_temp.npc_kills
            current_stats.user_kills = current_temp.user_kills
            ending_time = datetime(evt.end_year,evt.end_month,evt.end_day,12,tzinfo=timezone.utc).timestamp()
            for teammate in team_stats_current:
                current_team_temp = await Database.select_user_stat(teammate.smmo_id,evt.end_year,evt.end_month,evt.end_day)
                teammate.steps = current_team_temp.steps
                teammate.npc_kills = current_team_temp.npc_kills
                teammate.user_kills = current_team_temp.user_kills
            ended = True
        started = True
        if datetime(evt.start_year,evt.start_month,evt.start_day,12,tzinfo=timezone.utc) > current_day:
            started = False
        if starting_stats is None:
            score = 0
            team_score = 0
        else:
            score = helpers.evaluate_formula(evt.event_type,
                                                        current_stats.steps-starting_stats.steps,
                                                        current_stats.npc_kills-starting_stats.npc_kills,
                                                        current_stats.user_kills-starting_stats.user_kills
                                                        )
            team_score = sum(helpers.evaluate_formula(evt.event_type,
                                                        x.steps-y.steps,
                                                        x.npc_kills-y.npc_kills,
                                                        x.user_kills-y.user_kills
                                                        ) for x in team_stats_current for y in team_stats_starting if x.smmo_id == y.smmo_id)
        emb = helpers.Embed(title=f"[{current_stats.name}]'s stats from {evt.name}",
                                  description=f"**Timeframe**: {f"<t:{int(datetime(evt.start_year,evt.start_month,evt.start_day,12,tzinfo=timezone.utc).timestamp())}> - <t:{int(ending_time)}>" if started else "Not Started"}\n"
                                              f"**Last updated**: <t:{int(datetime.now().timestamp())}:R>\n"
                                              f"**Team**: '{user_evt.team if user_evt.team != "" else "No Team... Yet."}'",
                                  url=f"https://simple-mmo.com/user/view/{current_stats.id}",
                                  thumbnail=f"https://simple-mmo.com{current_stats.avatar}")
        emb.add_field(name="Your Score",
                      value=f"{score:,} ({(score/max(team_score+score,1))*100:.2f}%)",
                      inline=True
                      )
        emb.add_field(name="Team Score",
                      value=f"{team_score:,}",
                      inline=True
                      )
        
        emb.add_field(name="Total Score",
                      value=f"{score+team_score:,}",
                      inline=True
                      )
        emb.add_field(name="",value=f"Formula used in this event: `{evt.event_type.upper()}`",inline=False)

        if event_id is None:
            emb.add_field(name="Other Events You are in:",value="\n".join(f"[{x.id}] - {x.name}" for x,_ in zip(user_events,range(5))),inline=False)

        if ended:
            emb.set_footer(text="*Event Ended*")
        return await ctx.followup.send(embed=emb)

    
    
    # @tasks.loop(time=time(hour=12))
    # async def create_new_daily_leaderboard(self):
    #     data = await Database.select_all_event_lb()
    #     event = await Database.select_all_events(int(datetime.now().timestamp()))
    #     dat = []
    #     for e,d in zip(event,data):
    #         if e.id == d.event_id:
    #             if e.start_data <= datetime.now().timestamp() and e.end_data > datetime.now().timestamp():
    #                 dat.append(d)
    #     for d in data:
    #         try:
    #             channel = await self.client.fetch_channel(d.channel_id)
    #         except discord.errors.NotFound:
    #             continue
    #         except discord.errors.Forbidden:
    #             continue


        # partecipants = await Database.select_event_team(data.event_id,data.guild_id)
        # msg: str = ""
        # emb = command_utils.Embed(title=f"{event.name}", description=f"Updated: <t:{int(datetime.now().timestamp())}:R>")
        # values = set(map(lambda x:x.team, partecipants))
        # ppppp = [[y for y in partecipants if y.team==x] for x in values]
        # guild_membets = await SMMOApi.get_guild_members(event.guild_id)
        # var = []
        # for pp in ppppp:
        #     var.append([])
        #     for p in pp:
        #         try:
        #             if not any(x.user_id == p.smmo_id for x in guild_membets):
        #                 continue
        #             player = await SMMOApi.get_player_info(p.smmo_id)
        #             stats = await Database.get_event_stats(smmo_id=p.smmo_id,event_id=data.event_id,time=Database.get_current_day_start())
        #             stats2 = await Database.get_event_stats(smmo_id=p.smmo_id,event_id=data.event_id,time=Database.get_current_day_start(1))
        #             stats3 = await Database.get_event_stats(smmo_id=p.smmo_id,event_id=data.event_id,time=event.start_data)
        #             var[-1].append({"name":player.name,"id":player.id, "team": p.team})
        #             yest = 0
        #             if event.event_type == "GXP":
        #                 contr = await SMMOApi.get_guild_member_contribution(3075, p.smmo_id)
        #                 var[-1][-1]["stat"] = contr.pve_exp + (player.steps * 3) + contr.pvp_exp - stats3[0].stats
        #                 yest = contr.pve_exp + (player.steps * 3) + contr.pvp_exp
        #             elif event.event_type == "NPC":
        #                 var[-1][-1]["stat"] = player.npc_kills - stats3[0].stats
        #                 yest = player.npc_kills
        #             elif event.event_type == "PVP":
        #                 var[-1][-1]["stat"] = player.user_kills - stats3[0].stats
        #                 yest = player.user_kills
        #             elif event.event_type == "Steps":
        #                 var[-1][-1]["stat"] = player.steps - stats3[0].stats
        #                 yest = player.steps
        #             elif event.event_type == "Levels":
        #                 var[-1][-1]["stat"] = player.level - stats3[0].stats
        #                 yest = player.level
        #             if len(stats2) != 0:
        #                 var[-1][-1]["ys"] = yest - stats[0].stats
        #         except Exception as e:
        #             print(f"Error on update stats event {p}\n{e}")

        # var = [sorted(v, key=lambda item: -item["stat"]) for v in var]
        # var = sorted(var, key=lambda item: -sum([v["stat"] for v in item]))

        # for i,v in enumerate(var):
        #     for k in v:
        #         msg = f"{msg}[{k["name"]}](https://simple-mmo.com/user/view/{k["id"]}): {format(k["stat"],",d")} {f"(+{format(k["ys"],",d")})\n" if "ys" in k else "\n"}"
    
        #     emb.add_field(name=f"#{i+1} Team {v[0]["team"]} - {format(sum([k["stat"] for k in v]),",d")}",
        #                 value=msg,
        #                 inline=False)
        #     msg = ""
        
        # emb.set_footer(text="Update every hour")

        # return emb
    
    # @tasks.loop(time=time(hour=12))
    # async def update_event_stats(self):
    #     print("TASK STARTED-ues")
    #     events = await Database.get_all_events()
    #     for e in events:
    #         if e.start_data >= datetime.now().timestamp() or e.end_data <= datetime.now().timestamp():
    #             continue
    #         partecipants = await Database.get_all_event_teams(e.id)
    #         for p in partecipants:
    #             try:
    #                 player = await SMMOApi.get_player_info(p.smmo_id)
    #                 if player is None:
    #                     continue
    #                 stats: int = 0
    #                 if e.event_type == "GXP":
    #                     data = await SMMOApi.get_guild_member_contribution(3075, p.smmo_id)
    #                     stats = data.pve_exp + (player.steps * 3) + data.pvp_exp
    #                 elif e.event_type == "NPC":
    #                     stats = player.npc_kills
    #                 elif e.event_type == "PVP":
    #                     stats = player.user_kills
    #                 elif e.event_type == "Steps":
    #                     stats = player.steps
    #                 elif e.event_type == "Levels":
    #                     stats = player.level
    #                 elif e.event_type == "Quests":
    #                     stats = player.quests_performed
    #                 await Database.set_event_stats(e.id, p.smmo_id, stats=stats, start_date=Database.get_current_day_start(), end_date=Database.get_current_day_start()+86400)
    #             except Exception as e:
    #                 print(f"Error on saving event stats {p}\n{e}")
    #                 continue
    #     print("TASK ENDED-ues")

def setup(client:Bot):
    client.add_cog(Events(client))
    client.add_cog(EventTasks(client))
    
