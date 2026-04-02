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

class CommunityTasks(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.listing_cleanup.start()

    def cog_unload(self) -> None:
        self.listing_cleanup.cancel()

    @loop(time=time(hour=12))
    async def listing_cleanup(self):
        await Database.delete_old_market_item()