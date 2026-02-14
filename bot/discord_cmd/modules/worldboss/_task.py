    
from discord import ApplicationContext, slash_command,guild_only,option,TextChannel,Role,Cog
from discord.ext.tasks import loop

from pycord.multicog import subcommand

from bot.discord_cmd.helpers import permissions, command_utils, helpers,logger
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.database.model import WorldBoss
from bot.api import SMMOApi,ApiError
from datetime import datetime, time
from bot.discord_cmd.modules.worldboss._worldboss_url_button import WorldbossUrlButton
from bot.discord_cmd.modules.worldboss._worldboss_view import WorldbossView



class WorldbossTasks(Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.check_worldboss.start()
        self.update_worldboss.start()

    def cog_unload(self):
        self.check_worldboss.cancel()
        self.update_worldboss.cancel()


    @loop(time=time(hour=12,minute=5))
    async def update_worldboss(self):
        if datetime.today().weekday() != 0:
            return
        await Database.delete_all_worldboss()
        wb_data = await SMMOApi.get_world_bosses()
        for wb in wb_data:
            if not await Database.insert_worldboss(wb.id,wb.name,wb.avatar,wb.level,int(wb.god),wb.strength,wb.defence,wb.dexterity,wb.current_hp,wb.max_hp,wb.enable_time):
                logger.warning("Error while saving worldboss:%s",wb)
            
    @loop(seconds=1)
    async def check_worldboss(self):
        is_empty,worldboss_data = helpers.gen_is_empty(await Database.select_worldboss(int(datetime.now().timestamp()-10)))
        if is_empty:
            return
        wb = next(worldboss_data)
        await self.notify_wb(wb)
        await self.update_message(wb)


    async def update_message(self, wb_data:WorldBoss):
        data = await Database.select_wb_message()
        emb = helpers.Embed(title=wb_data.name,url="https://simple-mmo.com/worldboss/all",thumbnail=f"https://simple-mmo.com/img/sprites/{wb_data.avatar}.png")
        emb.add_field(name="Level", value=wb_data.level, inline=False)
        emb.add_field(name="HP", value=f"{wb_data.current_hp:,} :heart:", inline=False)
        emb.add_field(name="God", value=f"{":white_check_mark:" if bool(wb_data.god) else ":x:"}", inline=False)
        emb.add_field(name="Strength", value=f"{wb_data.strength:,} :crossed_swords:", inline=True)
        emb.add_field(name="Defence", value=f"{wb_data.defence:,} :shield:", inline=True)
        emb.add_field(name="Dexterity", value=f"{wb_data.dexterity:,} :boot:", inline=True)
        emb.add_field(name="Active", value=f"<t:{wb_data.enable_time}:R> (<t:{wb_data.enable_time}>)", inline=False)
    
        for d in data:
            if d.boss_id == wb_data.id:
                continue
            if not await helpers.get_channel_and_edit(self.client,d.channel_id,embed=emb,delete_after=int(wb_data.enable_time - datetime.now().timestamp() + 120), view=WorldbossUrlButton()):
                logger.warning("Could not update wb message for: %s",d)
            await Database.update_wb_message(d.channel_id,wb_data.id)
            

    async def notify_wb(self, wb:WorldBoss):
        data = sorted(await Database.select_wb_notification(), key=lambda boss: boss.seconds_before)
        for d in data:
            if d.boss_id == wb.id:
                continue
            if wb.enable_time <= datetime.now().timestamp() + d.seconds_before:
                await Database.update_wb_notification(d.channel_id, wb.id,d.seconds_before)
                if d.god == 1 and not wb.god:
                    continue
                await helpers.get_channel_and_edit(self.client,d.channel_id,content=f"<@&{d.role_id}> world boss **{wb.name}** in about <t:{wb.enable_time}:R>", delete_after=(wb.enable_time - datetime.now().timestamp() + 60))
              
