from discord import Bot
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from datetime import datetime, timezone, timedelta,time
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.helpers import helpers

from bot.api import SMMOApi
from bot.database import Database
from bot.api.model import GuildSeasonLeaderboard
from bot.core import GuildMembersManager
from itertools import chain

import pandas as pd
import numpy as np

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
        current_guild: list = chain(await SMMOApi.get_guild_season_leaderboard(await Database.select_last_season_id()),await Database.select_all_server_guild())

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
            await UsersTask.repopulate_best_table(players_info)
            #await UsersTask.repopulate_best_table_pandas(players_info)
        except:
            logger.exception("BEST TABLE BIP BOP BOOM")


    @staticmethod
    async def repopulate_best_table_pandas(players_info: dict) -> None:
        if not players_info:
            return
        logger.info("Starting to repopulate best user stats")


        ids_tuple = tuple(players_info.keys())
        placeholders = ",".join("?" for _ in ids_tuple)

        raw_rows = await Database._select(
            f"""SELECT smmo_id, year, month, day, time, level, steps, npc_kills, user_kills
                FROM user_stats WHERE smmo_id IN ({placeholders})""",
            ids_tuple
        )
        if not raw_rows:
            return


        ANALYTICAL_SCHEMA = {
            "smmo_id": "int32[pyarrow]",
            "year": "int16[pyarrow]",
            "month": "int8[pyarrow]",
            "day": "int8[pyarrow]",
            "time": "float64[pyarrow]",
            "level": "int32[pyarrow]",
            "steps": "int32[pyarrow]",
            "npc_kills": "int32[pyarrow]",
            "user_kills": "int32[pyarrow]",
        }

        df = pd.DataFrame(raw_rows, columns=list(ANALYTICAL_SCHEMA.keys()))

        for cat in ['time','level','npc_kills','user_kills','steps']:
            df[cat] = np.trunc(df[cat])

        df = df.astype(ANALYTICAL_SCHEMA)
        #df = pd.DataFrame(raw_rows, columns=[
        #    'smmo_id', 'year', 'month', 'day', 'time', 'level', 'steps', 'npc_kills', 'user_kills'
        #]).astype(
        #    {
        #    "smmo_id": "uint16",
        #    "year": "uint16",
        #    "month": "uint8",
        #    "day": "uint8",
        #    "time": "int64",
        #    "level": "int32",
        #    "steps": "uint32",
        #    "npc_kills": "uint32",
        #    "user_kills": "uint32",
        #})
        df = df.sort_values(by=['smmo_id', 'year', 'month', 'day'])

        categories = {'LEVEL': 'level', 'STEPS': 'steps', 'NPC': 'npc_kills', 'PVP': 'user_kills'}
        bulk_inserts = []

        for cat_name, column in categories.items():
            df[f'{cat_name}_gain'] = df.groupby('smmo_id')[column].diff()

            # Isolate absolute maximum index for each partition slice
            idx = df.dropna(subset=[f'{cat_name}_gain']).groupby('smmo_id')[f'{cat_name}_gain'].idxmax()
            max_rows = df.loc[idx]

            for _, row in max_rows.iterrows():
                bulk_inserts.append((
                    int(row['smmo_id']), players_info[int(row['smmo_id'])], cat_name,
                    int(row['time']), int(row['level']), int(row['steps']),
                    int(row['npc_kills']), int(row['user_kills'])
                ))

        await Database.delete_best_bulk(ids_tuple)
        res = await Database.insert_best_bulk(bulk_inserts)
        if not res:
            logger.warning("Updating best stats")
        logger.info("Repopulating Best stats. done.")


    @staticmethod
    async def repopulate_best_table(players_info:dict) -> None:
        CATEGORIES = ('NPC','STEPS','PVP','LEVEL')
        bulk_inserts = []
        logger.info("Starting to repopulate best user stats")
        dt = helpers.get_current_date_game()
        ids = [x for x in players_info]
        current_stats = await Database.select_user_stat_bulk(ids,dt.year,dt.month,dt.day)
        dt -= timedelta(days=1)
        yesterd_stats = await Database.select_user_stat_bulk(ids,dt.year,dt.month,dt.day)
        print("BEST TABLE UPDATE")
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
                        print("Skip?")

                    if not skip and best_gain <= last_gain:
                            stats = current_stats[smmo_id]
                            stats.level -= yesterd_stats[smmo_id].level
                            stats.steps -= yesterd_stats[smmo_id].steps
                            stats.npc_kills -= yesterd_stats[smmo_id].npc_kills
                            stats.user_kills -= yesterd_stats[smmo_id].user_kills
                    elif not skip:
                        stats = current_stats[smmo_id]
                        stats.level = bests[category].levels
                        stats.steps = bests[category].steps
                        stats.npc_kills = bests[category].npc
                        stats.user_kills = bests[category].pvp
                        stats.time = bests[category].date
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
                        stats.time,
                        stats.level,
                        stats.steps,
                        stats.npc_kills,
                        stats.user_kills
                    )
                )
        print(ids)
        print(bulk_inserts)
        await Database.delete_best_bulk(ids)
        res = await Database.insert_best_bulk(bulk_inserts)
        if not res:
            logger.warning("Updating best stats")
        logger.info("Repopulating Best stats. done.")
        return


def setup(client:Bot):
    client.add_cog(UsersTask(client))
