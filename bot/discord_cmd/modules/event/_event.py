from discord import ApplicationContext, slash_command, Bot, guild_only, option, TextChannel, Forbidden, User, Member
from discord.ext import tasks, commands
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.api.model import PlayerInfo
from bot.database import Database
from bot.database.model import EventTeam,UserStat
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.modules.event._tasks import EventTasks
from bot.core._event import EventManager

from bot.discord_cmd.modules.event._leaderboard_view import EvtLeaderboardView
from bot.discord_cmd.modules.event._event_global_list_view import EventListView
from bot.discord_cmd.modules.event._preview_registration_view import PreviewRegistrationView
from bot.discord_cmd.modules.event._registration_dialog import RegistrationModal
from bot.discord_cmd.modules.event._history_view import HistoryView
from bot.discord_cmd.modules.event._participants_view import ParticipantsView 
from bot.discord_cmd.modules.event._create_teams_view import CreateTeamsView

from datetime import time, datetime, timezone, timedelta
from random import shuffle

# bot do random team anyway then can be customized

# Event setup has a parameter where you can select "guild member only" to accept only guildie to the event (automatic with the gxp)
# so multi guilds events can be done

# edit event need to upload the edit in the message


# Auto choose the last event, and show others event list in stats
class Events(commands.Cog):
    def __init__(self, client:Bot) -> None:
        self.client = client


    @subcommand("admin event")
    @slash_command(description="Remove a user from a team")
    @guild_only()
    @command_utils.auto_defer()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.statistics("/event remove_user_from_team")
    @command_utils.took_too_long()
    async def remove_user_from_team(self, ctx: ApplicationContext, event_id:int, user:Member):
        discord_user = await Database.select_user_discord(user.id)
        if discord_user is None:
            return await ctx.followup.send("User not found")
        partecipant = await Database.select_event_partecipant(event_id,discord_user.smmo_id)
        if partecipant is None:
            return await ctx.followup.send("User not found in the event")
        if not await Database.update_event_partecipant(discord_user.smmo_id,event_id,""):
            return await ctx.followup.send("Error during update")
        await ctx.followup.send("User remove from the team changed.")


    @subcommand("admin event")
    @slash_command(description="Change the amount of bonus point of a user")
    @guild_only()
    @command_utils.auto_defer()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.statistics("/event set_points")
    @command_utils.took_too_long()
    async def set_points(self, ctx: ApplicationContext, event_id:int, user:Member, points:int):
        discord_user = await Database.select_user_discord(user.id)
        if discord_user is None:
            return await ctx.followup.send("User not found")
        partecipant = await Database.select_event_partecipant(event_id,discord_user.smmo_id)
        if partecipant is None:
            return await ctx.followup.send("User not found in the event")

        if not await Database.update_event_partecipant_points(discord_user.smmo_id,event_id,points):
            return await ctx.followup.send("Error during update")
        await ctx.followup.send("Points changed.")

    @subcommand("admin event")
    @slash_command(description="Create custom Teams for the event")
    @guild_only()
    @command_utils.auto_defer()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.statistics("/event create_teams")
    @command_utils.took_too_long()
    async def create_teams(self, ctx: ApplicationContext, event_id:int=None):
        evt = tuple(await Database.select_all_guild_events(await Database.select_server(ctx.guild_id)))
        if len(evt) == 0:
            return await ctx.followup.send(content="No event found for this guild")
        elif len(evt) == 1:
            event_id = evt[0].id
            evt = evt[0]
        elif len(evt) != 1 and event_id is None:
            return await ctx.followup.send(content=f"More than one event found.\nInsert the event_id of the event you want to see.\nEvents you are in: `{"`  `".join(str(v.id) for v in evt)}`")
        elif event_id is not None and event_id not in set(v.id for v in evt):
            return await ctx.followup.send(content="Event id not found")
        else:
            for v in evt:
                if v.id == event_id:
                    evt = v
                    break
        
        view = CreateTeamsView()
        view.evt = evt
        await view.send(ctx)
     

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
        if is_empty and event_id is None:
            return await helpers.send(ctx,content="You aren't in an event")
        elif event_id is None:
            event_id = next(user_events).event_id
        else:
            found = False
            for evt in user_events:
                if evt.event_id == event_id:
                    found = True
                    break
            #if not found:
            #    return await helpers.send(ctx,content="You aren't in that event")
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
    
        view = ParticipantsView()
        view.evt = evt
        view.team_size = evt.team_size
        view.event_participants = sorted(event_participants,key=lambda member: member.team)
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
    @slash_command(description="Set up a custom event in the current channel")
    @guild_only()
    @option(name="custom_image", description="Specifies the link of an image/gif to be embedded within the text")
    @permissions.require_admin_or_staff()
    @permissions.require_linked_account()
    @permissions.require_linked_server()
    @command_utils.statistics("/event setup")
    @command_utils.took_too_long()
    async def setup(self,ctx:ApplicationContext,teams_size:int=1,custom_image:str=None,custom_thumbnail:str=None):
        try:
            ch = await self.client.fetch_channel(ctx.channel.id)
            await ch.send(content="test message.", delete_after=1)
        except Exception:
            return await ctx.followup.send(content="Bot doesn't have the perms to see/write the channel.")
        player = ctx.user_game_profile if ctx.user_game_profile else await SMMOApi.get_player_info(ctx.discord_user.smmo_id) 
        modal = RegistrationModal(title="Event Setup")
        modal.player = player
        modal.custom_image = custom_image
        modal.custom_thumbnail = custom_thumbnail
        modal.team_size = teams_size
        modal.author_id = ctx.author.id
        modal.igguild_id = player.guild.id
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
    async def add_participant(self,ctx:ApplicationContext,event_id:int,user:User):
        user_discord = await Database.select_user_discord(user.id)
        if user_discord is None:
            return await helpers.send(ctx,content=f"User not linked with the bot")
        evt = await Database.select_event(event_id)
        server = await Database.select_server(ctx.guild_id)
        if evt is None or not (evt.guildies_only and evt.guild_id==server):
            pass
            #return await helpers.send(ctx,content=f"Not allowed to add participant in this event")
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

        event_teams = {}
        current_date = helpers.get_current_date_game()
        if evt.guildies_only:
            guild_member = tuple(await SMMOApi.get_guild_members(evt.igguild_id))
        author_team = ""
        
        bulk_stats1 = await Database.select_user_stat_bulk([p.smmo_id for p in event_partecipants],evt.start_year,evt.start_month,evt.start_day)
        bulk_stats2 = await Database.select_user_stat_bulk([p.smmo_id for p in event_partecipants],current_date.year,current_date.month,current_date.day)
        for partecipant in event_partecipants:
            if partecipant.smmo_id == g_user.smmo_id:
                author_team = str(partecipant.team)
                
            user_stats = bulk_stats1[partecipant.smmo_id]

            if user_stats is None:
                continue
            start_day_stats = bulk_stats2[partecipant.smmo_id]
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
        
        start_datetime = datetime(evt.start_year,evt.start_month,evt.start_day,hour=12,tzinfo=timezone.utc)
        ending_datetime = datetime(evt.end_year,evt.end_month,evt.end_day,hour=12,tzinfo=timezone.utc)

        evt_mng = EventManager(evt)
        event_teams = await evt_mng.get_partecipants_points(user_evt.team)

        score = event_teams[user_evt.smmo_id]["stats"]+event_teams[user_evt.smmo_id]["extra"]
        total_team_score = sum(x["stats"]+x["extra"] for x in event_teams.values() if x["player"].smmo_id != user_evt.smmo_id)
        full_team_score = total_team_score+score

        emb = helpers.Embed(
            title=f"[{user_evt.name}]'s stats from {evt.name}",
            description=f"**Timeframe**: <t:{int(start_datetime.timestamp())}> - <t:{int(ending_datetime.timestamp())}>\n"
                        f"**Last updated**: <t:{int(datetime.now().timestamp())}:R>\n"
                        f"**Team**: {user_evt.team or "No Team... Yet."}",
            url=f"https://simple-mmo.com/user/view/{user_evt.smmo_id}",
            #thumbnail=f"https://simple-mmo.com{current_stats.avatar}"
        )
        emb.add_field(name="Your Score",
                        value=f"{score:,} ({(score/max(full_team_score,1))*100:.2f}%)",
                        inline=True
                        )
        emb.add_field(name="Team Score",
                        value=f"{total_team_score:,}",
                        inline=True
                        )
        
        emb.add_field(name="Total Score",
                        value=f"{full_team_score:,}",
                        inline=True
                        )
                        
        emb.add_field(name="",value=f"Formula used in this event: `{evt.event_type.upper()}`",inline=False)

        if event_id is None:
            emb.add_field(name="Other Events You are in:",value="\n".join(f"[{x.id}] - {x.name}" for x,_ in zip(user_events,range(5))),inline=False)

        now = datetime.now(tz=timezone.utc)
        if now > ending_datetime:
            emb.set_footer(text="*Event Ended*")
        if start_datetime > now:
            emb.set_footer(text="*Event Has To Start*")

        return await helpers.send(ctx,embed=emb)


    @subcommand("event")
    @slash_command(description="Show your team's stats")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event stats_team")
    @command_utils.took_too_long()
    async def stats_team(self, ctx: ApplicationContext, event_id:int=None):
        smmo_id = ctx.discord_user.smmo_id

        user_events = tuple(await Database.select_event_user_partecipants(smmo_id))
        if len(user_events)==0:
            return await helpers.send(ctx,content="No Event Found")
        elif event_id is None:
            user_evt = user_events[0]
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
        start_datetime = datetime(evt.start_year,evt.start_month,evt.start_day,hour=12,tzinfo=timezone.utc)
        ending_datetime = datetime(evt.end_year,evt.end_month,evt.end_day,hour=12,tzinfo=timezone.utc)

        evt_mng = EventManager(evt)
        event_teams = await evt_mng.get_partecipants_points(user_evt.team)

        score = event_teams[user_evt.smmo_id]["stats"]+event_teams[user_evt.smmo_id]["extra"]
        total_team_score = sum(x["stats"]+x["extra"] for x in event_teams.values() if x["player"].smmo_id != user_evt.smmo_id)
        full_team_score = total_team_score+score

        emb = helpers.Embed(
            title=f"[{user_evt.name}]'s stats from {evt.name}",
            description=f"**Timeframe**: <t:{int(start_datetime.timestamp())}> - <t:{int(ending_datetime.timestamp())}>\n"
                        f"**Last updated**: <t:{int(datetime.now().timestamp())}:R>\n"
                        f"**Team**: {user_evt.team or "No Team... Yet."}",
            url=f"https://simple-mmo.com/user/view/{user_evt.smmo_id}",
            #thumbnail=f"https://simple-mmo.com{current_stats.avatar}"
        )
        emb.add_field(name="Your Score",
                        value=f"{score:,} ({(score/max(full_team_score,1))*100:.2f}%)",
                        inline=True
                        )
        emb.add_field(name="Team Score",
                        value=f"{total_team_score:,}",
                        inline=True
                        )
        
        emb.add_field(name="Total Score",
                        value=f"{full_team_score:,}",
                        inline=True
                        )
                        
        msg = ""
        title = True
        for x in sorted(event_teams.values(), key=lambda mbr: mbr["stats"]+mbr["extra"],reverse=True):
            temp = f"{x["player"].name}: {x["stats"]+x["extra"]:,}{f" [{x["extra"]}]" if x["extra"]!=0 else ""} ({(x["stats"]/max(full_team_score,1))*100:.2f}%)\n"
            if len(msg)+len(temp)<1024:
                msg += temp
            else:
                emb.add_field(
                    name="Team Info" if title else "",
                    value=msg,
                    inline=False
                )
                title = False
                msg = ""
        if msg != "":
            emb.add_field(
                    name="Team Info" if title else "",
                    value=msg,
                    inline=False
            )
        emb.add_field(name="",value=f"Formula used in this event: `{evt.event_type.upper()}`",inline=False)

        if event_id is None:
            emb.add_field(name="Other Events You are in:",value="\n".join(f"[{x.id}] - {x.name}" for x,_ in zip(user_events,range(5))),inline=False)

        now = datetime.now(tz=timezone.utc)
        if now > ending_datetime:
            emb.set_footer(text="*Event Ended*")
        if start_datetime > now:
            emb.set_footer(text="*Event Has To Start*")

        return await helpers.send(ctx,embed=emb)
    
    @subcommand("event")
    @slash_command(description="Show your event overall")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/event overall")
    @command_utils.took_too_long()
    async def overall(self, ctx: ApplicationContext, user:Member=None, smmo_id:int = None, event_id:int=None):
        if user is not None:
            u_id = user.id
        else:
            u_id = ctx.user.id
        bot_user = await Database.select_user_discord(u_id)
        if bot_user is None:
            return await ctx.followup.send("User not linked.")
        smmo_id = bot_user.smmo_id if smmo_id is None else smmo_id

        is_empty,user_events = helpers.gen_is_empty(await Database.select_event_user_partecipants(smmo_id))
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
        
        emb = helpers.Embed(
            title=f"[{user_evt.name}]'s overall from {evt.name}",
            description=f"**Last updated**: <t:{int(datetime.now().timestamp())}:R>\nEvent formula: `{evt.event_type.upper()}`",
            url=f"https://simple-mmo.com/user/view/{smmo_id}"
        )

        start_datetime = datetime(evt.start_year,evt.start_month,evt.start_day,hour=12,tzinfo=timezone.utc)
        ending_datetime = datetime(evt.end_year,evt.end_month,evt.end_day,hour=12,tzinfo=timezone.utc)
        
        starting_stats = await Database.select_user_stat(smmo_id,start_datetime.year,start_datetime.month,start_datetime.day)
        ending_stats = await Database.select_user_stat(smmo_id,ending_datetime.year,ending_datetime.month,ending_datetime.day)


        day_count = (ending_datetime - start_datetime).days
        msg = ""
        temp_stats = starting_stats
        temp_point = None
        _exit = False
        for i,single_date in enumerate((start_datetime + timedelta(n) for n in range(1,day_count))):
            if day_count == i:
                day_stats = ending_stats
            else:
                day_stats = await Database.select_user_stat(smmo_id,single_date.year,single_date.month,single_date.day)
            
            if not _exit and day_stats is None:
                day_stats = await SMMOApi.get_player_info(smmo_id)
                _exit = True

            steps = day_stats.steps - starting_stats.steps
            npc = day_stats.npc_kills - starting_stats.npc_kills
            pvp = day_stats.user_kills - starting_stats.user_kills

            points = helpers.evaluate_formula(evt.event_type,steps,npc,pvp)
            
            steps = day_stats.steps - temp_stats.steps
            npc = day_stats.npc_kills - temp_stats.npc_kills
            pvp = day_stats.user_kills - temp_stats.user_kills

            if not _exit:
                temp = (
                    f"- Day {i+1} (<t:{int(single_date.timestamp())}:d>):\n"
                    f"> NPC: {npc:,}\n"
                    f"> PVP: {pvp:,}\n"
                    f"> STEPS: {steps:,}\n"
                    f"> ---------------\n"
                    f"> Points: {points:,}{f" (+{points-temp_point:,})" if temp_point is not None else ""}\n"
                )
            else:
                temp = f"- Day {i} (<t:{int(single_date.timestamp())}:d>):\n"
            if len(msg)+len(temp) < 1024:
                msg += temp
            else:
                emb.add_field(name="",value=msg,inline=False)
                msg = temp
            if _exit:
                continue
            temp_point = points
            temp_stats = day_stats
        
        if msg != "":
            emb.add_field(name="",value=msg,inline=False)
        
        await helpers.send(ctx,embed=emb)



def setup(client:Bot):
    client.add_cog(Events(client))
    client.add_cog(EventTasks(client))
    
