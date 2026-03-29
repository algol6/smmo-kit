from discord.ext import commands, tasks

from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi,ApiError
from datetime import datetime, time

class OrphanageTask(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.check_orphanage.start()
        self.toggle_orph.start()

    def cog_unload(self):
        self.check_orphanage.cancel()
        self.toggle_orph.cancel()

    @tasks.loop(time=time(hour=12, minute=30))
    async def toggle_orph(self):
        self.check_orphanage.start()

    @tasks.loop(minutes=5.0)
    async def check_orphanage(self):
        try:
            orphanage_data = tuple(await SMMOApi.get_orphanage())
        except ApiError:
            return
        if orphanage_data[2].has_expired:
            self.check_orphanage.stop()
        
        orphanage_db = await Database.select_orphanage()
        emb = None
        channels_id = set()
        TEMPLATES:str = ["[{bar}] {percentage}%\nGold :coin::\n> {x:,}/{y:,}\nStatus :repeat::\n> {status}\n",
                         "Bonuses :top::\n> {bonuses}\nActived since :clock4::\n> {actived_time}\nExpiring in :clock6::\n> {expiring_time1} {expiring_time2}"]
        BAR_LENGHT:int=15
        progression:bool = True
        for tier_data in orphanage_data:
            tier = OrphanageTask.parse_orphanage_key_tier(tier_data.tier.key)
            for notification_config in orphanage_db:
                if emb is None:
                    emb = helpers.Embed(title=f"Orphanage Status",
                                url="https://simple-mmo.com/orphanage",
                                thumbnail="https://simple-mmo.com/img/icons/orphanage.png",
                                color= 0xffd700)
                    for i in range(3):
                        if not progression:
                            continue
                        if not(orphanage_data[i].is_active or orphanage_data[i].has_expired):
                            progression = False
                        ntemp = int((orphanage_data[i].current_value / orphanage_data[i].target_value)*BAR_LENGHT)
                        temp = ntemp * ":small_orange_diamond:"
                        temp_status = "Active :white_check_mark:" if orphanage_data[i].is_active else "Inactive :x:"
                        temp_status = "Expired :zzz:" if orphanage_data[i].has_expired else temp_status
                        emb.add_field(name=f"Tier {i+1}",
                                    value=TEMPLATES[0].format(
                                        bar=f"{temp}{(BAR_LENGHT - ntemp) * ":small_blue_diamond:"}",
                                        percentage=orphanage_data[i].percentage,
                                        x=orphanage_data[i].current_value,
                                        y=orphanage_data[i].target_value,status=temp_status) + 
                                            (
                                                TEMPLATES[1].format(
                                                    bonuses="\n> ".join(orphanage_data[i].effects),
                                                    actived_time=f"<t:{int(datetime.fromisoformat(orphanage_data[i].goal_reached_at).timestamp())}:R>",
                                                    expiring_time1=f"<t:{int(datetime.fromisoformat(orphanage_data[i].goal_reached_at).timestamp() + 7200)}:R>",
                                                    expiring_time2=f"(<t:{int(datetime.fromisoformat(orphanage_data[i].goal_reached_at).timestamp() + 7200)}>)"
                                                ) if orphanage_data[i].is_active else ""
                                            ),
                                        inline=False)
                    emb.set_footer(text=f"Updated every 5 minutes")
                if notification_config.channel_id not in channels_id:
                    channels_id.add(notification_config.channel_id)
                    if notification_config.message_id is None:
                        msg = await helpers.get_channel_and_edit(self.client,notification_config.channel_id,embed=emb)
                        if not isinstance(msg, bool):
                            await Database.update_orphanage_msg_id(notification_config.channel_id,notification_config.tier,msg.id)
                        elif not msg:
                            logger.info("Removing a orphanage cause: channel not found or forbidden: %s",notification_config.channel_id)
                            await Database.delete_orphanage(notification_config.channel_id)
                            
                    else:
                        msg = await helpers.get_channel_and_edit(self.client,
                                                                channel_id=notification_config.channel_id,
                                                                message_id=notification_config.message_id,
                                                                embed=emb)
                if notification_config.tier != int(tier):
                    continue
                if notification_config.active != 1 and tier_data.is_active:
                    await helpers.get_channel_and_edit(self.client,
                                                        notification_config.channel_id,
                                                        content=f"<@&{notification_config.role_id}>\nOrphanage **tier {tier}** is now active.",
                                                        delete_after=int(datetime.fromisoformat(tier_data.goal_reached_at).timestamp() + 7200)-datetime.now().timestamp())
                if not await Database.update_orphanage_active(notification_config.channel_id,notification_config.tier,int(tier_data.is_active)):
                    logger.warning("Couldn't update orphanage status")
        
    @staticmethod
    def parse_orphanage_key_tier(tier_key: str):
        return tier_key.split('_')[-1]
    
def setup(client):
    client.add_cog(OrphanageTask(client))
