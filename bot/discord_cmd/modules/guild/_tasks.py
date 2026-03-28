from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger

from datetime import datetime, time, date, timezone, timedelta

class GuildTask(Cog):
    def __init__(self, client):
        self.client = client
        self.check_stats.start()
        self.check_raid.start()
        # import asyncio
        # asyncio.run(self.check_stats())

    def cog_unload(self):
        self.check_stats.cancel()
        self.check_raid.cancel()

        
    @loop(time=time(hour=12))
    async def check_stats(self, end_season:bool=False,start_season:bool=False):
        logger.info("Started saving guild stats.")
        season_id:int = await Database.select_last_season_id()
        current_guild = await SMMOApi.get_guild_season_leaderboard(season_id)
        id = set()
        guilds: list[int] = await Database.select_all_server_guild()
        date = datetime.now(tz=timezone.utc)
        if end_season:
            date = helpers.get_current_date_game() + timedelta(days=1)
        elif start_season:
            date = helpers.get_current_date_game()
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

def setup(client):
    client.add_cog(GuildTask(client))
