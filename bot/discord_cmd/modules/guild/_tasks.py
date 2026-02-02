from discord import slash_command, ApplicationContext,AutocompleteContext, Bot, guild_only, option, Role, TextChannel
from discord.ext.commands import Cog
from pycord.multicog import subcommand
from discord.ext.tasks import loop

from bot.api import SMMOApi
from bot.database import Database
from bot.api.model import GuildSeasonLeaderboard, GuildMemberInfo, PlayerInfo
from bot.database.model import UserStat, Requirements
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger

from random import random, choice
from datetime import datetime, time, date, timezone, timedelta
from math import floor
from matplotlib import pyplot as plt
import pandas as pd

class GuildTask(Cog):
    def __init__(self, client):
        self.client:Bot = client
        self.check_stats.start()
        self.check_raid.start()

    def cog_unload(self):
        self.check_stats.cancel()
        self.check_raid.cancel()

        
    @loop(time=time(hour=12))
    async def check_stats(self):
        logger.info("Started saving guild stats.")
        season_id:int = await helpers.get_current_season_id()
        current_guild = await SMMOApi.get_guild_season_leaderboard(season_id)
        id = set()
        guilds: list[int] = await Database.select_all_server_guild()
        date = datetime.now(tz=timezone.utc)
        date_timestamp = date.timestamp()
        for g in current_guild:
            try:
                await Database.insert_guild_stats(date.year,date.month,date.day,date_timestamp,g.guild["id"],g.position,g.experience,season_id)
                id.add(g.guild["id"])
            except Exception as e:
                logger.exception("while saving stats from season lb:\n%s",e)

        for i in guilds:
            if i in id:
                continue
            data = await SMMOApi.get_guild_info(i)
            if data is None:
                continue
            if not await Database.insert_guild_stats(date.year,date.month,date.day,date_timestamp,i,0,data.current_season_exp,season_id):
                logger.warning("Error while saving stats from guild not in season lb: %s",data.name)

        logger.info("Guild stats saved.")


    @loop(minutes=5)
    async def check_raid(self):
        raids = await Database.select_all_raid()
        time = datetime.now(tz=timezone.utc).timestamp()
        for raid in raids:
            if raid.time + raid.duration*3600 >= time:
                continue

            await helpers.get_channel_and_edit(self.client,raid.channel_id,content=f"<@&{raid.role_id}> {raid.duration}h raid ended.")
            await Database.delete_raid(raid.channel_id)

def setup(client:Bot):
    client.add_cog(GuildTask(client))