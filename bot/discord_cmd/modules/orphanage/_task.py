from discord import ApplicationContext, slash_command, guild_only, option, Role, TextChannel, Forbidden
from discord.ext import commands, tasks
from pycord.multicog import subcommand

from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.api import SMMOApi,ApiError
from datetime import datetime

class OrphanageTask(commands.Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.check_orphanage.start()

    def cog_unload(self):
        self.check_orphanage.cancel()

    @tasks.loop(minutes=5.0)
    async def check_orphanage(self):
        try:
            orphanage_data = await SMMOApi.get_orphanage()
        except ApiError:
            return
        orphanage_db = await Database.select_orphanage()
        for tier_data in orphanage_data:
            tier = OrphanageTask.parse_orphanage_key_tier(tier_data.tier.key)
            for notification_config in orphanage_db:
                if notification_config.tier != int(tier):
                    continue
                if notification_config.active != 1 and tier_data.is_active:
                    await helpers.get_channel_and_edit(self.client,notification_config.channel_id,content=f"<@&{notification_config.role_id}>\nOrphanage **tier {tier}** is now active.\nExpire in <t:{int(datetime.fromisoformat(tier_data.goal_reached_at).timestamp())+7200}:R>\n{"\n".join(tier_data.effects)}", delete_after=int(datetime.fromisoformat(tier_data.goal_reached_at).timestamp())+720)
                if not await Database.update_orphanage(notification_config.channel_id,notification_config.tier,int(tier_data.is_active)):
                        logger.warning("Couldn't update orphanage status")
        
    @staticmethod
    def parse_orphanage_key_tier(tier_key: str):
        return tier_key.split('_')[-1]
    
def setup(client):
    client.add_cog(OrphanageTask(client))
