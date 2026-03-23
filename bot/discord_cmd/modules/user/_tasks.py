from discord import Bot
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from datetime import datetime, timezone, timedelta,time
from bot.discord_cmd.helpers.logger import logger

from bot.api import SMMOApi
from bot.database import Database
from bot.api.model import GuildSeasonLeaderboard
from itertools import chain

class UsersTask(Cog):
    def __init__(self, client):
        self.client = client
        self.check_stats.start()
        # import asyncio
        # asyncio.run(self.check_stats())

    def cog_unload(self):
        self.check_stats.cancel()

    @loop(time=time(hour=12))
    async def check_stats(self):
        logger.info("Started saving user stats.")
        users = chain(await Database.select_all_user(), await Database.select_track())
        ids = set()
        guild_ids = set()
        banned = await Database.select_banned()
        current_guild: list = chain(await SMMOApi.get_guild_season_leaderboard(await Database.select_last_season_id()),await Database.select_all_server_guild())

        players_info = {}
        for g in current_guild:
            if isinstance(g,GuildSeasonLeaderboard):
                g_id = g.guild["id"]
            else:
                g_id = g
            if g_id in guild_ids:
                continue
            guild_ids.add(g_id)
            guild = await SMMOApi.get_guild_members(g_id)
            date = datetime.now(tz=timezone.utc)
            date_timestamp = date.timestamp()
            for user in guild:
                if user is None or user.user_id in banned:
                    continue
                players_info[str(user.user_id)] = user.name
                if not await Database.insert_user_stat(user.user_id,date.year,date.month,date.day,date_timestamp,user.level,user.steps,user.npc_kills,user.user_kills,-1,-1,0,-1):
                    logger.warning("Error while saving user from guild_members of season lb: %s",user)
                #ids.add(user.user_id)
                if user.banned:
                    await Database.insert_banned(user.user_id)

        logger.info("STARTING LINKED USERS")
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
                if not await Database.insert_user_stat(data.smmo_id,date.year,date.month,date.day,date_timestamp,data.level,data.steps,data.npc_kills,data.user_kills,data.quests_performed,data.bounties_completed,data.reputation,data.chests_opened):
                    logger.warning("Error while saving linked user (banned): %s",user)
                continue
            player = await SMMOApi.get_player_info(user.smmo_id)
            if player is not None and player.id is not None:
                players_info[str(player.id)] = player.name
                if not await Database.insert_user_stat(player.id,date.year,date.month,date.day,date_timestamp,player.level,player.steps,player.npc_kills,player.user_kills,player.quests_performed,player.bounties_completed,player.reputation,player.chests_opened):
                    if not await Database.update_user_stat(player.id,date.year,date.month,date.day,player.quests_performed,player.bounties_completed,player.reputation,player.chests_opened):
                        logger.warning("Error while updating linked user: %s",user)
                ids.add(user.smmo_id)
                if player.banned:
                    await Database.insert_banned(player.id)
        logger.info("ENDED LINKED USERS")
        logger.info("User save complete.")

        await UsersTask.repopulate_best_table(players_info)

    @staticmethod
    async def repopulate_best_table(players_info:dict) -> None:
        CATEGORIES = ('NPC','STEPS','PVP','LEVEL')
        logger.info("Starting to repopulate best user stats")
        for smmo_id, name in players_info.items():
            for category in CATEGORIES:
                await Database.delete_best(smmo_id,category)
                match category:
                    case "LEVEL":
                        stats = await Database.select_best_level_stats(smmo_id)
                    case "PVP":
                        stats = await Database.select_best_pvp_stats(smmo_id)
                    case "STEPS":
                        stats = await Database.select_best_step_stats(smmo_id)
                    case "NPC":
                        stats = await Database.select_best_npc_stats(smmo_id)
                await Database.insert_best(
                            smmo_id, 
                            name,
                            category, 
                            stats.time, 
                            stats.level, 
                            stats.steps, 
                            stats.npc_kills, 
                            stats.user_kills
                        )
        logger.info("Repopulating Best stats. done.")
        return
        
    
def setup(client:Bot):
    client.add_cog(UsersTask(client))
