from datetime import datetime,timedelta,timezone,time
from asyncio import sleep

from discord import Bot
from discord.ext.commands import Cog
from discord.errors import Forbidden,NotFound,HTTPException
from discord.ext.tasks import loop

from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi
from bot.database.model import GuildStats

class AdminTask(Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.check_montly_reward.start()
        self.set_new_gain_lb.start()
        self.update_gains_lb.start()
        self.create_new_daily_leaderboard.start()
        self.update_leaderboards.start()
        self.reset_valut_msg.start()
        self.check_valut_code.start()
        self.activity_check.start()
        self.cleanup_msg.start()

    def cog_unload(self) -> None:
        self.check_montly_reward.cancel()
        self.set_new_gain_lb.cancel()
        self.update_gains_lb.cancel()
        self.create_new_daily_leaderboard.cancel()
        self.update_leaderboards.cancel()
        self.reset_valut_msg.cancel()
        self.check_valut_code.cancel()
        self.activity_check.cancel()
        self.cleanup_msg.cancel()

    @loop(minutes=5)
    async def cleanup_msg(self):
        msgs = await Database.select_delmsg(datetime.now().timestamp())
        for msg in msgs:
            try:
                channel = await self.client.fetch_channel(msg.chn_id)
                message = await channel.fetch_message(msg.msg_id)
                await message.delete()
                await Database.delete_delmsg(msg.msg_id,msg.chn_id)
            except NotFound:
                continue
            except HTTPException:
                continue
            except AttributeError:
                continue

        
    @loop(time=time(hour=12))
    async def set_new_gain_lb(self):
        data = await Database.select_all_gains_leaderboard()
        for d in data:
            emb = helpers.Embed(title="Loading leaderboard...")
            message = await helpers.get_channel_and_edit(self.client,d.channel_id,embed=emb)
            if not message:
                continue
            await Database.update_gains_leaderboard(d.channel_id,message.id)

    @loop(minutes=10.0)
    async def update_gains_lb(self):
        emb = await helpers.make_gains_emb()
        if not emb:
            return
        data = await Database.select_all_gains_leaderboard()
        for d in data:
            if not await helpers.get_channel_and_edit(self.client,d.channel_id,d.message_id,embed=emb):
                logger.info("Removing a gains lb cause: channel not found: %s",d.channel_id)
                await Database.delete_gains_leaderboard(d.channel_id)
            

    @loop(time=time(hour=11, minute=59))
    async def create_new_daily_leaderboard(self):
        await self.update_leaderboards(False)
        await sleep(120) # to have the date to the next day for helpers.get_current_date_game()
        data = await Database.select_all_lb()
        for d in data:
            try:
                channel = await self.client.fetch_channel(d.channel_id)
                emb = helpers.Embed(title="Loading leaderboard...\n*Now it should load 30/40min after the server reset*")
                message = await channel.send(embed=emb)
                await Database.update_lb(channel_id=channel.id,message_id=message.id,date=helpers.get_current_date_game().strftime("%d/%m/%Y"))
            except NotFound:
                continue
            except Forbidden:
                logger.info("Removing a gains lb cause: channel forbidden: %s",d.channel_id)
                await Database.delete_lb(d.channel_id)
                continue
            except HTTPException:
                logger.warning("Internet fault")
                continue

    @loop(minutes=10.0)
    async def update_leaderboards(self,skip:bool=True):
        current_date = helpers.get_current_date_game()
        if skip and datetime.now(tz=timezone.utc).hour == 12 and datetime.now(tz=timezone.utc).minute <= 30:
            return
        data = await Database.select_all_lb()
        for d in data:
            if skip and current_date.strftime("%d/%m/%Y") != d.date:
                continue
            emb = await helpers.make_members_lb(d,current_date,task=True)
            if not emb:
                logger.warning("Could not make the embed for the guild %s",d.guild_id)
                continue
            if not await helpers.get_channel_and_edit(self.client,d.channel_id,d.message_id,embed=emb):
                logger.info("Removing a member lb cause: channel not found: %s",d.channel_id)
                await Database.delete_lb(d.channel_id)

    @loop(minutes=5)
    async def check_valut_code(self):
        date = helpers.get_current_date_game()
        code = await Database.select_valut(date.year, date.month, date.day)
        if code is None:
            return
        emb: helpers.Embed = helpers.Embed(title="Daily Vault Code", description='Go to "Town > Vault" to use the code')

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

        emb.add_field(name="Code", value=f"{code.code}", inline=False)
        emb.add_field(
            name="Bonus:",
            value=f"**{bonuses}**% on BA, Steps, PVP, Quests and Professions",
            inline=False
        )
        if code.note is not None:
            emb.add_field(name="", value=code.note, inline=False)

        valutmsg = await Database.select_valutmsg()
        for v in valutmsg:
            if v.status == 1:
                continue
            await helpers.get_channel_and_edit(self.client,v.channel_id,embed=emb)
            if v.role_id is not None:
                await helpers.get_channel_and_edit(self.client,v.channel_id,content=f"<@&{v.role_id}> Here the Vault Code!")
            await Database.update_valutmsg(1, v.channel_id)

    @loop(time=time(hour=12))
    async def reset_valut_msg(self):
        valutmsg = await Database.select_valutmsg()
        for v in valutmsg:
            await Database.update_valutmsg(0, v.channel_id)

    @loop(time=time(hour=12))
    async def check_montly_reward(self):
        if datetime.now().day != 28:
            return
        pings = await Database.select_monthly_reward()
        for ping in pings:
            await helpers.get_channel_and_edit(self.client,channel_id=ping.channel_id,content=f"<@&{ping.role_id}> time to get monthly reward!\nGo to Town > Mahols Hut > Monthly Reward, to reedem it.")

    @loop(minutes=30)
    async def activity_check(self):
        print(f"[{datetime.now()}] Bot still running... Maybe...")

        
def setup(client: Bot):
    client.add_cog(AdminTask(client))