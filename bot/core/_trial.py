from bot.database import TrialDatabase
from bot.database.model import Trial,TrialCategory,TrialTask,TrialRecord,TrialTaskRequisite
from functools import wraps
from bot.discord_cmd.helpers.logger import logger
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
        self.data.setdefault(key, {})[value.id] = value
    
    def cleanup(self,key):
        self.data[key] = {}

class CacheRecord(Cache):
    pass

class CacheCategory(Cache):
    pass

class CacheTask(Cache):
    pass
        
class CacheRequisite(Cache):
    pass

class CacheTrial:
    def __init__(self):
        self.alias = {}
        self.values = []
        self.category = CacheCategory()
        self.task = CacheTask()
        self.records = CacheRecord()
        self.requisites = CacheRequisite()

    def __len__(self):
        return len(self.values)

    def __getitem__(self,index):
        idx = self.alias.get(index)
        if idx is None:
            return None
        return self.values[idx]

    def __setitem__(self,key,value):
        self.alias[key] = len(self.values)
        self.values.append(value)

    def add_key(self,existent_key,new_key):
        self.alias[new_key] = self.alias[existent_key]

    def add(self,trial):
        self.__setitem__(trial.server_id,trial)
        self.add_key(trial.server_id,trial.guild_id)


def require_cache(attribute: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if getattr(self, attribute) is None:
                await getattr(self, f"fetch_{attribute}")()
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

class TrialManager:
    _trial_cache = CacheTrial()

    def __init__(self,id:int,trial=None):
        if len(str(id)) > 5:
            self.server_id, self.guild_id = id, None
        else:
            self.server_id, self.guild_id = None, id
        if trial:
            self.server_id, self.guild_id = trial.server_id, trial.guild_id
        self.trial = trial
        self.categories = None
        self.tasks = None
        self.records = None
        self.requisites = None

        self.last_records = None 
        self.active_records = None
    
    def get_tasks_for_category(self, category_id: int):
        return self._trial_cache.task[category_id] or {}
    
    def get_requisite_for_task(self, task_id: int):
        return self._trial_cache.requisites[task_id] or {}

    async def fetch_trial(self,force:bool=False):
        if not force and self._load_trial_cache():
            return
        if self.server_id:
            self.trial = await TrialDatabase.select_trial_by_server_id(self.server_id)
            self.guild_id = self.trial.guild_id
        else:
            self.trial = await TrialDatabase.select_trial_by_guild_id(self.guild_id)
            self.server_id = self.trial.server_id

        if self.trial:
            self._trial_cache.add(self.trial)
    
    def _load_trial_cache(self) -> bool:
        cached = self._trial_cache[self.server_id or self.guild_id]
        if cached:
            self.trial = cached
            return True
        return False

    @require_cache('trial')
    async def fetch_categories(self,force:bool=False):
        if not force and self._load_category_cache():
            return
        db_cat = await TrialDatabase.select_trial_category_active(self.server_id)
        self.categories = {x.id : x for x in db_cat}
        if self.categories:
            self._trial_cache.category.cleanup(self.trial.server_id)
            for category in self.categories.values():
                self._trial_cache.category[self.trial.server_id] = category

    def _load_category_cache(self) -> bool:
        cached = self._trial_cache.category[self.server_id]
        if cached:
            self.categories = cached
            return True
        return False

    @require_cache('categories')
    async def fetch_tasks(self,force:bool=False):
        if not force and self._load_task_cache():
            return
        
        self.tasks = {}
        for cat_id in self.categories.keys():
            db_task = await TrialDatabase.select_trial_task(cat_id)
            self._trial_cache.task.cleanup(cat_id)
            for task in db_task:
                self.tasks[task.id] = task
                self._trial_cache.task[task.trial_category_id] = task
       

    def _load_task_cache(self) -> bool:
        if not self.categories:
            return False
        cached = {}
        for cat_id in self.categories.keys():
            tasks = self._trial_cache.task[cat_id]
            if not tasks:
                return False
            cached.update(tasks)
            
        self.tasks = cached
        return True

    @require_cache('tasks')
    async def fetch_records(self,force:bool=False):
        if not force and self._load_record_cache():
            return
        db_records = await TrialDatabase.select_all_trial_record(self.server_id)
        self.records = {x.id: x for x in db_records}
        for record in self.records.values():
            self._trial_cache.records[record.trial_task_id] = record

    def _load_record_cache(self) -> bool:
        if not self.tasks:
            return False
        cached = {}
        for task_id in self.tasks.keys():
            records = self._trial_cache.records[task_id]
            if records:
                cached.update(records)
        if cached:
            self.records = cached
            return True
        return False

    @require_cache('tasks')
    async def fetch_requisites(self,force:bool=False):
        if not force and self._load_requisite_cache():
            return
        self.requisites = {}
        for task_id in self.tasks:
            self._trial_cache.requisites.cleanup(task_id)
            requisites = await TrialDatabase.select_trial_task_requisite(task_id)
            for requisite in requisites:
                self.requisites[requisite.id] = requisite
                self._trial_cache.requisites[task_id] = requisite

    def _load_requisite_cache(self) -> bool:
        if not self.tasks:
            return False
        cached = {}
        for task_id in self.tasks:
            requisite = self._trial_cache.requisites[task_id]
            if not requisite:
                return False
            cached.update(requisite)
        if cached:
            self.requisites = cached
            return True
        return False
    
    async def save(self):
        if self.trial:
            await TrialDatabase.insert_trial(self.trial.server_id,self.trial.log_channel_id,self.trial.notify_channel_id,self.trial.entry_channel_id,self.trial.guild_id,self.trial.name,self.trial.enabled)
            await self.fetch_trial(True)
        map_c = {}
        if self.categories:
            inserted = False
            for category in self.categories.values():
                if category.id < 0:
                    id = await TrialDatabase.insert_trial_category(category.trial_id,category.name,category.allow_parallel)
                    inserted = True
                    map_c[category.id] = id
            if inserted:
                await self.fetch_categories(True)
        map_t = {}
        if self.tasks:
            inserted = False
            for task in self.tasks.values():
                if task.id < 0:
                    if task.trial_category_id < 0:
                        if task.trial_category_id not in map_c:
                            continue
                        task.trial_category_id = map_c[task.trial_category_id]
                    id = await TrialDatabase.insert_trial_task(task.trial_category_id,task.name,task.cooldown,task.reward,task.point,task.bonus_time,task.bonus)
                    inserted = True
                    map_t[task.id] = id
            if inserted:
                await self.fetch_tasks(True)

        if self.records:
            inserted = False
            for record in self.records.values():
                if record.id < 0:
                    if record.trial_task_id < 0:
                        if record.trial_task_id not in map_t:
                            continue
                        record.trial_task_id = map_t[record.trial_task_id]
                    await TrialDatabase.insert_trial_record(record.trial_task_id,record.smmo_id,record.user_id,record.start_time,record.end_time,record.update_time,record.start_npc,record.start_steps,record.start_pvp,record.start_levels,record.current_npc,record.current_steps,record.current_pvp,record.current_levels,record.status,record.cancelled)
                    inserted = True
            if inserted:
                await self.fetch_records(True)

        if self.requisites:
            inserted = False
            for requisite in self.requisites.values():
                if requisite.id < 0:
                    if requisite.trial_task_id < 0:
                        if requisite.trial_task_id not in map_t:
                            continue
                        requisite.trial_task_id = map_t[requisite.trial_task_id]
                    await TrialDatabase.insert_trial_task_requisite(requisite.trial_task_id,requisite.formula,requisite.goal)
                    inserted = True
            if inserted:
                await self.fetch_requisites(True)

    async def update(self,update:str,value,refetch:bool=True):
        match update:
            case "trial":
                await TrialDatabase.update_trial(value.server_id,value.log_channel_id,value.notify_channel_id,value.entry_channel_id,value.name,value.enabled)
                if refetch:
                    await self.fetch_trial(True)
            case "category":
                await TrialDatabase.update_trial_category(value.id,value.name)
                if refetch:
                    await self.fetch_categories(True)
            case "task":
                await TrialDatabase.update_trial_task(value.id,value.name,value.cooldown,value.reward,value.points,value.bonus_time,value.bonus)
                if refetch:
                    await self.fetch_tasks(True)
            case "record":
                await TrialDatabase.update_trial_record(value.current_npc,value.current_steps,value.current_pvp,value.current_levels,value.update_time,value.end_time,value.cancelled,value.status,value.id)
                if refetch:
                    await self.fetch_records(True)
            case "requisite":
                await TrialDatabase.update_trial_task_requisite(value.id,value.formula,value.goal)
                if refetch:
                    await self.fetch_requisites(True)
            case _:
                logger.warning("Wrong update str")
    
    # On those create_* i'll call save() after

    def create_trial(self,server_id:int,enabled:bool,log_channel_id:int,notify_channel_id:int,entry_channel_id:int,guild_id:int,name:str):
        self.trial = Trial(server_id,enabled,log_channel_id,notify_channel_id,entry_channel_id,guild_id,name)
        return self.trial

    @require_cache('categories')
    async def create_category(self,name:str,allow_parallel:bool):
        temp_id = -1
        while temp_id in self.categories:
            temp_id -= 1
        self.categories[temp_id] = TrialCategory(temp_id,self.server_id,name,allow_parallel)
        return self.categories[temp_id]

    @require_cache('tasks')
    async def create_task(self,trial_category_id:int,name:str,cooldown:int,reward:str,point:int,bonus_time:int,bonus:str):
        temp_id = -1
        while temp_id in self.tasks:
            temp_id -= 1
        self.tasks[temp_id] = TrialTask(temp_id,trial_category_id,name,cooldown,reward,point,bonus_time,bonus)
        return self.tasks[temp_id]

    @require_cache('tasks')
    async def create_record(self,trial_task_id:int,smmo_id:int,user_id:int,status:bool,cancelled:bool,start_time:int,end_time:int,update_time:int,start_npc:int,start_steps:int,start_pvp:int,start_levels:int,current_npc:int,current_steps:int,current_pvp:int,current_levels:int):
        if self.records is None:
            self.records = {}
        temp_id = -1
        while temp_id in self.records:
            temp_id -= 1
        self.records[temp_id] = TrialRecord(temp_id,trial_task_id,smmo_id,user_id,status,cancelled,start_time,end_time,update_time,start_npc,start_steps,start_pvp,start_levels,current_npc,current_steps,current_pvp,current_levels)
        return self.records

    @require_cache('tasks')
    async def create_requisite(self,trial_task_id:int,formula:str,goal:int):
        if self.requisites is None:
            self.requisites = {}

        temp_id = -1
        while temp_id in self.requisites:
            temp_id -= 1
        self.requisites[temp_id] = TrialTaskRequisite(temp_id,trial_task_id,formula,goal)
        return self.requisites[temp_id]


    @require_cache('records')
    async def fetch_user_last_records(self,smmo_id:int,in_cooldown:bool=False):
        if self.last_records is None:
            self.last_records = {}

        user_records = [r for r in self.records.values() if r.smmo_id == smmo_id]
        if in_cooldown:
            ts = int(datetime.now().timestamp())
        latest_per_category = {}
        for record in user_records:
            if not record.end_time:
                continue
            task = self.tasks.get(record.trial_task_id)
            if not task:
                continue 
                                    # cooldown ended, can be started another
            if in_cooldown and record.end_time+task.cooldown<ts:
                continue
            cat_id = task.trial_category_id
            
            if cat_id not in latest_per_category:
                latest_per_category[cat_id] = record
            elif record.end_time > latest_per_category[cat_id].end_time:
                latest_per_category[cat_id] = record

        self.last_records[smmo_id] = {k: r for k,r in latest_per_category.items()}
        
        return self.last_records[smmo_id]


    @require_cache('records')
    async def fetch_user_active_records(self, smmo_id: int):
        if self.active_records is None:
            self.active_records = {}

        active_recs = [
            r for r in self.records.values() 
            if r.smmo_id == smmo_id and not r.status and not r.cancelled 
        ]
        
        self.active_records[smmo_id] = {r.id: r for r in active_recs}
        
        return self.active_records[smmo_id]
    
    @require_cache('records')
    async def fetch_active_records(self):
        active_recs = [r for r in self.records.values() if not r.status and not r.cancelled]
        return {(r.smmo_id,r.id): r for r in active_recs}
            
