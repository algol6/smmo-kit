import asyncio

from discord import Bot
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from datetime import datetime, timezone, timedelta,time
from bot.api._api import ApiError
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.helpers import helpers

from bot.api import SMMOApi
from bot.database import Database
from bot.api.model import GuildSeasonLeaderboard
from bot.core import GuildMembersManager
from itertools import chain

class UsersTask(Cog):
    def __init__(self, client):
        self.client = client
        self.check_stats.start()
        #import asyncio
        #asyncio.run(self.check_stats())

    def cog_unload(self):
        self.check_stats.cancel()

    @loop(time=time(hour=12))
    async def check_stats(self):
        logger.info("Started saving user stats.")
        users = chain(await Database.select_all_user(), await Database.select_track())
        ids = set()
        guild_ids = set()
        banned = await Database.select_banned()
        current_guild = chain(
            await SMMOApi.get_guild_season_leaderboard(await Database.select_last_season_id()),
            await Database.select_all_server_guild()
        )

        players_info = {}
        for g in current_guild:
            g_id = g.guild["id"] if isinstance(g,GuildSeasonLeaderboard) else g
            if g_id in guild_ids:
                continue

            guild_ids.add(g_id)

            guild_members_mgr = GuildMembersManager(g_id)
            await guild_members_mgr.fetch_members(True)
            if guild_members_mgr.members:
                for mbr in guild_members_mgr.members.values():
                    players_info[mbr.user_id] = mbr.name
            await guild_members_mgr.save()


        logger.info("STARTING LINKED USERS")
        for user in users:
            if user is None and user.smmo_id is None:
                continue
            if user.smmo_id in ids:
                continue
            date = datetime.now(tz=timezone.utc)
            date_timestamp = int(date.timestamp())
            if user.smmo_id in banned:
                date2 = date - timedelta(days=1)
                data = await Database.select_user_stat(user.smmo_id, date2.year, date2.month, date2.day)
                if data is None:
                    continue
                if not await Database.insert_user_stat(data.smmo_id,date.year,date.month,date.day,date_timestamp,data.level,data.steps,data.npc_kills,data.user_kills,data.quests_performed,data.bounties_completed,data.reputation,data.chests_opened):
                    logger.warning("Error while saving linked user (banned): %s",user)
                continue
            player = await SMMOApi.get_player_info(user.smmo_id)

            #player = None
            #n = 1
            #while player is None:
            #    try:
            #        print(player)
            #        print(n)
            #        player = await SMMOApi.get_player_info(user.smmo_id)
            #        print(player)
            #    except ApiError:
            #        player = None
            #        await asyncio.sleep(60*n)
            #        n+=1
            if player is not None and player.id is not None:
                players_info[player.id] = player.name
                if not await Database.insert_user_stat(player.id,date.year,date.month,date.day,date_timestamp,player.level,player.steps,player.npc_kills,player.user_kills,player.quests_performed,player.bounties_completed,player.reputation,player.chests_opened):
                    if not await Database.update_user_stat(player.id,date.year,date.month,date.day,player.quests_performed,player.bounties_completed,player.reputation,player.chests_opened):
                        logger.warning("Error while updating linked user: %s",user)
                ids.add(user.smmo_id)
                if player.banned:
                    await Database.insert_banned(player.id)
        logger.info("ENDED LINKED USERS")
        logger.info("User save complete.")

        try:
            logger.info("Starting to repopulate best user stats")
            await UsersTask.repopulate_best_table(players_info)
            logger.info("Repopulating Best stats. done.")
        except:
            logger.exception("BEST TABLE BIP BOP BOOM")

    @staticmethod
    async def repopulate_best_table(players_info:dict) -> None:
        CATEGORIES = ('NPC','STEPS','PVP','LEVEL')
        bulk_inserts = []
        dt = helpers.get_current_date_game()
        ids = [x for x in players_info]
        current_stats = await Database.select_user_stat_bulk(ids,dt.year,dt.month,dt.day)
        dt -= timedelta(days=1)
        yesterd_stats = await Database.select_user_stat_bulk(ids,dt.year,dt.month,dt.day)
        for smmo_id, name in players_info.items():
            bests = {x.category : x for x in await Database.select_best(smmo_id)}
            skip = True
            for category in CATEGORIES:
                if bests:
                    skip = False
                    last_gain = None
                    best_gain = None
                    if smmo_id in current_stats and smmo_id in yesterd_stats:
                        match category:
                            case "LEVEL":
                                last_gain = current_stats[smmo_id].level - yesterd_stats[smmo_id].level
                                best_gain = bests[category].levels
                            case "PVP":
                                last_gain = current_stats[smmo_id].user_kills - yesterd_stats[smmo_id].user_kills
                                best_gain = bests[category].pvp
                            case "STEPS":
                                last_gain = current_stats[smmo_id].steps - yesterd_stats[smmo_id].steps
                                best_gain = bests[category].steps
                            case "NPC":
                                last_gain = current_stats[smmo_id].npc_kills - yesterd_stats[smmo_id].npc_kills
                                best_gain = bests[category].npc


                    if best_gain is None or last_gain is None:
                        skip = True

                    if not skip and best_gain <= last_gain:
                            stats = current_stats[smmo_id]
                            level = stats.level - yesterd_stats[smmo_id].level
                            steps = stats.steps - yesterd_stats[smmo_id].steps
                            npc = stats.npc_kills - yesterd_stats[smmo_id].npc_kills
                            pvp = stats.user_kills - yesterd_stats[smmo_id].user_kills
                            time = stats.time
                    elif not skip:
                        stats = current_stats[smmo_id]
                        level = bests[category].levels
                        steps = bests[category].steps
                        npc = bests[category].npc
                        pvp = bests[category].pvp
                        time = bests[category].date
                if skip:
                    match category:
                        case "LEVEL":
                            stats = await Database.select_best_level_stats(smmo_id)
                        case "PVP":
                            stats = await Database.select_best_pvp_stats(smmo_id)
                        case "STEPS":
                            stats = await Database.select_best_step_stats(smmo_id)
                        case "NPC":
                            stats = await Database.select_best_npc_stats(smmo_id)
                    bulk_inserts.append(
                        (
                            smmo_id,
                            name,
                            category,
                            int(stats.time),
                            stats.level,
                            stats.steps,
                            stats.npc_kills,
                            stats.user_kills
                        )
                    )
                    continue
                bulk_inserts.append(
                    (
                        smmo_id,
                        name,
                        category,
                        int(time),
                        level,
                        steps,
                        npc,
                        pvp
                    )
                )
        await Database.delete_best_bulk(ids)
        res = await Database.insert_best_bulk(bulk_inserts)
        if not res:
            logger.warning("Updating best stats")
        return


def setup(client:Bot):
    client.add_cog(UsersTask(client))
