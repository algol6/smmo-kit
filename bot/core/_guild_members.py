from asyncio import sleep

from bot.api._api import ApiError
from bot.database import Database
from bot.api import SMMOApi
from bot.discord_cmd.helpers.logger import logger
from datetime import timezone,datetime

class Cache:
    def __init__(self):
        self.data = {}

    def __len__(self):
        return sum(len(group) for group in self.data.values())

    def __getitem__(self,index):
        if not isinstance(index, tuple):
            index = (index,)
        main = self.data.get(index[0])
        if not main:
            return None
        if len(index) == 1:
            return main
        return main.get(index[1])

    def __setitem__(self,key,value):
        self.data.setdefault(key, {}).update({v.user_id : v for v in value})

class GuildMembersManager:
    _cache = Cache()
    _last_updates = {}

    def __init__(self,guild_id:int):
        self.guild_id = guild_id
        self.members = None

    async def fetch_members(self,force:bool = False):
        last_guild_update = self._last_updates.get(self.guild_id, 0)
        recent_updated = last_guild_update > datetime.now().timestamp() - 600
        if recent_updated and not force and self._fetch_cache():
            return
        data = await SMMOApi.get_guild_members(self.guild_id)
        #data = None
        #n = 1
        #while data is None:
        #    try:
        #        data = await SMMOApi.get_guild_members(self.guild_id)
        #    except ApiError:
        #        await sleep(60*n)
        #        n += 1
        if data:
            self._last_updates[self.guild_id] = datetime.now().timestamp()
            self._cache[self.guild_id] = data
            self.members = self._cache[self.guild_id]

    def _fetch_cache(self):
        cached = self._cache[self.guild_id]
        if cached:
            self.members = cached
            return True
        return False

    async def save(self):
        dt = datetime.now(tz=timezone.utc)
        ts = dt.timestamp()
        if self.members:
            try:
                if not await Database.insert_user_stat_bulk([(member.user_id,dt.year,dt.month,dt.day,ts,member.level,member.steps,member.npc_kills,member.user_kills,-1,-1,0,-1) for member in self.members.values()]):
                    logger.warning("Error while saving users from guild_members of season lb: %s",self.guild_id)
            except:
                logger.exception("Save ERROR")
                for member in self.members.values():
                    if not await Database.insert_user_stat(member.user_id,dt.year,dt.month,dt.day,ts,member.level,member.steps,member.npc_kills,member.user_kills,-1,-1,0,-1):
                        logger.warning("Error while saving user from guild_members of season lb: %s",member.name)
