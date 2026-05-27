from discord import Bot
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from datetime import datetime,timezone,timedelta,time
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.helpers import helpers

from bot.api import SMMOApi
from bot.database import Database,TrialDatabase
from bot.database.model._trial import TrialRecord
from bot.core._trial import TrialManager
from bot.core._guild_members import GuildMembersManager
from bot.discord_cmd.modules.trial._helper import send_log,LogType

class TrialTask(Cog):
    def __init__(self, client):
        self.client = client
        self.check_stats.start()
        #import asyncio
        #asyncio.run(self.check_stats())

    def cog_unload(self):
        self.check_stats.cancel()

    @loop(minutes=10)
    async def check_stats(self):
        trials_id = await TrialDatabase.select_all_trial_enabled_ids()
        ts = int(datetime.now().timestamp())
        for id in trials_id:
            trial_mng = TrialManager(id)
            await trial_mng.fetch_trial()
            await trial_mng.fetch_records()
            await trial_mng.fetch_requisites()
            active_records = await trial_mng.fetch_active_records()
            gm_mgr = GuildMembersManager(trial_mng.trial.guild_id)
            await gm_mgr.fetch_members()
            if not gm_mgr.members:
                continue
            for ids,record in active_records.items():
                smmo_id = ids[0]
                rid = ids[1]
                user = gm_mgr.members.get(smmo_id)
                task = trial_mng.tasks[record.trial_task_id]
                if not user:
                    record.cancelled = True
                    await send_log(self.client,trial_mng.trial.server_id,LogType.TASK_CANCELLED,
                        value=f"{trial_mng.categories[task.trial_category_id].name.title()} > {task.name.title()}",
                        usr1=record.user_id,
                        extra_post=f"\n**Reason**: Not found in the guild list."
                    )
                    await trial_mng.update("record",record,False)
                    continue
                requisites = trial_mng.get_requisite_for_task(task.id)
                values = []
                for req in requisites.values():
                    if req.formula == "LVL":
                        values.append((user.level-record.start_levels,req.goal))
                    else:
                        values.append(
                            (
                                helpers.evaluate_formula(
                                    req.formula,
                                    user.steps-record.start_steps,
                                    user.npc_kills-record.start_npc,
                                    user.user_kills-record.start_pvp
                                ),
                                req.goal
                            )
                        )
                if all(x1>=x2 for x1,x2 in values):
                    et = ts
                    duser = await self.client.fetch_user(int(record.user_id))
                    if trial_mng.trial.notify_channel_id is not None:
                        emb = helpers.Embed(title=f"{helpers.make_title(trial_mng.trial.name)} complete!")
                        emb.add_field(
                            name=f"{trial_mng.categories[task.trial_category_id].name.title()} > {task.name.title()} has been completed.",
                            value=(
                                f"{duser.display_name} (<@{int(record.user_id)}>) Has completed a {helpers.make_title(trial_mng.trial.name)}\n"
                                f"\n**Bonus**: {":white_check_mark:" if record.start_time + task.bonus_time >= et else ":x:"}\n"
                                f"\n**Cooldown**: {helpers.formattime(task.cooldown/60)}, <t:{int(et+task.cooldown)}:R> (<t:{int(et+task.cooldown)}>)"
                            )
                        )
                        msg = await helpers.get_channel_and_edit(self.client,channel_id=trial_mng.trial.notify_channel_id,content=f"<@{int(record.user_id)}>",embed=emb)
                        if msg and not isinstance(msg,bool):
                            await helpers.get_channel_and_edit(self.client,msg.channel.id,msg.id,embed=emb)
                    
                    await send_log(self.client,trial_mng.trial.server_id,LogType.TASK_COMPLETED,
                        value=f"{trial_mng.categories[task.trial_category_id].name.title()} > {task.name.title()}",
                        usr1=int(record.user_id),
                        extra_post=(
                            f"\n**Bonus**: {":white_check_mark:" if record.start_time + task.bonus_time >= et else ":x:"}"
                            f"\n**Cooldown**: {helpers.formattime(task.cooldown/60)}, <t:{int(et+task.cooldown)}:R> (<t:{int(et+task.cooldown)}>)"
                            )
                    )
                else:
                    et = None
                trial_mng.records[rid].current_npc = user.npc_kills
                trial_mng.records[rid].current_steps = user.steps
                trial_mng.records[rid].current_pvp = user.user_kills
                trial_mng.records[rid].current_levels = user.level
                trial_mng.records[rid].update_time = ts
                trial_mng.records[rid].end_time = et
                trial_mng.records[rid].status = et!=None
                await trial_mng.update("record",trial_mng.records[rid],False)        
    
def setup(client:Bot):
    client.add_cog(UsersTask(client))
