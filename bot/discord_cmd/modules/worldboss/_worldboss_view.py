import discord
from datetime import datetime
from bot.discord_cmd.helpers import helpers 

class WorldbossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    current_page: int = 0

    async def on_timeout(self):
        self.disable_all_items()
        self.remove_item(self.children)
        self.prev_button.style = discord.ButtonStyle.gray
        self.next_button.style = discord.ButtonStyle.gray


    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        for i,boss in enumerate(self.data):
            if boss.enable_time > datetime.now().timestamp():
                self.current_page = i
                break
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.current_page])


    async def update_message(self, data):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(data), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")

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

    async def create_embed(self, data):
        
        emb = helpers.Embed(title=data.name,
                                    url="https://simple-mmo.com/worldboss/all",
                                    thumbnail=f"https://simple-mmo.com/img/sprites/{data.avatar}.png",
                                    color= 0xc0392b if bool(data.god) else 0x34495e)
        emb.add_field(name="Level", value=data.level, inline=False)
        emb.add_field(name="HP", value=f"{f'{format(data.current_hp,",d")} :heart:' if data.enable_time > datetime.now().timestamp()-300 else "Dead :broken_heart:"}", inline=False)
        emb.add_field(name="God", value=f"{":white_check_mark:" if bool(data.god) else ":x:"}", inline=False)
        emb.add_field(name="Strength", value=f"{format(data.strength,",d")} :crossed_swords:", inline=True)
        emb.add_field(name="Defence", value=f"{format(data.defence,",d")} :shield:", inline=True)
        emb.add_field(name="Dexterity", value=f"{format(data.dexterity,",d")} :boot:", inline=True)
        emb.add_field(name="Active", value=f"<t:{data.enable_time}:R> (<t:{data.enable_time}>)", inline=False)

        emb.set_footer(text=f"Page {self.current_page + 1}/{len(self.data)}")
        return emb
            
    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page -= 1
        if self.current_page < 0:
            self.current_page = len(self.data) - 1
            
        await self.update_message(self.data[self.current_page])

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page += 1
        try:
            await self.update_message(self.data[self.current_page])
        except IndexError:
            self.current_page = 0
            await self.update_message(self.data[self.current_page])
    