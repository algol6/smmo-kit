from discord import Bot,NotFound
from discord.ext.tasks import loop
from discord.ext.commands import Cog

from bot.api import SMMOApi,ApiError
from bot.database import Database
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger

from random import shuffle
from collections import Counter, defaultdict
from datetime import datetime,time,timezone

class EventTasks(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.create_teams.start()
        self.update_leaderboard.start()
        self.event_notif.start()
        #self.register_partecipants.start()

    def cog_unload(self) -> None:
        self.create_teams.cancel()
        self.update_leaderboard.cancel()
        self.event_notif.cancel()
        #self.register_partecipants.cancel()

    @loop(time=time(hour=12,minute=5))
    async def event_notif(self):
        today = helpers.get_current_date_game()
        event = await Database.select_events_by_starting_day(today.year,today.month,today.day)
        for e in event:
            participants = await Database.select_event_partecipants(e.id)
            try:
                chn = await self.client.fetch_channel(e.channel_id)
            except:
                logger.exception("Getting the channel")
                continue
            for partecipant in participants:
                try:
                    chn.send(f"<@{partecipant.discord_id}> Event '{e.name}' Started, Go and earn your prize",delete_after=1,silent=True)
                except Exception as e:
                    logger.exception("Sending not event start")
                    continue


    @loop(minutes=15)
    async def create_teams(self):
        dt = int(datetime.now().timestamp())
        event = await Database.select_all_events(dt)
        for evt in event:
            if evt.start_time >= dt or evt.end_time < dt:
                continue
            partecipants = list(await Database.select_event_partecipants(evt.id))
            shuffle(partecipants)
            count = Counter(x.team for x in partecipants)
            count.update(str(x) for x in range(1,len(partecipants)+1))
            for part in partecipants:
                if part.team != "":
                    continue
                for i in count:
                    if count[i] >= evt.team_size+1:
                        continue
                    count.update([i])
                    await Database.update_event_partecipant(part.smmo_id,part.event_id,str(i))
                    break


    @loop(hours=1)
    async def update_leaderboard(self):
        data = await Database.select_all_event_lb()
        event = await Database.select_all_events(int(datetime.now().timestamp()))
        for e in event:
            for d in data:
                if e.id != d.event_id:
                    continue
                if e.end_time < datetime.now().timestamp():
                    continue
                if e.start_time > datetime.now().timestamp():
                    continue
                emb = await self.make_embed(e)
                await helpers.get_channel_and_edit(self.client,d.channel_id,d.message_id,embed=emb)


    @loop(minutes=15)
    async def register_partecipants(self):
        #unused
        events = await Database.select_all_events(datetime.now().timestamp())
        for evt in events:
            if evt is None:
                continue
            try:
                chn = await self.client.fetch_channel(evt.channel_id)
                msg = await chn.fetch_message(evt.message_id)
                # users = set(y for x in msg.reactions async for y in x.users().flatten())
                discord_users = set()
                for reaction in msg.reactions:
                    async for user in reaction.users():
                        discord_users.add(user)
            except Exception as e:
                logger.exception("REGISTER PARTECIPANTS")
                print(e)
                continue
            guildy = None
            if evt.guildies_only:
                guildy = set(x.user_id for x in await SMMOApi.get_guild_members(evt.guild_id))
            for user in discord_users:
                g_user = await Database.select_user_discord(user.id)
                if g_user is None:
                    continue
                if await Database.select_event_partecipant(evt.id,g_user.smmo_id):
                    continue
                if evt.guildies_only and g_user.smmo_id not in guildy:
                    continue
                u = await SMMOApi.get_player_info(g_user.smmo_id)
                await Database.insert_event_partecipant(g_user.smmo_id,u.name,g_user.discord_id,evt.id,"")


    @staticmethod
    async def make_embed(event) -> helpers.Embed:
        event_partecipants = await Database.select_event_partecipants(event.id)

        event_teams:dict = dict()
        current_date = helpers.get_current_date_game()
        if event.guildies_only:
            guild_member = tuple(await SMMOApi.get_guild_members(event.guild_id))
            
        for partecipant in event_partecipants:
            user_stats = await Database.select_user_stat(partecipant.smmo_id,event.start_year,event.start_month,event.start_day)
            if user_stats is None:
                continue
            start_day_stats = await Database.select_user_stat(partecipant.smmo_id,current_date.year,current_date.month,current_date.day)
            if start_day_stats is None:
                continue
            # TODO: make more efficient t-t
            if event.guildies_only:
                current_stats = next((x for x in guild_member if x.user_id == partecipant.smmo_id), None)
            else:
                current_stats = await SMMOApi.get_player_info(partecipant.smmo_id)

            if current_stats is None:
                continue
            
            if partecipant.team == "":
                partecipant.team = "No Team"
            if partecipant.team not in event_teams:
                event_teams[partecipant.team] = []

            curr_stats = helpers.evaluate_formula(event.event_type,
                                                 current_stats.steps-user_stats.steps,
                                                 current_stats.npc_kills-user_stats.npc_kills,
                                                 current_stats.user_kills-user_stats.user_kills)
            today_stats = helpers.evaluate_formula(event.event_type,
                                                  start_day_stats.steps-user_stats.steps,
                                                  start_day_stats.npc_kills-user_stats.npc_kills,
                                                  start_day_stats.user_kills-user_stats.user_kills)
            
            if not helpers.is_number(curr_stats) or not helpers.is_number(today_stats):
                return helpers.Embed(title="Error with event Formula")
            event_teams[partecipant.team].append({"player":partecipant,"stats": curr_stats, "gains": curr_stats-today_stats, "name":current_stats.name})

        if len(event_teams) == 0:
            return helpers.Embed(title="No Data")

        # evt.event_teams = {k[0]:sum(y["stats"] for y in k[1]) for k in sorted(event_teams.items(), key=lambda item: sum(x["stats"] for x in item[1]), reverse=True)}
        event_lb = [(k,sum(y["stats"] for y in event_teams[k]), [x["player"] for x in event_teams[k]]) for k in sorted(event_teams, key=lambda item: sum(x["stats"] for x in event_teams[item]), reverse=True)][:10]
        emb = helpers.Embed(title="",
                                  description=f"Last Update: <t:{int(datetime.now().timestamp())}:R>")
        
        for v,i in zip(event_lb,range(1, 11)):
            if event.team_size == 1:
                msg = f"#{i} - {v[2][0].name}: {v[1]:,}"
            else:
                msg = f"#{i} - Team '{v[0]}': {v[1]:,}"
            emb.add_field(name="",
                        #   value=f"#{i} - Team '{v[0]}' (Total: {v[1]:,})",
                          value=msg,
                          inline=False)
        emb.set_footer(text=f"Updated every hour")
        
        return emb
        
                
