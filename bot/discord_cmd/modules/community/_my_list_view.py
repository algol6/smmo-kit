import discord
from datetime import datetime
from bot.database import Database
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger

class MyListView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.current_page: int = 0
        self.categories_names:tuple[str] = ("Weapons","Armour","Items","Pets","Amulets","Shields","Boots","Helmets","Collectables","Avatars","Materials","Sprites","Greaves","Gaunlets","Backgrounds","Specials","Tools","Potions","Event Materials","Pleb","Misc")
        self.SELLING_TEMPLATE: str = "{description}\n**Price**: {price}\nListed: <t:{timestamp}:R>"

    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        await ctx.followup.send(view=self)
        await self.update_message(self.get_current_page_data())

    async def update_message(self, data):
        await self.update_buttons()
        await self.message.edit(embed=await self.create_embed(data), view=self)
            
    async def update_buttons(self):
        if self.current_page == 0:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == len(self.data) - 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
        
        self.delete_button.disabled = len(self.data) == 0
        
    def get_current_page_data(self):
        if len(self.data) == 0:
            return None
        if self.current_page == len(self.data):
            self.current_page -= 1
        return self.data[self.current_page]

    async def create_embed(self, data):
        if data is None:
            return helpers.Embed(
                    title="No items found",
                    description="Use '/market sell' to add your item"
                )
        emb:helpers.Embed = helpers.Embed(
            title=f"{data.author_name}'s Shop"
        )
        price = f"{data.price:,}" if helpers.is_number(data.price) else data.price
        emb.add_field(
            name=data.title,
            value=self.SELLING_TEMPLATE.format(description=data.description,price=price,timestamp=data.time),
            inline=False
        )
        return emb
    

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message(self.get_current_page_data())
        
    @discord.ui.button(label="Remove Item", style=discord.ButtonStyle.red)
    async def delete_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message(content="You don't have permission to press this button.", ephemeral=True)
        await interaction.response.defer()
        item_id = self.data[self.current_page].id
        await Database.delete_market_item(item_id)
        message_notice = await Database.select_market_notice_item(item_id)
        try:
            await Database.update_delmsg(message_notice.message_id,0)
            await Database.delete_market_notice_item(item_id,message_notice.message_id)
        except AttributeError:
            logger.exception("Probably notice error:\nItem ID: %s\nMessage Notice: %s\n%s",item_id,message_noticeself.data[self.current_page])
        self.data = tuple(await Database.select_market_by_user(self.ctx.user.id))
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Close", style=discord.ButtonStyle.blurple)
    async def close_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.message.delete(delay=5)
        await interaction.followup.send("Deleting message...")
    