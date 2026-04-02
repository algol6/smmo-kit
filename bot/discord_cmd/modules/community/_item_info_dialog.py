import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import Database
from bot.discord_cmd.modules.event._preview_registration_view import PreviewRegistrationView
from datetime import datetime,timezone

class ItemModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(label="Title",placeholder="The name of the item or service you are selling"))
        self.add_item(discord.ui.InputText(label="Description (optional)",placeholder="Description of what you want to sell", required=False,style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="Price",placeholder="What payament you want for it"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        title = self.children[0].value
        desc = self.children[1].value if self.children[1] else ""
        price = self.children[2].value
        cat_id = ("Weapons","Armour","Items","Pets","Amulets","Shields","Boots","Helmets","Collectables","Avatars","Materials","Sprites","Greaves","Gaunlets","Backgrounds","Specials","Tools","Potions","Event Materials","Pleb","Misc").index(self.category)
        if not await Database.insert_market_item(title,desc,cat_id,price,self.author_id,self.author_smmo_id,self.author_name,self.time):
            return await interaction.followup.send("Error while adding item")
        await interaction.followup.send("Item Added, the item will be automatically removed after 7 days to keep the list clean.")

        item = await Database.select_market_by_author_timestamp(self.author_id,self.time)
        if item is not None:
            await self.update_market_items(item)

    async def update_market_items(self,item):
        cat = ("Weapons","Armour","Items","Pets","Amulets","Shields","Boots","Helmets","Collectables","Avatars","Materials","Sprites","Greaves","Gaunlets","Backgrounds","Specials","Tools","Potions","Event Materials","Pleb","Misc")
        SELLING_TEMPLATE: str = "{description}\n**Price**: {price}\n[DM User In Game](https://web.simple-mmo.com/chat/private?user_id={smmo_id})\nListed: <t:{timestamp}:R>"
        emb:helpers.Embed = helpers.Embed(
            title=f"{item.author_name} is selling!",
            url=f"https://simple-mmo.com/user/view/{item.author_smmo_id}"
        )
        price = f"{int(item.price):,}" if helpers.is_number(item.price) else item.price
        emb.add_field(
            name=item.title,
            value=SELLING_TEMPLATE.format(description=item.description,price=price,smmo_id=item.author_smmo_id,timestamp=item.time),
            inline=False
        )
        channels = await Database.select_all_market_notice()
        for ch in channels:
            try:
                channel = await self.client.fetch_channel(ch.channel_id)
                msg = await channel.send(embed=emb)
                await Database.insert_market_notice_item(item.id,msg.id,item.time)
                await Database.insert_delmsg(msg.id,channel.id,item.time+604800)
            except:
                logger.exception("While sending past market items on a new set channel")
