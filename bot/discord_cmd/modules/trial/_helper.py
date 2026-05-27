from discord import Bot
from bot.discord_cmd.helpers import helpers
from bot.database import TrialDatabase
from enum import Enum
from bot.database.model._stats import UserStat
from bot.api.model._player_info import PlayerInfo
from bot.database.model._trial import TrialRecord
from bot.core._trial import TrialManager
from re import finditer

def parse_duration_to_seconds(time_str: str) -> int:
    if not time_str:
        return 0
    seconds = 0
    matches = finditer(r'(\d+)\s*([wdhms])', time_str.lower())
    multipliers = {
        'w': 604800,
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }
    for match in matches:
        amount = int(match.group(1))
        unit = match.group(2)
        seconds += amount * multipliers[unit]
    return seconds

class LogType(Enum):
    TRIAL_CREATION = ("The '{value}' has been created.\nBy User: <@{user1}> ( {display_name} )","System Creation",0x00b300)
    TRIAL_DELETION = ("The '{value}' has been deleted.\nBy User: <@{user1}> ( {display_name} )","System Deleted",0xb30000)
    TRIAL_UPDATE = ("The '{value}' has been updated.\nBy User: <@{user1}> ( {display_name} )","System Updated",0x005ab3)
    TRIAL_TOGGLE = ("The system has been updated to '{value}'.\nBy User: <@{user1}> ( {display_name} )","System Enabled/Disabled",0xffa500)
    CATEGORY_CREATION = ("The '{value}' has been added.\nBy User: <@{user1}> ( {display_name} )","Category Added",0x00b300)
    CATEGORY_DELETION = ("The '{value}' has been removed.\nBy User: <@{user1}> ( {display_name} )","Category Deleted",0xb30000)
    CATEGORY_UPDATE = ("The '{value}' has been updated.\nBy User: <@{user1}> ( {display_name} )","Category Update",0x005ab3)
    TASK_CREATION = ("The '{value}' has been added.\nBy User: <@{user1}> ( {display_name} )","Task Created",0x00b300)
    TASK_DELETION = ("The '{value}' has been removed.\nBy User: <@{user1}> ( {display_name} )","Task Deleted",0xb30000)
    TASK_UPDATE = ("The '{value}' has been updated.\nBy User: <@{user1}> ( {display_name} )","Task Updated",0x005ab3)
    TASK_ACCEPTED = ("<@{user1}> ( {display_name} ) has accepted '{value}'.","Task Accepted",0xe6e600)
    TASK_COMPLETED = ("<@{user1}> ( {display_name} ) has completed '{value}'.","Task Completed",0x00ff00)
    TASK_CANCELLED = ("<@{user1}> ( {display_name} ) has cancelled '{value}'.","Task Cancelled",0x565656)
    TASK_POINT_CHANGED = ("<@{user1}> ( {display_name1} ) has changed the point of '<@{user2}> ( {display_name2} ) by {value}'.","User Points Changed",0x005ab3)

    def __new__(cls, msg, title, color):
        obj = object.__new__(cls)
        obj._value_ = title
        obj.msg:str = msg
        obj.color = color
        return obj
    
async def send_log(client:Bot,server_id:int,log_type:LogType,value:str,usr1:int,usr2:int=None,channel_id:int=None,extra_pre:str="",extra_post:str=""):
    emb = helpers.Embed(
        title=log_type.value,
        color=log_type.color
    )
    user1 = await client.fetch_user(usr1)
    if usr2 is not None:
        user2 = await client.fetch_user(usr2)
        msg = log_type.msg.format(value=value,user1=usr1,user2=usr2,display_name1=user1.display_name,display_name2=user2.display_name)
    elif channel_id is not None:
        msg = log_type.msg.format(value=value,user1=usr1,display_name=user1.display_name,channel_id=channel_id)
    else:
        msg = log_type.msg.format(value=value,user1=usr1,display_name=user1.display_name)

    emb.add_field(
        name="Log Info:",
        value=extra_pre+msg+extra_post
    )
    channel_id = await TrialDatabase.select_trial_log_channel(server_id)
    if channel_id is None:
        return
    await helpers.get_channel_and_edit(client,channel_id=channel_id,embed=emb)


async def generate_status_emb(records,user:PlayerInfo,system_name:str,show_cooldown:bool=False) -> helpers.Embed:
    emb = helpers.Embed(
        title=f"{user.name}'s Status",
        url=f"https://simple-mmo.com/user/view/{user.id}",
        thumbnail=f"https://simple-mmo.com{user.avatar}",
    )
    check = True
    for record in records.values():
        msg = ""
        task = await TrialDatabase.select_trial_task_by_id(record.trial_task_id) 
        category = await TrialDatabase.select_trial_category(task.trial_category_id)
        requisites = await TrialDatabase.select_trial_task_requisite(task.id)
        msg = ""
        for req in requisites:
            if "LVL" == req.formula.upper():
                val = record.current_levels - record.start_levels
            else:
                val = helpers.evaluate_formula(
                    req.formula,
                    record.current_steps-record.start_steps,
                    record.current_npc-record.start_npc,
                    record.current_pvp-record.start_pvp
                )
            msg += f"`{req.formula.upper()}`: {val:,}/{req.goal:,} [{min((100*val)/req.goal,100):.2f}%]\n"
        if show_cooldown and record is not None and record.end_time is not None:
            msg += f"Cooldown: New {system_name} <t:{record.end_time+task.cooldown}:R>\n"
        msg += f"\nUpdated <t:{int(record.update_time)}:R>:\n _Updated every 10 minutes_"
        emb.add_field(
            name=f"{category.name.title()}: {task.name.title()}{" :green_circle:" if record.status else " :orange_circle:"}",
            value=msg,
            inline=False
        )
        check = False
    if check:
        emb.add_field(name="",value="No record found")
    return emb

async def generate_info_emb(trial_id:int):
    tm = TrialManager(trial_id)
    await tm.fetch_categories()
    if not tm.categories:
        emb = helpers.Embed(title=f"{helpers.make_title(tm.trial.name)}")
        emb.add_field(name="",value="No categories or tasks set.")
        return emb
    
    emb = helpers.Embed(
        title=f"{helpers.make_title(tm.trial.name)}",
        description=""
    )
    await tm.fetch_tasks()
    await tm.fetch_requisites()
    for category in tm.categories.values():
        print(category)
        msg = ""
        for task in tm.get_tasks_for_category(category.id).values():
            print(task)
            msg += f"**{task.name.title()}** | {helpers.formattime(task.cooldown/60)} :stopwatch: | {task.reward}:\n"
            requisites = tm.get_requisite_for_task(task.id)
            values = []
            for requisite in requisites.values():
                msg += f"> `{requisite.formula.upper()}` : {requisite.goal:,}\n"
            if task.bonus:
                msg += f"Bonus: {task.bonus} if completed in {helpers.formattime(task.bonus_time/60)}\n"
            msg += "\n"
        if msg == "":
            emb.add_field(
                name=category.name.title(),
                value="No Tasks for this category."
            )
            continue
        emb.add_field(
            name=f"==={category.name.title()}===",
            value=msg,
            inline=False
        )
    emb.set_footer(text="Name | Cooldown | Reward")
    return emb