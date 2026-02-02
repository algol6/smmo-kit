from discord import Bot,ApplicationContext,slash_command,guild_only,option,Member,File
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from datetime import datetime, timezone, timedelta,time
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.helpers import helpers

from bot.api import SMMOApi
from bot.database import Database
from itertools import chain


class UsersTask(Cog):
    def __init__(self, client):
        self.client = client
        self.check_stats.start()

    def cog_unload(self):
        self.check_stats.cancel()

    @loop(time=time(hour=12))
    async def check_stats(self):
        logger.info("Started saving user stats.")
        users = chain(await Database.select_all_user(), await Database.select_track())
        ids = set()
        guild_ids = set()
        banned = await Database.select_banned()
        current_guild: list = await SMMOApi.get_guild_season_leaderboard(await helpers.get_current_season_id())

        players_info = {}
        for g in current_guild:
            guild_ids.add(g.guild["id"])
            guild = await SMMOApi.get_guild_members(g.guild["id"])
            date = datetime.now(tz=timezone.utc)
            date_timestamp = date.timestamp()
            for user in guild:
                if user is None or user.user_id in banned:
                    continue
                players_info[str(user.user_id)] = user.name
                if not await Database.insert_user_stat(user.user_id,date.year,date.month,date.day,date_timestamp,user.level,user.steps,user.npc_kills,user.user_kills,-1,-1,0,-1):
                    logger.warning("Error while saving user from guild_members of season lb: %s",user)
                ids.add(user.user_id)
                if user.banned:
                    await Database.insert_banned(user.user_id)

        guilds = await Database.select_all_server_guild()
        for guild in guilds:
            if guild in guild_ids:
                continue
            member_guild = await SMMOApi.get_guild_members(guild)
            date = datetime.now(tz=timezone.utc)
            date_timestamp = date.timestamp()
            for user in member_guild:
                if user.user_id in ids or user.user_id in banned:
                    continue
                players_info[str(user.user_id)] = user.name
                # player = await SMMOApi.get_player_info(user.user_id)
                # if player is not None:
                #     await Database.insert_user_stat(player)
                # stats_x_best.append([user,date])
                if not await Database.insert_user_stat(user.user_id,date.year,date.month,date.day,date_timestamp,user.level,user.steps,user.npc_kills,user.user_kills,-1,-1,0,-1):
                    logger.warning("Error while saving user from guild_members not in season lb: %s",user)
                ids.add(user.user_id)
                if user.banned:
                    await Database.insert_banned(user.user_id)

        for user in users:
            if user is None and user.smmo_id is None:
                continue
            if user.smmo_id in ids:
                continue
            date = datetime.now(tz=timezone.utc)
            date_timestamp = date.timestamp()

            if user.smmo_id in banned:
                date2 = date - timedelta(days=1)
                data = await Database.select_user_stat(user.smmo_id, date2.year, date2.month, date2.day)
                if data is None:
                    continue
                if not await Database.insert_user_stat(data.smmo_id,date.year,date.month,date.day,date_timestamp,data.level,data.steps,data.npc_kills,data.user_kills,data.quest_performed,data.bounties_completed,data.reputation,data.chests_opened):
                    logger.warning("Error while saving linked user (banned): %s",user)
                continue
            player = await SMMOApi.get_player_info(user.smmo_id)
            if player is not None and player.id is not None:
                players_info[str(player.id)] = player.name
                # stats_x_best.append([player,date])
                if not await Database.insert_user_stat(player.id,date.year,date.month,date.day,date_timestamp,player.level,player.steps,player.npc_kills,player.user_kills,player.quests_performed,player.bounties_completed,player.reputation,player.chests_opened):
                    logger.warning("Error while saving linked user: %s",user)

                ids.add(user.smmo_id)
                if player.banned:
                    await Database.insert_banned(player.id)
        logger.info("User save complete.")

        await UsersTask.repopulate_best_table(players_info)

    @staticmethod
    async def repopulate_best_table(players_info:dict) -> None:
        logger.info("Starting to repopulate best user stats")

        # GODS ONLY KNOW WHY I'M DOING THIS T-T

        all_data = await Database.data_for_best()

        all_data = all_data.sort_values(by=['smmo_id', 'date'])

        all_data['daily_npc'] = all_data.groupby('smmo_id')['npc_kills'].diff()
        all_data['daily_steps'] = all_data.groupby('smmo_id')['steps'].diff()
        all_data['daily_user_kills'] = all_data.groupby('smmo_id')['user_kills'].diff()
        all_data['daily_level'] = all_data.groupby('smmo_id')['level'].diff()

        all_data['daily_npc'] = all_data['daily_npc'].fillna(0)
        all_data['daily_steps'] = all_data['daily_steps'].fillna(0)
        all_data['daily_user_kills'] = all_data['daily_user_kills'].fillna(0)
        all_data['daily_level'] = all_data['daily_level'].fillna(0)


        cat = {
            "STEP":all_data.groupby('smmo_id')['daily_steps'].idxmax(),
            "NPC":all_data.groupby('smmo_id')['daily_npc'].idxmax(),
            "PVP":all_data.groupby('smmo_id')['daily_user_kills'].idxmax(),
            "LEVEL":all_data.groupby('smmo_id')['daily_level'].idxmax()
        }
        for label, idx_series in cat.items():
            best_df = all_data.loc[idx_series].reset_index().drop_duplicates(subset=['smmo_id'], keep='first')

            print(f"Updating database for category: {label} ({len(best_df)} players)")

            for _, row in best_df.iterrows():
                sid = row['smmo_id']
                print(sid)
                await Database.delete_best(sid, label)
                try:
                    await Database.insert_best(
                        sid, 
                        players_info[str(sid)],
                        label, 
                        row['date'], 
                        row['daily_level'], 
                        row['daily_steps'], 
                        row['daily_npc'], 
                        row['daily_user_kills']
                    )
                except KeyError:
                    logger.warning("Error when updating best stats of user: %s",str(sid))
        logger.info("Repopulating Best stats. done.")

    
    
def setup(client:Bot):
    client.add_cog(UsersTask(client))
