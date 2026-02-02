from discord import Bot,NotFound
from discord.ext.tasks import loop
from discord.ext.commands import Cog

from bot.api import SMMOApi,ApiError
from bot.database import Database
from bot.discord_cmd.modules.diamond._market_url_button import MarketUrlButton
from bot.discord_cmd.helpers import permissions, command_utils, helpers
from bot.discord_cmd.helpers.logger import logger

from asyncio import sleep
from datetime import datetime,time
class DiamondsTasks(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.update_market.start()
        self.pause_market_reset.start()

    def cog_unload(self) -> None:
        self.update_market.cancel()
        self.pause_market_reset.cancel()

    @loop(time=time(hour=11,minute=59))
    async def pause_market_reset(self):
        self.update_market.stop()
        await sleep(600)
        self.update_market.start()

    @loop(seconds=5)
    async def update_market(self):
        try:
            is_empty,market_data = helpers.gen_is_empty(await SMMOApi.get_diamond_market())
        except ApiError:
            return
        if is_empty:
            return
        market_data = sorted([*market_data],key=lambda x: x.price_per_diamond)
        await self.notify_prices(market_data[0])

    async def notify_prices(self, market_data):
        for dias in await Database.select_diamonds():
            if market_data.price_per_diamond > dias.min_price:
                continue

            if dias.last_min_price != '' and datetime.fromisoformat(market_data.listing_created) <= datetime.fromisoformat(dias.last_min_price):
                continue
            await Database.update_diamonds(market_data.listing_created, dias.channel_id)

            await helpers.get_channel_and_send(self.client,dias.channel_id,
                                               content= f"<@&{dias.role_id}> {market_data.seller.name} "
                                                        f"is selling {market_data.diamond_amount_at_start} diamonds "
                                                        f"for {market_data.price_per_diamond:,} :coin: [{int(market_data.price_per_diamond*1.025):,} :bank:] gold each.\n"
                                                        f"Total price: {(market_data.price_per_diamond*market_data.diamond_amount_at_start):,} :coin: [{int((market_data.price_per_diamond*market_data.diamond_amount_at_start)*1.025):,} :bank:]",
                                                view=MarketUrlButton())
            

def setup(client:Bot):
    client.add_cog(DiamondsTasks(client))
