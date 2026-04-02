import discord
from bot.database import Database
from bot.discord_cmd.helpers import helpers 
from bot.discord_cmd.helpers.logger import logger

class ConfirmButton(discord.ui.View):
    SELLING_TEMPLATE: str = "{description}\n**Price**: {price}\n[DM User In Game](https://web.simple-mmo.com/chat/private?user_id={smmo_id})\nListed: <t:{timestamp}:R>"

    async def send(self, ctx: discord.ApplicationContext):
        self.emb = helpers.Embed(title="Do you want to get the old Items?", 
            description="If you confirm the bot will send the items already in the database otherwise you will get only the one that will be added.")
        await ctx.followup.send(embed=self.emb, view=self)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.edit_message(embed=helpers.Embed(title="Sending Messages"),view=self)
        await self.message.delete(delay=10)
        await self.send_past_market_items()
        
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancell_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.edit_message(embed=helpers.Embed(title="Operation cancelled"),view=self)
        await self.message.delete(delay=10)

    async def send_past_market_items(self):
        items = await Database.select_all_market()
        for item in items:
            emb:helpers.Embed = helpers.Embed(
                title=f"{item.author_name} is selling!",
                url=f"https://simple-mmo.com/user/view/{item.author_smmo_id}"
            )
            price = f"{int(item.price):,}" if helpers.is_number(item.price) else item.price
            emb.add_field(
                name=item.title,
                value=self.SELLING_TEMPLATE.format(description=item.description,price=price,smmo_id=item.author_smmo_id,timestamp=item.time),
                inline=False
            )
            try:
                msg = await self.channel.send(embed=emb)
                await Database.insert_market_notice_item(item.id,msg.id,item.time)
                await Database.insert_delmsg(msg.id,self.channel.id,item.time+604800)
            except:
                logger.exception("While sending past market items on a new set channel")