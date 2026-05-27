from bot.database import Database
from functools import wraps
from bot.discord_cmd.helpers import helpers
from ._guild_members import GuildMembersManager
from bot.api import SMMOApi
from datetime import datetime

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
        self.data.setdefault(key, {}).update({v.smmo_id : v for v in value})

class CacheTeam(Cache):
    def __setitem__(self,key,value):
        val = {}
        for i,v in value.items():
            val.setdefault(v.team,{}).update({i: v})
        self.data.setdefault(key, {}).update(val)

class CacheStats(Cache):
    pass

def require_cache(attribute: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if getattr(self, attribute) is None:
                await getattr(self, f"fetch_{attribute}")()
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

class CacheEvent:
    def __init__(self):
        self.events = {}
        self.partecipants = Cache()
        self.teams = CacheTeam()
        self.starting_stats = CacheStats()

class EventManager:
    _cache = CacheEvent()
    def __init__(self,event):
        self.evt = event
        self.partecipants = None
        self.teams = None
        self.starting_stats = None

    def has_ended(self) -> bool:
        return self.evt.end_time < datetime.now().timestamp()

    async def fetch_partecipants(self,force:bool=False):
        if not force and self._fetch_cache_partecipants():
            return
        self._cache.partecipants[self.evt.id] = await Database.select_event_partecipants(self.evt.id)
        self.partecipants = self._cache.partecipants[self.evt.id]
        if self.partecipants is None:
            return
        self._cache.teams[self.evt.id] = self._cache.partecipants[self.evt.id]
        self.teams = self._cache.teams[self.evt.id]
        
    def _fetch_cache_partecipants(self):
        cached1 = self._cache.partecipants[self.evt.id]
        cached2 = self._cache.teams[self.evt.id]
        if cached1 and cached2:
            self.partecipants = cached1
            self.teams = cached2
            return True
        return False

    @require_cache('partecipants')
    async def fetch_starting_stats(self,force:bool=False):
        if not force and self._fetch_starting_stats():
            return
        if self.partecipants is None:
            return
        stats = await Database.select_user_stat_bulk([id for id in self.partecipants],self.evt.start_year,self.evt.start_month,self.evt.start_day)
        self._cache.starting_stats[self.evt.id] = [x for x in stats.values()]
        self.starting_stats = self._cache.starting_stats[self.evt.id]

    def _fetch_starting_stats(self):
        cached = self._cache.starting_stats[self.evt.id]
        if cached:
            self.starting_stats = cached
            return True
        return False

    @require_cache('starting_stats')
    async def get_partecipants_points(self,team:str=None):
        if self.partecipants is None:
            return {}
        event_teams = {}
        current_date = helpers.get_current_date_game()
        temp_user_stats = {u_id: u for guild in GuildMembersManager._cache.data.values() for u_id,u in guild.items()}
        has_ended = self.has_ended()
        if has_ended:
            end_stats = await Database.select_user_stat_bulk([id for id in self.partecipants],self.evt.end_year,self.evt.end_month,self.evt.end_day)
        else:
            start_day_stats = await Database.select_user_stat_bulk([id for id in self.partecipants],current_date.year,current_date.month,current_date.day)
        for p in self.partecipants.values():
            if team is not None and p.team != team:
                continue
            if has_ended:
                current_stats = end_stats[p.smmo_id]
            else:
                sds = start_day_stats.get(p.smmo_id)
                if sds is None:
                    continue
                current_stats = temp_user_stats.get(p.smmo_id)
                if current_stats is None:
                    current_stats = await SMMOApi.get_player_info(p.smmo_id)
                if current_stats is None:
                    continue
            
            p.team = p.team or "No Team"

            user_points = helpers.evaluate_formula(
                self.evt.event_type,
                current_stats.steps-self.starting_stats[p.smmo_id].steps,
                current_stats.npc_kills-self.starting_stats[p.smmo_id].npc_kills,
                current_stats.user_kills-self.starting_stats[p.smmo_id].user_kills
            )
            if has_ended:
                today_points = 0
            else:
                today_points = helpers.evaluate_formula(
                    self.evt.event_type,
                    sds.steps-self.starting_stats[p.smmo_id].steps,
                    sds.npc_kills-self.starting_stats[p.smmo_id].npc_kills,
                    sds.user_kills-self.starting_stats[p.smmo_id].user_kills
                )
            event_teams.setdefault(p.team,{}).update(
                {p.smmo_id:{
                    "player":p,
                    "stats": user_points+p.points,
                    "gains": user_points-today_points,
                    "extra": p.points,
                    "name":p.name
                    }
                }
            )
        return event_teams if team is None else event_teams.get(team,{})