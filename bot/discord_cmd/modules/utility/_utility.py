from discord import ApplicationContext, slash_command, guild_only,option
from discord.ext import commands
from pycord.multicog import subcommand

from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.helpers import command_utils, permissions,helpers
from bot.discord_cmd.helpers.logger import logger

from time import strftime, gmtime
from math import ceil
from re import findall

class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @slash_command(description="Show vault code")
    @guild_only()
    @command_utils.auto_defer()
    @command_utils.statistics("/vault")
    @command_utils.took_too_long()
    async def vault(self,ctx:ApplicationContext) -> None:
        date = helpers.get_current_date_game()
        code = await Database.select_valut(date.year,date.month,date.day)
        if code is None:
            return await helpers.send(ctx,content="No code added for today, try again later")
        emb = helpers.Embed(title="Daily Vault Code",description='Go to "Town>Vault" to use the code')
        
        match len(str(code.code)):
            case 9:
                bonuses = 15
            case 10:
                bonuses = 20
            case 11:
                bonuses = 25
            case 12:
                bonuses = 40
            case _:
                bonuses = 10

        emb.add_field(name="Code",
                      value=f"{code.code}",
                      inline=False)
        emb.add_field(name="Bonus:",
                      value=f"**{bonuses}**% on BA, Steps, PVP, Quests and Professions",
                      inline=False
                      )
        if code.note is not None:
            emb.add_field(name="",value=code.note,inline=False)

        await helpers.send(ctx,embed=emb)

    @slash_command(description="Calculate the ba needed to reach x level")
    @guild_only()
    @option(name="rank", choices=["Copper","Bronze","Silver","Gold","Platinum","Titanium","7th Circle","Ragnarok","Mount Olympus","Rapture","Nirvana"])
    @option(name="npc",description="If used this parameter ignore the target_level and show how many levels you gain by killing x npc")
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/bacalc")
    @command_utils.took_too_long()
    async def bacalc(self, ctx:ApplicationContext, rank:str, target_level:int = None, boost_percentage:int = 0, starting_level:int=None, energy_point:int=None,npc:int=None) -> None:
        if target_level is None and npc is None:
            return await helpers.send(ctx,content="Insert a target level (target_level) or the amount of npc to kill (npc)")
        mult: float = 0.0
        cost: int = 0
        color = 0x000000
        icon = ""
        rank_data = {
                        "Copper": {"mult": 2.0, "cost": 1000, "color": 0xf8922f, "icon": "https://simple-mmo.com/img/icons/battlearena/1.png"},
                        "Bronze": {"mult": 2.2, "cost": 2500, "color": 0xe39f62, "icon": "https://simple-mmo.com/img/icons/battlearena/2.png"},
                        "Silver": {"mult": 2.4, "cost": 6000, "color": 0x9fa6b4, "icon": "https://simple-mmo.com/img/icons/battlearena/3.png"},
                        "Gold": {"mult": 2.6, "cost": 9375, "color": 0xe6c53a, "icon": "https://simple-mmo.com/img/icons/battlearena/4.png"},
                        "Platinum": {"mult": 3.0, "cost": 11250, "color": 0xa8aade, "icon": "https://simple-mmo.com/img/icons/battlearena/5.png"},
                        "Titanium": {"mult": 3.5, "cost": 13750, "color": 0xdf7676, "icon": "https://simple-mmo.com/img/icons/battlearena/6.png"},
                        "7th Circle": {"mult": 4.0, "cost": 16250, "color": 0xec1b04, "icon": "https://simple-mmo.com/img/icons/S_Fire08.png"},
                        "Ragnarok": {"mult": 4.5, "cost": 18750, "color": 0x6d0b52, "icon": "https://simple-mmo.com/img/icons/two/32px/RuneStone17_32.png"},
                        "Mount Olympus": {"mult": 5.0, "cost": 21250, "color": 0x9c5048, "icon": "https://simple-mmo.com/img/icons/S_Earth07.png"},
                        "Rapture": {"mult": 5.5, "cost": 27000, "color": 0xac6d28, "icon": "https://simple-mmo.com/img/icons/one/icon174.png"},
                        "Nirvana": {"mult": 6.0, "cost": 34500, "color": 0xfafaee, "icon": "https://simple-mmo.com/img/icons/one/icon130.png"}
                    }

        if rank in rank_data:
            mult = rank_data[rank]["mult"]
            cost = rank_data[rank]["cost"]
            color = rank_data[rank]["color"]
            icon = rank_data[rank]["icon"]

        player = await helpers.get_user(ctx)
        if player is None:
            return
            
        player.level = player.level if starting_level is None else starting_level

        if npc is None and player.level >= target_level:
            return await helpers.send(ctx,"The level that you want reach has to be higher than your actual level. -_-")
            
        xp = player.exp if starting_level is None else 0

        xp_needed  = xp - ((50 * (player.level * (player.level+1))//2) if starting_level is None else 0)

        money_needed:int = 0
        npc_to_kill:int = 0
        current_level = player.level
        xp_multiplier = 3.25 * mult * (1.0 + boost_percentage / 100)

        if npc is not None:
            npc_to_kill = npc
            for _ in range(1, npc + 1):
                xp_needed += xp_multiplier * current_level
                if xp_needed >= 0:
                    xp_needed -= current_level * 50
                    current_level += 1
                money_needed += cost
        else:
            while current_level < target_level:
                xp_needed += xp_multiplier * current_level
                if xp_needed >= 0:
                    xp_needed -= current_level * 50
                    current_level += 1
                npc_to_kill += 1
                money_needed += cost


        regen_time: str = helpers.formattime(npc_to_kill*5)
        split_time = findall(r'\d+[a-zA-Z]', regen_time)
        m110 = 0
        for i in split_time:
            if "w" in i:
                m110 += 7 * int(i.split("w")[0])
            if "d" in i:
                m110 += int(i.split("d")[0])
        m150 = 180 * (m110 if npc_to_kill > 180 else 0)
        m110 = 125 * (m110 if npc_to_kill > 125 else 0)
        
        emb = helpers.Embed(title="Battle arena calculator",
                            description=f"**Level**: {player.level:,} -> {target_level if npc is None else current_level:,}\n**Rank**: {rank}\n**Boost**: {boost_percentage}%\n",
                            color=color,
                            thumbnail=icon)
        msg:str = (f"**NPC generated**: {npc_to_kill:,} :skull:\n"
                    f"**Cost**: {money_needed:,} :coin: [{int(money_needed*1.035):,} :bank:]\n"
                    f"**Natural regen time**: {regen_time} :alarm_clock:\n"
                    f"**Regen time w/ 125** :mushroom:: {helpers.formattime((max(0,npc_to_kill-m110))*5)} (Moe cost: {(m110)*30000:,} :coin: | {m110:,} :mushroom:)\n"
                    f"**Regen time w/ 180** :mushroom:: {helpers.formattime((max(0,npc_to_kill-m150))*5)} (Moe cost: {(m150)*30000:,} :coin: | {m150:,} :mushroom:)\n"
                    )
        msg2:str = ""
        STR_TEMPLATE = ["With {ep} Ep, it's worth to refill {refill_ep} EP instead\n",
                        "With {ep} Ep, if There is a sale it's worth to refill {refill_ep} EP instead\n",
                        "With {ep} Ep, if There is a double sale it's worth to refill {refill_ep} EP instead\n"]
        if energy_point is not None:
            diamon_needed = [0, 0, 0]
            refills = ceil(npc_to_kill / energy_point)
            
            thresholds = [
                # max energy, cost (no sale, sale and double), min energy to be worth a refill, prev max energy
                (10, [5, 4, 3],None,None),
                (25, [8, 7, 6],[16,18,20],10),
                (50, [10, 9, 8],[32,33,34],25),
                (100, [13, 11, 10],[65,62,63],50),
                (200, [15, 13, 12],[116,119,120],100),
                (500, [18, 15, 14],[240,231,234],200),
                (750, [24, 22, 21],[667,734,750],500),
                (1000, [29, 26, 24],[907,887,858],750),
                (float('inf'), [35, 31, 29],[1207,1193,1209],1000)
            ]
            for threshold, diamon_values, diamon_value,refill_ep in thresholds:
                if energy_point <= threshold:
                    diamon_needed = [refills * value for value in diamon_values]
                    if diamon_values:
                        if energy_point < diamon_value[0]:
                            msg2 += STR_TEMPLATE[0].format(ep=energy_point, refill_ep=refill_ep)
                        if energy_point < diamon_value[1]:
                            msg2 += STR_TEMPLATE[1].format(ep=energy_point, refill_ep=refill_ep)
                        if energy_point < diamon_value[2]:
                            msg2 += STR_TEMPLATE[2].format(ep=energy_point, refill_ep=refill_ep)
                    break
            if len(msg2) != 0:
                msg2 = f"**Tips**:\n{msg2}"
            msg += f"**Refills ({energy_point:,} ep)** :repeat:: {refills:,} refills\n"
            msg += f"**Refills Cost** (No sales): {diamon_needed[0]:,} :gem:\n"
            msg += f"**Refills Cost** (Sale): {diamon_needed[1]:,} :gem:\n"
            msg += f"**Refills Cost** (Double sale): {diamon_needed[2]:,} :gem:\n"
        emb.add_field(name="",
                      value=msg+msg2)
        await helpers.send(ctx,embed=emb)

    @slash_command(description="Calculate the xp, crafting and common mats needed to reach x crafting lvl")
    @guild_only()
    @option(name="lvl_to_reach", min_value=1)
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/crafting")
    @command_utils.took_too_long()
    async def crafting(self, ctx:ApplicationContext, lvl_to_reach:int) -> None:
        user = await Database.select_user_discord(ctx.user.id)
        profile = await SMMOApi.get_player_skills(user.smmo_id)
        current_lvl:int = 1
        current_lvl_xp:int = 0
        for s in profile:
            if s.skill == "forging":
                current_lvl = int(s.level)
                current_lvl_xp = int(s.exp)
                break

        if current_lvl >= lvl_to_reach:
            return await helpers.send(ctx,content=f"Your current level is higher than the level you are tring to reach. Your level: {current_lvl}")
        
        max_xp:int = 50 * ((lvl_to_reach - 1) * lvl_to_reach) // 2
        xp_needed:int = max_xp - current_lvl_xp

        embed = helpers.Embed(
            title=f"Crafting from lvl {current_lvl} to {lvl_to_reach}",
            description=f"**XP needed to reach lvl {lvl_to_reach}**: {xp_needed:,}")

        rarity = {"Common": (15,15),
                       "Uncommon":(20,20),
                       "Rare":(25,20),
                       "Elite":(40,25),
                       "Epic":(45,30),
                       "Legendary":(55,25),
                       "Celestial":(70,35)
                       }
        
        for name,values in rarity.items():
            craft_needed:int = ceil(xp_needed/values[0])
            embed.add_field(name=f"{name} mats",
                            value=f"Items to craft: {craft_needed:,}\n"
                                  f"Mats needed: {craft_needed*values[1]:,}\n",
                            inline=False)

        await helpers.send(ctx,embed=embed)

def setup(client):
    client.add_cog(Utility(client))